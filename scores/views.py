from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum
from accounts.models import User, SchoolClass
from .models import ScoreTransaction


@login_required
def leaderboard(request):
    """Лидеры класса или всех классов."""
    class_id = request.GET.get('class')
    students = User.objects.filter(role='student')
    if class_id:
        students = students.filter(school_class_id=class_id)

    students = students.annotate(
        total=Sum('score_transactions__points')
    ).order_by('-total', 'username')

    return render(request, 'scores/leaderboard.html', {
        'students': students,
        'classes': SchoolClass.objects.all(),
        'selected_class': class_id,
    })


@login_required
def give_points(request, student_id):
    """Учитель вручную выдаёт баллы."""
    if not request.user.is_teacher():
        messages.error(request, 'Только учитель может начислять баллы')
        return redirect('home')

    student = get_object_or_404(User, pk=student_id, role='student')

    if student.school_class is None or student.school_class.teacher_id != request.user.id:
        messages.error(request, 'Это не ваш ученик')
        return redirect('scores:leaderboard')

    if request.method == 'POST':
        try:
            points = int(request.POST.get('points', 0))
        except ValueError:
            messages.error(request, 'Некорректное число')
            return redirect('scores:give_points', student_id=student.id)

        comment = request.POST.get('comment', '')
        ScoreTransaction.objects.create(
            student=student, teacher=request.user,
            points=points, reason='manual', comment=comment
        )
        messages.success(request, f'{student.username} получил {points:+d} баллов')
        return redirect('scores:leaderboard')

    return render(request, 'scores/give_points.html', {'student': student})