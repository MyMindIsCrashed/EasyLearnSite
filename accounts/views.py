from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, Avg, Max
from django.utils import timezone
from datetime import timedelta

from .models import User, SchoolClass
from .forms import StudentSignUpForm, TeacherSignUpForm, ProfileForm


def signup(request):
    role = request.GET.get('role') or request.POST.get('role')

    if request.method == 'POST':
        if role == 'student':
            form = StudentSignUpForm(request.POST)
        elif role == 'teacher':
            form = TeacherSignUpForm(request.POST)
        else:
            messages.error(request, 'Выберите роль')
            return redirect('accounts:signup')

        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('home')
    else:
        if role == 'student':
            form = StudentSignUpForm()
        elif role == 'teacher':
            form = TeacherSignUpForm()
        else:
            form = None

    return render(request, 'accounts/signup.html', {
        'form': form,
        'role': role,
    })


# ============================================================
# ЛИЧНЫЙ КАБИНЕТ
# ============================================================
@login_required
def profile(request):
    if request.user.is_student():
        return profile_student(request)
    return profile_teacher(request)


def profile_student(request):
    from games.models import StudentAnswer

    user = request.user

    total_score = user.score_transactions.aggregate(s=Sum('points'))['s'] or 0

    sessions = user.game_sessions.all()
    games_played = sessions.count()
    games_finished = sessions.filter(is_finished=True).count()

    now = timezone.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    score_week = user.score_transactions.filter(
        created_at__gte=week_ago
    ).aggregate(s=Sum('points'))['s'] or 0

    score_month = user.score_transactions.filter(
        created_at__gte=month_ago
    ).aggregate(s=Sum('points'))['s'] or 0

    answers = StudentAnswer.objects.filter(student=user)
    total_answers = answers.count()
    correct_answers = answers.filter(is_correct=True).count()
    wrong_answers = total_answers - correct_answers
    accuracy = round(correct_answers / total_answers * 100, 1) if total_answers else 0

    avg_quiz = sessions.aggregate(a=Avg('quiz_score'))['a'] or 0
    best_quiz = sessions.aggregate(m=Max('quiz_score'))['m'] or 0

    rank = None
    classmates_count = 0
    if user.school_class:
        classmates = User.objects.filter(
            role='student', school_class=user.school_class
        ).annotate(total=Sum('score_transactions__points')).order_by('-total')
        classmates_count = classmates.count()
        for i, s in enumerate(classmates, start=1):
            if s.id == user.id:
                rank = i
                break

    global_rank = None
    all_students = User.objects.filter(role='student').annotate(
        total=Sum('score_transactions__points')
    ).order_by('-total')
    total_students = all_students.count()
    for i, s in enumerate(all_students, start=1):
        if s.id == user.id:
            global_rank = i
            break

    history = user.score_transactions.order_by('-created_at')[:15]
    recent_games = sessions.select_related('game').order_by('-joined_at')[:5]

    achievements = compute_achievements(user, {
        'total_score': total_score,
        'games_finished': games_finished,
        'correct_answers': correct_answers,
        'accuracy': accuracy,
        'rank': rank,
    })

    chart_data = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        pts = user.score_transactions.filter(
            created_at__gte=day_start, created_at__lt=day_end
        ).aggregate(s=Sum('points'))['s'] or 0
        chart_data.append({
            'label': day.strftime('%d.%m'),
            'value': pts,
        })

    max_chart = max([d['value'] for d in chart_data] + [1])

    context = {
        'total_score': total_score,
        'score_week': score_week,
        'score_month': score_month,
        'games_played': games_played,
        'games_finished': games_finished,
        'total_answers': total_answers,
        'correct_answers': correct_answers,
        'wrong_answers': wrong_answers,
        'accuracy': accuracy,
        'avg_quiz': round(avg_quiz, 1),
        'best_quiz': best_quiz,
        'rank': rank,
        'classmates_count': classmates_count,
        'global_rank': global_rank,
        'total_students': total_students,
        'history': history,
        'recent_games': recent_games,
        'achievements': achievements,
        'chart_data': chart_data,
        'max_chart': max_chart,
    }
    return render(request, 'accounts/profile_student.html', context)


def profile_teacher(request):
    user = request.user

    classes = SchoolClass.objects.filter(teacher=user).annotate(
        student_count=Count('students')
    )

    total_games = user.created_games.count()
    games_active = user.created_games.filter(status__in=['quiz', 'maze']).count()
    games_finished = user.created_games.filter(status='finished').count()

    total_students = User.objects.filter(
        role='student',
        school_class__in=classes
    ).count()

    top_students = User.objects.filter(
        role='student',
        school_class__in=classes
    ).annotate(total=Sum('score_transactions__points')).order_by('-total')[:5]

    recent_games = user.created_games.order_by('-created_at')[:5]

    return render(request, 'accounts/profile_teacher.html', {
        'classes': classes,
        'total_games': total_games,
        'games_active': games_active,
        'games_finished': games_finished,
        'total_students': total_students,
        'top_students': top_students,
        'recent_games': recent_games,
    })


# ============================================================
# ПУБЛИЧНЫЙ ПРОФИЛЬ ДРУГОГО ПОЛЬЗОВАТЕЛЯ
# ============================================================
@login_required
def user_profile(request, user_id):
    """Подробный профиль другого ученика/учителя (только просмотр)."""
    from games.models import StudentAnswer

    profile_user = get_object_or_404(User, pk=user_id)

    if profile_user.id == request.user.id:
        return redirect('accounts:profile')

    now = timezone.now()

    # === БАЗА ===
    total_score = profile_user.score_transactions.aggregate(
        s=Sum('points')
    )['s'] or 0

    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    score_week = profile_user.score_transactions.filter(
        created_at__gte=week_ago
    ).aggregate(s=Sum('points'))['s'] or 0

    score_month = profile_user.score_transactions.filter(
        created_at__gte=month_ago
    ).aggregate(s=Sum('points'))['s'] or 0

    # === ИГРЫ ===
    sessions = profile_user.game_sessions.all()
    games_played = sessions.count()
    games_finished = sessions.filter(is_finished=True).count()

    avg_quiz = sessions.aggregate(a=Avg('quiz_score'))['a'] or 0
    best_quiz = sessions.aggregate(m=Max('quiz_score'))['m'] or 0

    # === ОТВЕТЫ ===
    answers = StudentAnswer.objects.filter(student=profile_user)
    total_answers = answers.count()
    correct_answers = answers.filter(is_correct=True).count()
    wrong_answers = total_answers - correct_answers
    accuracy = round(correct_answers / total_answers * 100, 1) if total_answers else 0

    # === МЕСТО В КЛАССЕ ===
    rank = None
    classmates_count = 0
    if profile_user.school_class:
        classmates = User.objects.filter(
            role='student',
            school_class=profile_user.school_class
        ).annotate(total=Sum('score_transactions__points')).order_by('-total')
        classmates_count = classmates.count()
        for i, s in enumerate(classmates, start=1):
            if s.id == profile_user.id:
                rank = i
                break

    # === МЕСТО В ШКОЛЕ ===
    global_rank = None
    all_students = User.objects.filter(role='student').annotate(
        total=Sum('score_transactions__points')
    ).order_by('-total')
    total_students = all_students.count()
    for i, s in enumerate(all_students, start=1):
        if s.id == profile_user.id:
            global_rank = i
            break

    # === ИСТОРИЯ / ИГРЫ ===
    history = profile_user.score_transactions.order_by('-created_at')[:15]
    recent_games = sessions.select_related('game').order_by('-joined_at')[:5]

    # === ДОСТИЖЕНИЯ ===
    achievements = compute_achievements(profile_user, {
        'total_score': total_score,
        'games_finished': games_finished,
        'correct_answers': correct_answers,
        'accuracy': accuracy,
        'rank': rank,
    })

    # === ГРАФИК ===
    chart_data = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        pts = profile_user.score_transactions.filter(
            created_at__gte=day_start, created_at__lt=day_end
        ).aggregate(s=Sum('points'))['s'] or 0
        chart_data.append({
            'label': day.strftime('%d.%m'),
            'value': pts,
        })

    max_chart = max([d['value'] for d in chart_data] + [1])

    return render(request, 'accounts/user_profile.html', {
        'profile_user': profile_user,
        'total_score': total_score,
        'score_week': score_week,
        'score_month': score_month,
        'games_played': games_played,
        'games_finished': games_finished,
        'avg_quiz': round(avg_quiz, 1),
        'best_quiz': best_quiz,
        'total_answers': total_answers,
        'correct_answers': correct_answers,
        'wrong_answers': wrong_answers,
        'accuracy': accuracy,
        'rank': rank,
        'classmates_count': classmates_count,
        'global_rank': global_rank,
        'total_students': total_students,
        'history': history,
        'recent_games': recent_games,
        'achievements': achievements,
        'chart_data': chart_data,
        'max_chart': max_chart,
    })


# ============================================================
# ДОСТИЖЕНИЯ
# ============================================================
def compute_achievements(user, stats):
    achievements = []

    if stats['total_score'] >= 100:
        achievements.append({'emoji': '💯', 'title': '100 баллов', 'desc': 'Набрал 100 баллов'})
    if stats['total_score'] >= 500:
        achievements.append({'emoji': '🔥', 'title': '500 баллов', 'desc': 'Набрал 500 баллов'})
    if stats['total_score'] >= 1000:
        achievements.append({'emoji': '👑', 'title': '1000 баллов', 'desc': 'Набрал 1000 баллов'})

    if stats['games_finished'] >= 1:
        achievements.append({'emoji': '🎮', 'title': 'Первая игра', 'desc': 'Прошёл первый лабиринт'})
    if stats['games_finished'] >= 5:
        achievements.append({'emoji': '🎯', 'title': '5 лабиринтов', 'desc': 'Прошёл 5 лабиринтов'})
    if stats['games_finished'] >= 20:
        achievements.append({'emoji': '🏅', 'title': '20 лабиринтов', 'desc': 'Прошёл 20 лабиринтов'})

    if stats['correct_answers'] >= 10:
        achievements.append({'emoji': '✅', 'title': '10 верных', 'desc': '10 правильных ответов'})
    if stats['correct_answers'] >= 50:
        achievements.append({'emoji': '🎓', 'title': '50 верных', 'desc': '50 правильных ответов'})

    if stats['accuracy'] >= 90:
        achievements.append({'emoji': '🎯', 'title': 'Снайпер', 'desc': 'Точность 90%+'})

    if stats['rank'] == 1:
        achievements.append({'emoji': '🥇', 'title': 'Чемпион', 'desc': '1 место в классе'})
    elif stats['rank'] == 2:
        achievements.append({'emoji': '🥈', 'title': 'Вице-чемпион', 'desc': '2 место в классе'})
    elif stats['rank'] == 3:
        achievements.append({'emoji': '🥉', 'title': 'Бронза', 'desc': '3 место в классе'})

    return achievements


# ============================================================
# РЕДАКТИРОВАНИЕ ПРОФИЛЯ
# ============================================================
@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль обновлён!')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)

    return render(request, 'accounts/profile_edit.html', {'form': form})


@login_required
def profile_delete_avatar(request):
    if request.method == 'POST':
        request.user.avatar.delete(save=True)
        messages.success(request, 'Картинка удалена')
    return redirect('accounts:profile_edit')