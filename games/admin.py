from django.contrib import admin
from .models import (
    Game, Question, AnswerOption, StudentAnswer, GameSession,
    MonopolyGame, MonopolyPlayer,
)


class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    extra = 4
    min_num = 2


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'game', 'points', 'order')
    list_filter = ('game',)
    inlines = [AnswerOptionInline]


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('title', 'pin_code', 'school_class', 'created_by', 'status', 'created_at')
    list_filter = ('status', 'school_class')
    search_fields = ('title', 'pin_code')
    readonly_fields = ('pin_code',)


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = ('student', 'question', 'is_correct', 'answered_at')
    list_filter = ('is_correct',)


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    list_display = ('student', 'game', 'quiz_score', 'spent_points', 'is_finished', 'finished_at')
    list_filter = ('is_finished', 'game')


class MonopolyPlayerInline(admin.TabularInline):
    model = MonopolyPlayer
    extra = 0


@admin.register(MonopolyGame)
class MonopolyGameAdmin(admin.ModelAdmin):
    list_display = ('id', 'game', 'status', 'turn_number', 'created_at')
    list_filter = ('status',)
    inlines = [MonopolyPlayerInline]


@admin.register(MonopolyPlayer)
class MonopolyPlayerAdmin(admin.ModelAdmin):
    list_display = ('student', 'monopoly', 'position', 'bonus_points', 'is_finished')
    list_filter = ('is_finished', 'monopoly')