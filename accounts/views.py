from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .models import User, SchoolClass
from .forms import StudentSignUpForm, TeacherSignUpForm


def signup(request):
    """Страница выбора роли + форма регистрации."""
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


@login_required
def profile(request):
    """Личный кабинет — отличается для учителя и ученика."""
    if request.user.is_student():
        total = request.user.score_transactions.aggregate(s=Sum('points'))['s'] or 0
        history = request.user.score_transactions.order_by('-created_at')[:20]
        return render(request, 'accounts/profile_student.html', {
            'total': total,
            'history': history,
        })

    # учитель
    classes = SchoolClass.objects.filter(teacher=request.user)
    return render(request, 'accounts/profile_teacher.html', {
        'classes': classes,
    })