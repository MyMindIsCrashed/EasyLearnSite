from django.contrib import admin
from .models import Game, Question, AnswerOption, StudentAnswer


class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    extra = 4


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'game', 'points', 'order')
    list_filter = ('game',)
    inlines = [AnswerOptionInline]


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('title', 'school_class', 'created_by', 'is_active', 'created_at')
    list_filter = ('is_active', 'school_class')
    search_fields = ('title',)


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = ('student', 'question', 'is_correct', 'answered_at')
    list_filter = ('is_correct',)