import random
import string
import math
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
        if score <= 20:
            size = 7
        elif score <= 40:
            size = 9
        elif score <= 70:
            size = 11
        elif score <= 100:
            size = 13
        else:
            size = 15

        if score <= 20:
            braid = 0.35
        elif score <= 40:
            braid = 0.30
        elif score <= 70:
            braid = 0.25
        else:
            braid = 0.20

        maze = self._build_maze(size, braid)
        self.maze_data = maze
        self.save()
        return maze

    @staticmethod
    def _bfs_distances(maze, start):
        rows, cols = len(maze), len(maze[0])
        dist = {start: 0}
        q = deque([start])
        while q:
            r, c = q.popleft()
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if (0 <= nr < rows and 0 <= nc < cols
                        and (nr, nc) not in dist
                        and maze[nr][nc] != 0):
                    dist[(nr, nc)] = dist[(r, c)] + 1
                    q.append((nr, nc))
        return dist

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

        start = (1, 1)
        goal = (size - 2, size - 2)
        dist_from_start = self._bfs_distances(maze, start)
        dist_from_goal = self._bfs_distances(maze, goal)

        trap_count = max(3, size // 2)
        placed = 0
        attempts = 0

        while placed < trap_count and attempts < 500:
            attempts += 1
            r = random.randrange(1, size - 1)
            c = random.randrange(1, size - 1)

            if maze[r][c] != 1:
                continue
            if (r, c) == start or (r, c) == goal:
                continue
            if (r, c) not in dist_from_start or dist_from_start[(r, c)] < 3:
                continue
            if (r, c) not in dist_from_goal or dist_from_goal[(r, c)] < 3:
                continue

            neighbors = 0
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < size and 0 <= nc < size and maze[nr][nc] != 0:
                    neighbors += 1
            if neighbors < 3:
                continue

            maze[r][c] = 4
            placed += 1

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
# МОНОПОЛИЯ
# ============================================================
MONOPOLY_MAP = [
    {'type': 'start', 'label': '🎲 Старт',       'icon': '🎲', 'effect': 0},
    {'type': 'empty', 'label': 'Пустая',         'icon': '⬜', 'effect': 0},
    {'type': 'bonus', 'label': 'Бонус +5',       'icon': '🎁', 'effect': 5},
    {'type': 'boost', 'label': 'Ускорение +3',   'icon': '⚡', 'effect': 3},
    {'type': 'empty', 'label': 'Пустая',         'icon': '⬜', 'effect': 0},
    {'type': 'trap',  'label': 'Ловушка −2',     'icon': '💀', 'effect': -2},
    {'type': 'bonus', 'label': 'Бонус +5',       'icon': '🎁', 'effect': 5},
    {'type': 'bonus', 'label': 'Бонус +5',       'icon': '🎁', 'effect': 5},
    {'type': 'empty', 'label': 'Пустая',         'icon': '⬜', 'effect': 0},
    {'type': 'boost', 'label': 'Ускорение +2',   'icon': '⚡', 'effect': 2},
    {'type': 'swap',  'label': 'Обмен местами',  'icon': '🔄', 'effect': 0},
    {'type': 'empty', 'label': 'Пустая',         'icon': '⬜', 'effect': 0},
    {'type': 'bonus', 'label': 'Бонус +5',       'icon': '🎁', 'effect': 5},
    {'type': 'boost', 'label': 'Ускорение +3',   'icon': '⚡', 'effect': 3},
    {'type': 'trap',  'label': 'Ловушка −2',     'icon': '💀', 'effect': -2},
    {'type': 'bonus', 'label': 'Бонус +5',       'icon': '🎁', 'effect': 5},
    {'type': 'empty', 'label': 'Пустая',         'icon': '⬜', 'effect': 0},
    {'type': 'bonus', 'label': 'Бонус +5',       'icon': '🎁', 'effect': 5},
    {'type': 'boost', 'label': 'Ускорение +2',   'icon': '⚡', 'effect': 2},
    {'type': 'finish', 'label': '🏁 Финиш',      'icon': '🏁', 'effect': 0},
]
MONOPOLY_MAX_POSITION = len(MONOPOLY_MAP) - 1


CARD_SHIELD = 'shield'
CARD_DOUBLE = 'double'
CARD_SEVEN = 'seven'

CARD_INFO = {
    CARD_SHIELD: {
        'name': 'Защита от ловушек',
        'emoji': '🛡',
        'desc': 'Первая ловушка на пути не отбросит тебя назад',
    },
    CARD_DOUBLE: {
        'name': 'Двойной бросок',
        'emoji': '🎲',
        'desc': 'После первого броска сможешь бросить ещё раз',
    },
    CARD_SEVEN: {
        'name': 'Бросок на 7',
        'emoji': '⚡',
        'desc': 'Первый ход — кубик покажет ровно 7',
    },
}


def calc_card_prices(max_possible_score):
    base = max(max_possible_score, 10)

    def clamp(v):
        return max(5, min(200, int(round(v))))

    return {
        CARD_SHIELD: clamp(base * 0.50),
        CARD_SEVEN:  clamp(base * 0.75),
        CARD_DOUBLE: clamp(base * 0.90),
    }


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
    state_version = models.PositiveIntegerField('Версия состояния', default=0)

    class Meta:
        verbose_name = 'Партия Монополии'
        verbose_name_plural = 'Партии Монополии'

    def __str__(self):
        return f"Монополия: {self.game.title}"

    def bump_version(self):
        self.state_version += 1
        self.save(update_fields=['state_version'])

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

    wallet_start = models.IntegerField('Баллы на старте партии', default=0)
    points_spent = models.IntegerField('Потрачено в партии', default=0)

    card_type = models.CharField(
        'Карта', max_length=20, blank=True, default='',
        choices=[(CARD_SHIELD, '🛡 Защита'),
                 (CARD_DOUBLE, '🎲 Двойной бросок'),
                 (CARD_SEVEN, '⚡ Бросок на 7'),
                 ('', 'Не куплена')]
    )
    card_used = models.BooleanField('Карта использована', default=False)
    has_extra_turn = models.BooleanField('Есть доп. ход', default=False)

    is_finished = models.BooleanField('Дошёл до финиша', default=False)
    finished_at = models.DateTimeField('Финиш', null=True, blank=True)
    joined_at = models.DateTimeField('Подключился', auto_now_add=True)
    move_seq = models.PositiveIntegerField('Номер хода игрока', default=0)

    class Meta:
        unique_together = ('monopoly', 'student')
        ordering = ['position', 'joined_at']
        verbose_name = 'Игрок Монополии'
        verbose_name_plural = 'Игроки Монополии'

    def __str__(self):
        return f"{self.student.username} @ {self.monopoly.game.title}"

    @property
    def wallet(self):
        return max(0, self.wallet_start - self.points_spent)


# ============================================================
# АТАКА БАШНИ
# ============================================================
import math

TOWER_MAX_HP = 100

ATTACK_ARROW = 'arrow'
ATTACK_METEOR = 'meteor'
ATTACK_FIREBALL = 'fireball'
ATTACK_ROCK = 'rock'
ATTACK_LIGHTNING = 'lightning'

TOWER_ATTACKS = {
    ATTACK_ARROW: {
        'name': 'Стрела', 'emoji': '🏹', 'damage': 5, 'chance': 100,
        'desc': 'Обычный выстрел из лука', 'is_default': True,
    },
    ATTACK_METEOR: {
        'name': 'Метеорит', 'emoji': '☄️', 'damage': 40,
        'desc': 'Мощный удар с неба (если не сработает — стрела)',
        'is_default': False,
    },
    ATTACK_FIREBALL: {
        'name': 'Огненный шар', 'emoji': '🔥', 'damage': 30,
        'desc': 'Поджигает башню врага (если не сработает — стрела)',
        'is_default': False,
    },
    ATTACK_ROCK: {
        'name': 'Камнепад', 'emoji': '🪨', 'damage': 25,
        'desc': 'Обрушивает камни (если не сработает — стрела)',
        'is_default': False,
    },
    ATTACK_LIGHTNING: {
        'name': 'Молния', 'emoji': '⚡', 'damage': 20,
        'desc': 'Быстрый разряд (если не сработает — стрела)',
        'is_default': False,
    },
}

# Шанс срабатывания спецатаки (50%)
TOWER_SPECIAL_CHANCE = 50

# Цены (% от максимума за квиз)
TOWER_ATTACK_PRICES = {
    ATTACK_METEOR: 90,
    ATTACK_FIREBALL: 70,
    ATTACK_ROCK: 50,
    ATTACK_LIGHTNING: 40,
}


class TowerGame(models.Model):
    STATUS_CHOICES = (
        ('waiting', 'Ожидание'),
        ('playing', 'Игра идёт'),
        ('finished', 'Завершена'),
    )

    game = models.OneToOneField(
        Game, on_delete=models.CASCADE,
        related_name='tower', verbose_name='Игра'
    )
    status = models.CharField('Статус', max_length=10, choices=STATUS_CHOICES, default='waiting')
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    started_at = models.DateTimeField('Начало', null=True, blank=True)
    finished_at = models.DateTimeField('Финиш', null=True, blank=True)
    state_version = models.PositiveIntegerField('Версия состояния', default=0)

    class Meta:
        verbose_name = 'Турнир «Атака башни»'
        verbose_name_plural = 'Турниры «Атака башни»'

    def __str__(self):
        return f"Башни: {self.game.title}"

    def bump_version(self):
        self.state_version += 1
        self.save(update_fields=['state_version'])

    def build_bracket(self):
        import random as rnd
        players = list(self.players.all())
        rnd.shuffle(players)

        n = len(players)
        if n < 2:
            raise ValueError('Нужно минимум 2 игрока')

        size = 2
        while size < n:
            size *= 2
        while len(players) < size:
            players.append(None)

        matches = []
        for i in range(0, size, 2):
            p1 = players[i]
            p2 = players[i + 1]
            is_bye = bool((p1 and not p2) or (p2 and not p1))

            if is_bye:
                winner = p1 if p1 else p2
                status = 'finished'
            elif p1 and p2:
                winner = None
                status = 'ready'
            else:
                continue

            match = TowerMatch.objects.create(
                tower=self,
                round_number=1,
                match_index=i // 2,
                player1=p1,
                player2=p2,
                status=status,
                winner=winner,
                is_bye=is_bye,
                hp1=TOWER_MAX_HP if p1 else 0,
                hp2=TOWER_MAX_HP if p2 else 0,
                finished_at=timezone.now() if is_bye else None,
            )
            matches.append(match)

            if is_bye and winner:
                match._advance_winner()

        total_rounds = int(math.log2(size))
        prev_matches = matches
        for r in range(2, total_rounds + 1):
            next_matches = []
            count = max(1, len(prev_matches) // 2)
            for i in range(count):
                m = TowerMatch.objects.create(
                    tower=self, round_number=r, match_index=i,
                    status='pending',
                    hp1=TOWER_MAX_HP, hp2=TOWER_MAX_HP,
                )
                next_matches.append(m)
            prev_matches = next_matches

        self.status = 'playing'
        self.started_at = timezone.now()
        self.save()
        self.bump_version()
        return matches

    def all_matches(self):
        return self.matches.order_by('round_number', 'match_index')

    def current_round(self):
        for m in self.matches.order_by('round_number', 'match_index'):
            if m.status in ['ready', 'playing']:
                return m.round_number
        last = self.matches.order_by('-round_number').first()
        return last.round_number if last else 1

    def current_match(self):
        m = self.matches.filter(status='playing').first()
        if m:
            return m
        return self.matches.filter(
            status='ready',
            player1__isnull=False,
            player2__isnull=False,
        ).order_by('round_number', 'match_index').first()

    def check_finished(self):
        if not self.matches.exclude(status='finished').exists():
            self.status = 'finished'
            self.finished_at = timezone.now()
            self.save()
            final = self.matches.order_by('-round_number', 'match_index').first()
            if final and final.winner:
                final.winner.is_winner = True
                final.winner.save()
            return True
        return False


class TowerPlayer(models.Model):
    tower = models.ForeignKey(
        TowerGame, on_delete=models.CASCADE,
        related_name='players', verbose_name='Турнир'
    )
    student = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE,
        related_name='tower_players', verbose_name='Ученик'
    )
    wallet_start = models.IntegerField('Баллы на старте', default=0)
    points_spent = models.IntegerField('Потрачено', default=0)

    # Купленная спецатака (покупается ДО турнира в магазине)
    chosen_attack = models.CharField(
        'Купленная спецатака', max_length=20, blank=True, default='',
        choices=[(ATTACK_METEOR, '☄️ Метеорит'),
                 (ATTACK_FIREBALL, '🔥 Огненный шар'),
                 (ATTACK_ROCK, '🪨 Камнепад'),
                 (ATTACK_LIGHTNING, '⚡ Молния'),
                 ('', 'Нет')]
    )
    joined_at = models.DateTimeField('Подключился', auto_now_add=True)
    is_eliminated = models.BooleanField('Выбыл', default=False)
    is_winner = models.BooleanField('Победитель', default=False)

    class Meta:
        unique_together = ('tower', 'student')
        ordering = ['joined_at']
        verbose_name = 'Участник турнира'
        verbose_name_plural = 'Участники турнира'

    def __str__(self):
        return f"{self.student.username} @ {self.tower.game.title}"

    @property
    def wallet(self):
        return max(0, self.wallet_start - self.points_spent)


class TowerMatch(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Ожидает'),
        ('ready', 'Готов'),
        ('playing', 'Идёт'),
        ('finished', 'Завершён'),
    )

    tower = models.ForeignKey(
        TowerGame, on_delete=models.CASCADE,
        related_name='matches', verbose_name='Турнир'
    )
    round_number = models.PositiveIntegerField('Раунд', default=1)
    match_index = models.PositiveIntegerField('Номер в раунде', default=0)

    player1 = models.ForeignKey(
        TowerPlayer, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='matches_as_p1',
    )
    player2 = models.ForeignKey(
        TowerPlayer, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='matches_as_p2',
    )

    hp1 = models.IntegerField('HP башни 1', default=TOWER_MAX_HP)
    hp2 = models.IntegerField('HP башни 2', default=TOWER_MAX_HP)

    turn = models.PositiveSmallIntegerField('Чей ход', default=1)
    status = models.CharField('Статус', max_length=10, choices=STATUS_CHOICES, default='pending')
    winner = models.ForeignKey(
        TowerPlayer, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='matches_won',
    )
    is_bye = models.BooleanField('Автопроход', default=False)

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    log = models.JSONField('Лог боя', default=list, blank=True)

    class Meta:
        ordering = ['round_number', 'match_index']

    def __str__(self):
        p1 = self.player1.student.username if self.player1 else '—'
        p2 = self.player2.student.username if self.player2 else '—'
        return f"R{self.round_number} #{self.match_index}: {p1} vs {p2}"

    @property
    def round_name(self):
        total = self.tower.matches.aggregate(m=models.Max('round_number'))['m'] or 1
        names = {
            total: 'Финал',
            total - 1: 'Полуфинал',
            total - 2: '1/4 финала',
            total - 3: '1/8 финала',
        }
        return names.get(self.round_number, f'Раунд {self.round_number}')

    def check_finish(self):
        if self.hp1 <= 0 and self.hp2 <= 0:
            self.winner = self.player2 if self.hp1 < self.hp2 else self.player1
        elif self.hp1 <= 0:
            self.winner = self.player2
        elif self.hp2 <= 0:
            self.winner = self.player1

        if self.winner:
            self.status = 'finished'
            self.finished_at = timezone.now()
            self.save()
            self._advance_winner()
            return True
        return False

    def _advance_winner(self):
        if not self.winner:
            return

        loser = self.player2 if self.winner == self.player1 else self.player1
        if loser:
            loser.is_eliminated = True
            loser.save()

        next_round = self.round_number + 1
        next_index = self.match_index // 2
        next_match = self.tower.matches.filter(
            round_number=next_round, match_index=next_index,
        ).first()

        if not next_match:
            self.winner.is_winner = True
            self.winner.save()
            self.tower.check_finished()
            return

        if self.match_index % 2 == 0:
            next_match.player1 = self.winner
        else:
            next_match.player2 = self.winner

        if next_match.player1 and next_match.player2:
            next_match.status = 'ready'
        next_match.save()
        self.tower.bump_version()

    def do_attack(self, attacker):
        """
        Единая атака.
        Если у игрока есть купленная спецатака и она сработала (50%) — бьёт она.
        Иначе — обычная стрела.
        """
        if self.status != 'playing':
            return {'error': 'not_playing'}

        current = self.player1 if self.turn == 1 else self.player2
        if current is None or current.id != attacker.id:
            return {'error': 'not_your_turn'}

        if attacker.id == self.player1_id:
            target_hp_field = 'hp2'
            defender = self.player2
        else:
            target_hp_field = 'hp1'
            defender = self.player1

        # По умолчанию — стрела
        attack_type = ATTACK_ARROW
        attack_info = TOWER_ATTACKS[ATTACK_ARROW]

        # Проверка спецатаки
        if attacker.chosen_attack and attacker.chosen_attack in TOWER_ATTACKS:
            if random.randint(1, 100) <= TOWER_SPECIAL_CHANCE:
                attack_type = attacker.chosen_attack
                attack_info = TOWER_ATTACKS[attack_type]

        # Наносим урон
        damage = attack_info['damage']
        new_hp = getattr(self, target_hp_field) - damage
        setattr(self, target_hp_field, max(0, new_hp))

        result = {
            'attack': attack_type,
            'attack_name': attack_info['name'],
            'attack_emoji': attack_info['emoji'],
            'damage': damage,
            'attacker_id': attacker.id,
            'attacker_name': attacker.student.get_full_name() or attacker.student.username,
            'defender_id': defender.id if defender else None,
            'defender_name': (defender.student.get_full_name() or defender.student.username) if defender else '',
            'hp_after': getattr(self, target_hp_field),
            'is_special': attack_type != ATTACK_ARROW,
        }

        log = list(self.log or [])
        log.append(result)
        self.log = log

        # Передаём ход
        self.turn = 2 if self.turn == 1 else 1

        # Конец боя?
        finished = self.check_finish()
        result['finished'] = finished
        result['winner_id'] = self.winner.id if self.winner else None

        self.save()
        self.tower.bump_version()
        return result