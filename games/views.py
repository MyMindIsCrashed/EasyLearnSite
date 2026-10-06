from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.db.models import Sum
from .models import Game, Question, AnswerOption, StudentAnswer
from scores.models import ScoreTransaction


@login_required
def game_list(request):
    if request.user.is_teacher():
        games = Game.objects.filter(created_by=request.user)
    else:
        games = Game.objects.filter(school_class=request.user.school_class)
    return render(request, 'games/list.html', {'games': games})


@login_required
def game_create(request):
    if not request.user.is_teacher():
        messages.error(request, 'Только учитель может создавать игры')
        return redirect('games:list')

    from accounts.models import SchoolClass

    if request.method == 'POST':
        title = request.POST.get('title')
        class_id = request.POST.get('school_class')
        school_class = get_object_or_404(SchoolClass, pk=class_id, teacher=request.user)
        game = Game.objects.create(
            title=title, school_class=school_class, created_by=request.user
        )
        messages.success(request, 'Игра создана!')
        return redirect('games:detail', game_id=game.id)

    classes = SchoolClass.objects.filter(teacher=request.user)
    return render(request, 'games/create.html', {'classes': classes})


@login_required
def game_detail(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    return render(request, 'games/detail.html', {'game': game})


@login_required
def game_start(request, game_id):
    game = get_object_or_404(Game, pk=game_id, is_active=True)
    if not request.user.is_student():
        return redirect('games:list')

    answered_ids = StudentAnswer.objects.filter(
        student=request.user, question__game=game
    ).values_list('question_id', flat=True)
    question = game.questions.exclude(id__in=answered_ids).first()

    if not question:
        return redirect('games:finish', game_id=game.id)

    return render(request, 'games/question.html', {'game': game, 'question': question})


@login_required
def answer_question(request, question_id):
    if request.method != 'POST':
        return redirect('games:list')

    question = get_object_or_404(Question, pk=question_id)
    option_id = request.POST.get('option')
    option = get_object_or_404(AnswerOption, pk=option_id, question=question)

    if StudentAnswer.objects.filter(student=request.user, question=question).exists():
        return redirect('games:start', game_id=question.game_id)

    is_correct = option.is_correct
    StudentAnswer.objects.create(
        student=request.user, question=question,
        selected=option, is_correct=is_correct
    )

    if is_correct:
        ScoreTransaction.objects.create(
            student=request.user,
            teacher=question.game.created_by,
            points=question.points,
            reason='quiz',
            comment=f'Верный ответ: {question.text[:40]}'
        )

    return redirect('games:start', game_id=question.game_id)


@login_required
def game_finish(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    earned = (StudentAnswer.objects
              .filter(student=request.user, question__game=game, is_correct=True)
              .aggregate(s=Sum('question__points'))['s'] or 0)
    return render(request, 'games/finish.html', {'game': game, 'earned': earned})