from django.contrib import admin
from .models import ScoreTransaction


@admin.register(ScoreTransaction)
class ScoreTransactionAdmin(admin.ModelAdmin):
    list_display = ('student', 'points', 'reason', 'teacher', 'created_at')
    list_filter = ('reason', 'created_at')
    search_fields = ('student__username', 'comment')