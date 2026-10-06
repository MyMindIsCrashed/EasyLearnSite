from django.db import models
from django.conf import settings


class ScoreTransaction(models.Model):
    """Начисление баллов ученику (за игру или вручную)."""
    REASON_CHOICES = (
        ('quiz', 'Ответ в игре'),
        ('manual', 'Вручную учителем'),
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='score_transactions',
        verbose_name='Ученик'
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='given_scores',
        verbose_name='Учитель'
    )
    points = models.IntegerField('Баллы')
    reason = models.CharField('Причина', max_length=10, choices=REASON_CHOICES)
    comment = models.CharField('Комментарий', max_length=200, blank=True)
    created_at = models.DateTimeField('Дата', auto_now_add=True)

    class Meta:
        verbose_name = 'Начисление баллов'
        verbose_name_plural = 'Начисления баллов'
        ordering = ['-created_at']

    def __str__(self):
        sign = '+' if self.points >= 0 else ''
        return f"{self.student.username}: {sign}{self.points}"