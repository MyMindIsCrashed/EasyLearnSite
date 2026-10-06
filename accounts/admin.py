from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, SchoolClass


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'get_full_name', 'role', 'grade', 'school_class', 'is_staff')
    list_filter = ('role', 'grade', 'is_staff', 'is_superuser')
    search_fields = ('username', 'first_name', 'last_name')

    fieldsets = UserAdmin.fieldsets + (
        ('EasyLearnSite', {'fields': ('role', 'grade', 'school_class')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('EasyLearnSite', {'fields': ('role', 'grade', 'school_class')}),
    )


@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'grade', 'teacher')
    list_filter = ('grade',)