import random
import string
from collections import deque
from django.db import models
from django.conf import settings
from django.utils import timezone


def generate_pin():
    while True:
        pin = ''.join(random.choices(string.digits, k=4))
        if not Game.objects.filter(pin_code=pin, status__in=['waiting', 'quiz', 'maze']).exists():
            return pin


class Game(models.Model):
    STATUS_CHOICES = (
        ('waiting', 'Ожидание'),
        ('quiz', 'Квиз идёт'),
        ('maze', 'Лабиринт'),
        ('finished', 'Завершена'),
    )

    title = models.CharField('Название', max_length=200)
    school_class = models.ForeignKey(
        'accounts.SchoolClass', on_delete=models.CASCADE,
        related_name='games', verbose_name='Класс'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='created_games', verbose_name='Автор'
    )
    pin_code = models.CharField('PIN-код', max_length=4, unique=True, blank=True)
    status = models.CharField('Статус', max_length=10, choices=STATUS_CHOICES, default='waiting')
    is_active = models.BooleanField('Активна', default=False)
    started_at = models.DateTimeField('Начало', null=True, blank=True)
    created_at = models.DateTimeField('Создана', auto_now_add=True)

    class Meta:
        verbose_name = 'Игра'
        verbose_name_plural = 'Игры'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} [PIN: {self.pin_code}]"

    def save(self, *args, **kwargs):
        if not self.pin_code:
            self.pin_code = generate_pin()
        super().save(*args, **kwargs)

    def total_points(self):
        return self.questions.aggregate(s=models.Sum('points'))['s'] or 0


class Question(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField('Вопрос', max_length=500)
    points = models.PositiveSmallIntegerField('Баллы за верный ответ', default=10)
    order = models.PositiveSmallIntegerField('Порядок', default=0)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'

    def __str__(self):
        return f"{self.order}. {self.text[:50]}"


class AnswerOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField('Вариант ответа', max_length=300)
    is_correct = models.BooleanField('Правильный', default=False)

    class Meta:
        verbose_name = 'Вариант ответа'
        verbose_name_plural = 'Варианты ответов'

    def __str__(self):
        return self.text


class StudentAnswer(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected = models.ForeignKey(AnswerOption, on_delete=models.CASCADE)
    is_correct = models.BooleanField()
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'question')


class GameSession(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='sessions')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='game_sessions')
    quiz_score = models.IntegerField('Баллы за квиз', default=0)
    spent_points = models.IntegerField('Потрачено в лабиринте', default=0)
    maze_bonus = models.IntegerField('Бонус за лабиринт', default=0)
    position = models.JSONField('Позиция', default=dict)
    maze_data = models.JSONField('Личный лабиринт', null=True, blank=True)
    is_finished = models.BooleanField('Финишировал', default=False)
    finished_at = models.DateTimeField('Финиш', null=True, blank=True)
    joined_at = models.DateTimeField('Подключился', auto_now_add=True)
    last_move_at = models.DateTimeField('Последний ход', null=True, blank=True)

    class Meta:
        unique_together = ('game', 'student')
        ordering = ['finished_at', 'quiz_score']

    @property
    def remaining_points(self):
        return self.quiz_score - self.spent_points

    @property
    def total_score(self):
        return self.quiz_score + self.maze_bonus

    def __str__(self):
        return f"{self.student.username} @ {self.game.title}"

    def generate_personal_maze(self):
        score = self.quiz_score
        max_path = max(6, score - 3)

        if score <= 20:
            size_pref = 7
        elif score <= 40:
            size_pref = 9
        elif score <= 60:
            size_pref = 11
        else:
            size_pref = 13

        for attempt in range(30):
            size = size_pref + (attempt % 3) * 2
            if size < 5:
                size = 5
            if size % 2 == 0:
                size += 1
            braid = 0.25 + (attempt * 0.02)
            maze = self._build_maze(size, braid)
            path_len = self._shortest_path_length(maze)
            if path_len <= max_path:
                self.maze_data = maze
                self.save()
                return maze

        maze = self._build_maze(7, 0.4)
        self.maze_data = maze
        self.save()
        return maze

    def _build_maze(self, size, braid):
        if size % 2 == 0:
            size += 1
        maze = [[0 for _ in range(size)] for _ in range(size)]

        def carve(r, c):
            maze[r][c] = 1
            dirs = [(-2, 0), (2, 0), (0, -2), (0, 2)]
            random.shuffle(dirs)
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                if 0 <= nr < size and 0 <= nc < size and maze[nr][nc] == 0:
                    maze[r + dr // 2][c + dc // 2] = 1
                    carve(nr, nc)

        carve(1, 1)

        extra = int(size * size * braid / 4)
        for _ in range(extra):
            r = random.randrange(2, size - 2)
            c = random.randrange(2, size - 2)
            if maze[r][c] == 1:
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < size and 0 <= nc < size and maze[nr][nc] == 0:
                        fr, fc = nr + dr, nc + dc
                        if 0 <= fr < size and 0 <= fc < size and maze[fr][fc] == 1:
                            maze[nr][nc] = 1
                            break

        maze[1][1] = 2
        maze[size - 2][size - 2] = 3
        return maze

    def _shortest_path_length(self, maze):
        rows, cols = len(maze), len(maze[0])
        start = goal = None
        for r in range(rows):
            for c in range(cols):
                if maze[r][c] == 2:
                    start = (r, c)
                elif maze[r][c] == 3:
                    goal = (r, c)
        if not start or not goal:
            return 9999

        q = deque([(start, 0)])
        visited = {start}

        while q:
            (r, c), dist = q.popleft()
            if (r, c) == goal:
                return dist
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if (0 <= nr < rows and 0 <= nc < cols
                        and (nr, nc) not in visited
                        and maze[nr][nc] != 0):
                    visited.add((nr, nc))
                    q.append(((nr, nc), dist + 1))
        return 9999


def is_maze_solvable(maze):
    rows, cols = len(maze), len(maze[0])
    start = goal = None
    for r in range(rows):
        for c in range(cols):
            if maze[r][c] == 2:
                start = (r, c)
            elif maze[r][c] == 3:
                goal = (r, c)
    if not start or not goal:
        return False
    visited = {start}
    q = deque([start])
    while q:
        r, c = q.popleft()
        if (r, c) == goal:
            return True
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if (0 <= nr < rows and 0 <= nc < cols
                    and (nr, nc) not in visited
                    and maze[nr][nc] != 0):
                visited.add((nr, nc))
                q.append((nr, nc))
    return False


# ============================================================
# МОНОПОЛИЯ — карта БЕЗ клетки "question"
# ============================================================
MONOPOLY_MAP = [
    {'type': 'start', 'label': '🎲 Старт',      'icon': '🎲'},
    {'type': 'empty', 'label': 'Пустая',        'icon': '⬜'},
    {'type': 'bonus', 'label': 'Бонус +5',      'icon': '🎁'},
    {'type': 'boost', 'label': 'Ускорение +3',  'icon': '⚡'},
    {'type': 'empty', 'label': 'Пустая',        'icon': '⬜'},
    {'type': 'trap',  'label': 'Ловушка −2',    'icon': '💀'},
    {'type': 'bonus', 'label': 'Бонус +5',      'icon': '🎁'},
    {'type': 'bonus', 'label': 'Бонус +5',      'icon': '🎁'},
    {'type': 'empty', 'label': 'Пустая',        'icon': '⬜'},
    {'type': 'boost', 'label': 'Ускорение +2',  'icon': '⚡'},
    {'type': 'swap',  'label': 'Обмен местами', 'icon': '🔄'},
    {'type': 'empty', 'label': 'Пустая',        'icon': '⬜'},
    {'type': 'bonus', 'label': 'Бонус +5',      'icon': '🎁'},
    {'type': 'boost', 'label': 'Ускорение +3',  'icon': '⚡'},
    {'type': 'trap',  'label': 'Ловушка −2',    'icon': '💀'},
    {'type': 'bonus', 'label': 'Бонус +5',      'icon': '🎁'},
    {'type': 'empty', 'label': 'Пустая',        'icon': '⬜'},
    {'type': 'bonus', 'label': 'Бонус +5',      'icon': '🎁'},
    {'type': 'boost', 'label': 'Ускорение +2',  'icon': '⚡'},
    {'type': 'finish', 'label': '🏁 Финиш',     'icon': '🏁'},
]
MONOPOLY_MAX_POSITION = len(MONOPOLY_MAP) - 1
MONOPOLY_MAX_TURNS = 50
MONOPOLY_MAX_PLAYERS = 6


class MonopolyGame(models.Model):
    STATUS_CHOICES = (
        ('waiting', 'Ожидание игроков'),
        ('playing', 'Игра идёт'),
        ('finished', 'Завершена'),
    )

    game = models.OneToOneField(
        Game, on_delete=models.CASCADE,
        related_name='monopoly', verbose_name='Игра'
    )
    status = models.CharField('Статус', max_length=10, choices=STATUS_CHOICES, default='waiting')
    turn_number = models.PositiveIntegerField('Номер хода', default=0)
    current_turn_index = models.PositiveIntegerField('Чья очередь', default=0)
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    started_at = models.DateTimeField('Начало', null=True, blank=True)
    finished_at = models.DateTimeField('Финиш', null=True, blank=True)

    class Meta:
        verbose_name = 'Партия Монополии'
        verbose_name_plural = 'Партии Монополии'

    def __str__(self):
        return f"Монополия: {self.game.title}"

    def players_ordered(self):
        return self.players.order_by('joined_at')

    def current_player(self):
        players = list(self.players_ordered())
        if not players:
            return None
        if self.current_turn_index >= len(players):
            return players[0]
        return players[self.current_turn_index]

    def next_turn(self):
        players = list(self.players_ordered())
        if not players:
            return
        self.current_turn_index = (self.current_turn_index + 1) % len(players)
        if self.current_turn_index == 0:
            self.turn_number += 1
        self.save()


class MonopolyPlayer(models.Model):
    monopoly = models.ForeignKey(
        MonopolyGame, on_delete=models.CASCADE,
        related_name='players', verbose_name='Партия'
    )
    student = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE,
        related_name='monopoly_players', verbose_name='Ученик'
    )
    position = models.PositiveIntegerField('Позиция', default=0)
    dice_value = models.PositiveSmallIntegerField('Последний кубик', default=0)
    last_event = models.CharField('Последнее событие', max_length=100, blank=True)
    bonus_points = models.IntegerField('Бонусные баллы', default=0)
    question_pending = models.BooleanField('Ждёт вопрос', default=False)
    is_finished = models.BooleanField('Дошёл до финиша', default=False)
    finished_at = models.DateTimeField('Финиш', null=True, blank=True)
    joined_at = models.DateTimeField('Подключился', auto_now_add=True)

    class Meta:
        unique_together = ('monopoly', 'student')
        ordering = ['position', 'joined_at']
        verbose_name = 'Игрок Монополии'
        verbose_name_plural = 'Игроки Монополии'

    def __str__(self):
        return f"{self.student.username} @ {self.monopoly.game.title}"

    def move_forward(self, steps):
        self.position = min(self.position + steps, MONOPOLY_MAX_POSITION)
        self.save()
        self._check_finish()

    def move_back(self, steps):
        self.position = max(self.position - steps, 0)
        self.save()

    def set_position(self, new_pos):
        self.position = max(0, min(new_pos, MONOPOLY_MAX_POSITION))
        self.save()
        self._check_finish()

    def _check_finish(self):
        if self.position >= MONOPOLY_MAX_POSITION and not self.is_finished:
            self.is_finished = True
            self.finished_at = timezone.now()
            self.save()