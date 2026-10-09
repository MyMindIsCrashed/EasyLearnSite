from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Кастомный пользователь: учитель или ученик."""
    ROLE_CHOICES = (
        ('teacher', 'Учитель'),
        ('student', 'Ученик'),
    )
    role = models.CharField('Роль', max_length=10, choices=ROLE_CHOICES)
    grade = models.PositiveSmallIntegerField('Класс (1-4)', null=True, blank=True)
    school_class = models.ForeignKey(
        'SchoolClass',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='students',
        verbose_name='Школьный класс'
    )

    avatar_emoji = models.CharField(
        'Эмодзи-аватар', max_length=10, blank=True, default='🧑'
    )
    avatar = models.ImageField(
        'Своя аватарка', upload_to='avatars/', null=True, blank=True
    )

    def is_teacher(self):
        return self.role == 'teacher'

    def is_student(self):
        return self.role == 'student'

    def total_score(self):
        from django.db.models import Sum
        return self.score_transactions.aggregate(s=Sum('points'))['s'] or 0

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


class SchoolClass(models.Model):
    name = models.CharField('Название', max_length=50)
    grade = models.PositiveSmallIntegerField('Параллель (1-4)')
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_classes',
        limit_choices_to={'role': 'teacher'},
        verbose_name='Учитель'
    )

    class Meta:
        verbose_name = 'Школьный класс'
        verbose_name_plural = 'Школьные классы'

    def __str__(self):
        return f"{self.name} (учитель: {self.teacher.username})"