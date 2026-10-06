from django.db import models
from django.conf import settings


class Game(models.Model):
    """Урок-игра, создаётся учителем."""
    title = models.CharField('Название', max_length=200)
    school_class = models.ForeignKey(
        'accounts.SchoolClass',
        on_delete=models.CASCADE,
        related_name='games',
        verbose_name='Класс'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_games',
        verbose_name='Автор'
    )
    is_active = models.BooleanField('Активна', default=False)
    created_at = models.DateTimeField('Создана', auto_now_add=True)

    class Meta:
        verbose_name = 'Игра'
        verbose_name_plural = 'Игры'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def total_points(self):
        return self.questions.aggregate(s=models.Sum('points'))['s'] or 0


class Question(models.Model):
    game = models.ForeignKey(
        Game, on_delete=models.CASCADE, related_name='questions'
    )
    text = models.CharField('Вопрос', max_length=500)
    points = models.PositiveSmallIntegerField('Баллы за верный ответ', default=1)
    order = models.PositiveSmallIntegerField('Порядок', default=0)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'

    def __str__(self):
        return f"{self.order}. {self.text[:50]}"


class AnswerOption(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name='options'
    )
    text = models.CharField('Вариант ответа', max_length=300)
    is_correct = models.BooleanField('Правильный', default=False)

    class Meta:
        verbose_name = 'Вариант ответа'
        verbose_name_plural = 'Варианты ответов'

    def __str__(self):
        return self.text


class StudentAnswer(models.Model):
    """Ответ ученика на конкретный вопрос."""
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='answers'
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected = models.ForeignKey(AnswerOption, on_delete=models.CASCADE)
    is_correct = models.BooleanField()
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'question')
        verbose_name = 'Ответ ученика'
        verbose_name_plural = 'Ответы учеников'

    def __str__(self):
        return f"{self.student.username} → {self.question}"