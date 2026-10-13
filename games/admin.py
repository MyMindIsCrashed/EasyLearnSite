from django.contrib import admin
from .models import TowerGame, TowerPlayer, TowerMatch
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
    fields = (
        'student', 'position', 'card_type', 'card_used',
        'has_extra_turn', 'wallet_start', 'is_finished',
    )
    readonly_fields = ('position', 'card_used', 'has_extra_turn', 'is_finished')


@admin.register(MonopolyGame)
class MonopolyGameAdmin(admin.ModelAdmin):
    list_display = ('id', 'game', 'status', 'turn_number', 'created_at')
    list_filter = ('status',)
    inlines = [MonopolyPlayerInline]


@admin.register(MonopolyPlayer)
class MonopolyPlayerAdmin(admin.ModelAdmin):
    list_display = (
        'student', 'monopoly', 'position',
        'card_type', 'card_used', 'has_extra_turn',
        'wallet_start', 'points_spent',
        'is_finished',
    )
    list_filter = ('is_finished', 'card_type', 'has_extra_turn', 'monopoly')
    search_fields = ('student__username',)

class TowerPlayerInline(admin.TabularInline):
    model = TowerPlayer
    extra = 0
    fields = ('student', 'chosen_attack', 'wallet_start', 'points_spent', 'is_eliminated', 'is_winner')
    readonly_fields = ('is_eliminated', 'is_winner')


class TowerMatchInline(admin.TabularInline):
    model = TowerMatch
    extra = 0
    fields = ('round_number', 'match_index', 'player1', 'player2', 'status', 'hp1', 'hp2', 'winner')
    readonly_fields = ('round_number', 'match_index')


@admin.register(TowerGame)
class TowerGameAdmin(admin.ModelAdmin):
    list_display = ('id', 'game', 'status', 'created_at')
    list_filter = ('status',)
    inlines = [TowerPlayerInline, TowerMatchInline]


@admin.register(TowerPlayer)
class TowerPlayerAdmin(admin.ModelAdmin):
    list_display = ('student', 'tower', 'chosen_attack', 'wallet_start', 'points_spent', 'is_eliminated', 'is_winner')
    list_filter = ('is_eliminated', 'is_winner', 'chosen_attack', 'tower')
    search_fields = ('student__username',)


@admin.register(TowerMatch)
class TowerMatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'tower', 'round_number', 'match_index', 'status', 'player1', 'player2', 'hp1', 'hp2', 'winner')
    list_filter = ('status', 'round_number')