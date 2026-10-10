import random
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import (
    Game, Question, AnswerOption, StudentAnswer, GameSession,
    MonopolyGame, MonopolyPlayer,
    MONOPOLY_MAP, MONOPOLY_MAX_POSITION,
    CARD_SHIELD, CARD_DOUBLE, CARD_SEVEN, CARD_INFO,
    calc_card_prices,
)
from .forms import QuestionForm
from scores.models import ScoreTransaction


# ============================================================
# СПИСОК / СОЗДАНИЕ
# ============================================================
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
        game = Game.objects.create(title=title, school_class=school_class, created_by=request.user)
        messages.success(request, f'Игра создана! PIN-код: {game.pin_code}')
        return redirect('games:manage', game_id=game.id)

    classes = SchoolClass.objects.filter(teacher=request.user)
    return render(request, 'games/create.html', {'classes': classes})


@login_required
def game_manage(request, game_id):
    game = get_object_or_404(Game, pk=game_id, created_by=request.user)
    monopoly = getattr(game, 'monopoly', None)
    return render(request, 'games/manage.html', {'game': game, 'monopoly': monopoly})


@login_required
def start_quiz(request, game_id):
    game = get_object_or_404(Game, pk=game_id, created_by=request.user)
    if game.questions.count() < 3:
        messages.error(request, f'Минимум 3 вопроса. Сейчас: {game.questions.count()}')
        return redirect('games:manage', game_id=game.id)

    game.status = 'quiz'
    game.is_active = True
    game.started_at = timezone.now()
    game.save()
    messages.success(request, 'Квиз запущен!')
    return redirect('games:manage', game_id=game.id)


@login_required
def start_maze(request, game_id):
    game = get_object_or_404(Game, pk=game_id, created_by=request.user)
    game.status = 'maze'
    game.save()

    for session in game.sessions.all():
        session.position = {'row': 1, 'col': 1}
        session.is_finished = False
        session.finished_at = None
        session.spent_points = 0
        session.maze_bonus = 0
        session.last_move_at = None
        session.maze_data = None
        session.save()
        session.generate_personal_maze()

    messages.success(request, 'Этап лабиринта начался!')
    return redirect('games:manage', game_id=game.id)


# ============================================================
# PIN
# ============================================================
@login_required
def game_join(request):
    if not request.user.is_student():
        return redirect('games:list')

    if request.method == 'POST':
        pin = request.POST.get('pin', '').strip()
        try:
            game = Game.objects.get(pin_code=pin, status__in=['waiting', 'quiz', 'maze'])
        except Game.DoesNotExist:
            messages.error(request, 'Игра с таким PIN не найдена')
            return render(request, 'games/join.html')

        if game.school_class != request.user.school_class:
            messages.error(request, 'Эта игра не для вашего класса')
            return render(request, 'games/join.html')

        GameSession.objects.get_or_create(
            game=game, student=request.user,
            defaults={'position': {'row': 1, 'col': 1}}
        )
        messages.success(request, f'Вы подключились к игре «{game.title}»')
        return redirect('games:detail', game_id=game.id)

    return render(request, 'games/join.html')


# ============================================================
# РОУТЕР
# ============================================================
@login_required
def game_detail(request, game_id):
    game = get_object_or_404(Game, pk=game_id)

    if request.user.is_teacher():
        return redirect('games:manage', game_id=game.id)

    session = GameSession.objects.filter(game=game, student=request.user).first()
    if not session:
        messages.info(request, 'Сначала введите PIN-код')
        return redirect('games:join')

    monopoly = getattr(game, 'monopoly', None)
    if monopoly:
        player, _ = MonopolyPlayer.objects.get_or_create(
            monopoly=monopoly, student=request.user,
            defaults={'wallet_start': 0},
        )
        if monopoly.status in ['waiting', 'playing']:
            if monopoly.status == 'waiting' and not player.card_type:
                return redirect('games:monopoly_shop', monopoly_id=monopoly.id)
            return redirect('games:monopoly_play', monopoly_id=monopoly.id)
        if monopoly.status == 'finished':
            return redirect('games:monopoly_results', monopoly_id=monopoly.id)

    if game.status == 'waiting':
        return render(request, 'games/waiting.html', {'game': game, 'session': session})
    if game.status == 'quiz':
        return redirect('games:play', game_id=game.id)
    if game.status == 'maze':
        return redirect('games:maze', game_id=game.id)
    return redirect('games:results', game_id=game.id)


# ============================================================
# КВИЗ
# ============================================================
@login_required
def game_play(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    if not request.user.is_student():
        return redirect('games:list')

    session = get_object_or_404(GameSession, game=game, student=request.user)

    monopoly = getattr(game, 'monopoly', None)
    if monopoly:
        player, _ = MonopolyPlayer.objects.get_or_create(
            monopoly=monopoly, student=request.user,
            defaults={'wallet_start': 0},
        )
        if monopoly.status in ['waiting', 'playing']:
            if monopoly.status == 'waiting' and not player.card_type:
                return redirect('games:monopoly_shop', monopoly_id=monopoly.id)
            return redirect('games:monopoly_play', monopoly_id=monopoly.id)
        if monopoly.status == 'finished':
            return redirect('games:monopoly_results', monopoly_id=monopoly.id)

    if game.status == 'waiting':
        return redirect('games:detail', game_id=game.id)
    if game.status == 'maze':
        return redirect('games:maze', game_id=game.id)
    if game.status == 'finished':
        return redirect('games:results', game_id=game.id)

    answered_ids = StudentAnswer.objects.filter(
        student=request.user, question__game=game
    ).values_list('question_id', flat=True)

    question = game.questions.exclude(id__in=answered_ids).first()

    if not question:
        return redirect('games:quiz_done', game_id=game.id)

    return render(request, 'games/question.html', {
        'game': game, 'question': question, 'session': session
    })


@login_required
@require_POST
def answer_question(request, question_id):
    question = get_object_or_404(Question, pk=question_id)

    if StudentAnswer.objects.filter(student=request.user, question=question).exists():
        return JsonResponse({
            'error': 'already_answered',
            'next_url': reverse('games:play', args=[question.game_id]),
        }, status=400)

    option_id = request.POST.get('option')
    option = get_object_or_404(AnswerOption, pk=option_id, question=question)

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

    correct_option = question.options.filter(is_correct=True).first()
    answered_ids = StudentAnswer.objects.filter(
        student=request.user, question__game=question.game
    ).values_list('question_id', flat=True)
    next_question = question.game.questions.exclude(id__in=answered_ids).first()

    return JsonResponse({
        'is_correct': is_correct,
        'correct_option_id': correct_option.id if correct_option else None,
        'selected_option_id': option.id,
        'next_url': (
            reverse('games:play', args=[question.game_id])
            if next_question else
            reverse('games:quiz_done', args=[question.game_id])
        ),
    })


@login_required
def quiz_done(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    if not request.user.is_student():
        return redirect('games:list')

    session = get_object_or_404(GameSession, game=game, student=request.user)

    monopoly = getattr(game, 'monopoly', None)
    if monopoly:
        player, _ = MonopolyPlayer.objects.get_or_create(
            monopoly=monopoly, student=request.user,
            defaults={'wallet_start': 0},
        )
        if monopoly.status in ['waiting', 'playing']:
            if monopoly.status == 'waiting' and not player.card_type:
                return redirect('games:monopoly_shop', monopoly_id=monopoly.id)
            return redirect('games:monopoly_play', monopoly_id=monopoly.id)
        if monopoly.status == 'finished':
            return redirect('games:monopoly_results', monopoly_id=monopoly.id)

    if game.status == 'maze':
        return redirect('games:maze', game_id=game.id)
    if game.status == 'finished':
        return redirect('games:results', game_id=game.id)
    if game.status == 'waiting':
        return redirect('games:detail', game_id=game.id)

    answers = StudentAnswer.objects.filter(
        student=request.user, question__game=game
    ).select_related('question', 'selected')

    total = answers.count()
    correct = answers.filter(is_correct=True).count()
    wrong = total - correct

    session.quiz_score = answers.filter(is_correct=True).aggregate(
        s=Sum('question__points')
    )['s'] or 0
    session.save()

    return render(request, 'games/quiz_done.html', {
        'game': game, 'session': session,
        'answers': answers, 'total': total,
        'correct': correct, 'wrong': wrong,
    })


# ============================================================
# ВОПРОСЫ
# ============================================================
@login_required
def question_add(request, game_id):
    game = get_object_or_404(Game, pk=game_id, created_by=request.user)
    if request.method == 'POST':
        form = QuestionForm(request.POST, game=game)
        if form.is_valid():
            form.save()
            messages.success(request, 'Вопрос добавлен!')
            return redirect('games:manage', game_id=game.id)
    else:
        form = QuestionForm(game=game)
    return render(request, 'games/question_form.html', {
        'game': game, 'form': form, 'mode': 'add',
    })


@login_required
def question_edit(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    game = question.game
    if game.created_by != request.user:
        messages.error(request, 'Нет доступа')
        return redirect('games:list')
    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question, game=game)
        if form.is_valid():
            form.save()
            messages.success(request, 'Вопрос обновлён!')
            return redirect('games:manage', game_id=game.id)
    else:
        form = QuestionForm(instance=question, game=game)
    return render(request, 'games/question_form.html', {
        'game': game, 'form': form, 'question': question, 'mode': 'edit',
    })


@login_required
@require_POST
def question_delete(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    game = question.game
    if game.created_by != request.user:
        messages.error(request, 'Нет доступа')
        return redirect('games:list')
    question.delete()
    messages.success(request, 'Вопрос удалён')
    return redirect('games:manage', game_id=game.id)


# ============================================================
# ЛАБИРИНТ
# ============================================================
@login_required
def maze_view(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    if not request.user.is_student():
        return redirect('games:list')

    session = get_object_or_404(GameSession, game=game, student=request.user)

    monopoly = getattr(game, 'monopoly', None)
    if monopoly:
        player, _ = MonopolyPlayer.objects.get_or_create(
            monopoly=monopoly, student=request.user,
            defaults={'wallet_start': 0},
        )
        if monopoly.status in ['waiting', 'playing']:
            if monopoly.status == 'waiting' and not player.card_type:
                return redirect('games:monopoly_shop', monopoly_id=monopoly.id)
            return redirect('games:monopoly_play', monopoly_id=monopoly.id)
        if monopoly.status == 'finished':
            return redirect('games:monopoly_results', monopoly_id=monopoly.id)

    if game.status == 'waiting':
        return redirect('games:detail', game_id=game.id)
    if game.status == 'quiz':
        return redirect('games:play', game_id=game.id)
    if game.status == 'finished':
        return redirect('games:results', game_id=game.id)

    real_score = StudentAnswer.objects.filter(
        student=request.user, question__game=game, is_correct=True
    ).aggregate(s=Sum('question__points'))['s'] or 0
    if real_score != session.quiz_score:
        session.quiz_score = real_score
        session.save()

    if session.is_finished:
        return redirect('games:results', game_id=game.id)

    if not session.maze_data:
        session.generate_personal_maze()
        session.position = {'row': 1, 'col': 1}
        session.save()

    return render(request, 'games/maze.html', {
        'game': game, 'session': session, 'maze_json': session.maze_data,
    })


@login_required
@require_POST
def maze_move(request, game_id):
    game = get_object_or_404(Game, pk=game_id, status='maze')
    session = get_object_or_404(GameSession, game=game, student=request.user)

    if session.is_finished:
        return JsonResponse({'error': 'already_finished'}, status=400)

    COOLDOWN_SECONDS = 3
    now = timezone.now()
    if session.last_move_at:
        elapsed = (now - session.last_move_at).total_seconds()
        if elapsed < COOLDOWN_SECONDS:
            return JsonResponse({
                'error': 'cooldown',
                'cooldown_remaining': round(COOLDOWN_SECONDS - elapsed, 1),
            }, status=429)

    action = request.POST.get('action', 'step')
    direction = request.POST.get('direction')

    COSTS = {'step': 1, 'long': 3, 'super': 5, 'teleport': 35}
    STEPS = {'step': 1, 'long': 2, 'super': 3}

    if action not in COSTS:
        return JsonResponse({'error': 'invalid_action'}, status=400)

    cost = COSTS[action]
    if session.remaining_points < cost:
        return JsonResponse({
            'error': 'not_enough_points',
            'remaining': session.remaining_points,
        }, status=400)

    maze = session.maze_data
    if not maze:
        return JsonResponse({'error': 'no_maze'}, status=400)

    rows, cols = len(maze), len(maze[0])
    row = session.position.get('row', 1)
    col = session.position.get('col', 1)

    new_row, new_col = row, col

    if action == 'teleport':
        free_cells = []
        for r in range(rows):
            for c in range(cols):
                if maze[r][c] == 0:
                    continue
                if r == row and c == col:
                    continue
                free_cells.append((r, c))
        if not free_cells:
            return JsonResponse({'error': 'no_free_cells'}, status=400)
        new_row, new_col = random.choice(free_cells)
    else:
        delta = {
            'up': (-1, 0), 'down': (1, 0),
            'left': (0, -1), 'right': (0, 1),
        }.get(direction)
        if not delta:
            return JsonResponse({'error': 'invalid_direction'}, status=400)

        def is_walkable(r, c):
            if r < 0 or r >= rows or c < 0 or c >= cols:
                return False
            return maze[r][c] != 0

        for _ in range(STEPS[action]):
            nr = new_row + delta[0]
            nc = new_col + delta[1]
            if not is_walkable(nr, nc):
                break
            new_row, new_col = nr, nc

        if new_row == row and new_col == col:
            return JsonResponse({
                'error': 'blocked',
                'position': {'row': row, 'col': col},
            }, status=400)

    session.position = {'row': new_row, 'col': new_col}
    session.spent_points += cost
    session.last_move_at = now

    if maze[new_row][new_col] == 3:
        session.is_finished = True
        session.finished_at = now

        already_finished = GameSession.objects.filter(
            game=game, is_finished=True, finished_at__lt=now,
        ).count()
        place = already_finished + 1
        BONUS_BY_PLACE = {1: 50, 2: 30, 3: 20}
        session.maze_bonus = BONUS_BY_PLACE.get(place, 5)

    session.save()

    return JsonResponse({
        'position': {'row': new_row, 'col': new_col},
        'spent_points': session.spent_points,
        'remaining': session.remaining_points,
        'is_finished': session.is_finished,
        'cooldown': COOLDOWN_SECONDS,
    })


# ============================================================
# ФИНИШ / РЕЗУЛЬТАТЫ
# ============================================================
@login_required
def game_finish(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    session = get_object_or_404(GameSession, game=game, student=request.user)
    return render(request, 'games/finish.html', {'game': game, 'session': session})


@login_required
def game_results(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    sessions = game.sessions.all()

    sessions = sorted(
        sessions,
        key=lambda s: (-s.total_score, s.finished_at or timezone.now())
    )

    ranked = []
    for i, s in enumerate(sessions, start=1):
        ranked.append({
            'place': i,
            'student': s.student,
            'quiz_score': s.quiz_score,
            'maze_bonus': s.maze_bonus,
            'total_score': s.total_score,
            'spent': s.spent_points,
            'remaining': s.remaining_points,
            'finished_at': s.finished_at,
            'is_finished': s.is_finished,
        })

    return render(request, 'games/results.html', {'game': game, 'ranked': ranked})


# ============================================================
# МОНОПОЛИЯ
# ============================================================
@login_required
def monopoly_create(request, game_id):
    game = get_object_or_404(Game, pk=game_id, created_by=request.user)

    if hasattr(game, 'monopoly'):
        messages.info(request, 'Партия уже создана')
        return redirect('games:monopoly_host', monopoly_id=game.monopoly.id)

    if game.sessions.count() < 2:
        messages.error(request, 'Нужно минимум 2 ученика в игре')
        return redirect('games:manage', game_id=game.id)

    mon = MonopolyGame.objects.create(game=game, status='waiting')

    sessions = game.sessions.all().order_by('joined_at')
    for s in sessions:
        quiz_score = StudentAnswer.objects.filter(
            student=s.student, question__game=game, is_correct=True
        ).aggregate(t=Sum('question__points'))['t'] or 0

        MonopolyPlayer.objects.create(
            monopoly=mon, student=s.student,
            position=0,
            wallet_start=quiz_score,
            has_extra_turn=False,
        )

    messages.success(request, 'Монополия создана! Ученики выбирают карты')
    return redirect('games:monopoly_host', monopoly_id=mon.id)


@login_required
def monopoly_host(request, monopoly_id):
    mon = get_object_or_404(MonopolyGame, pk=monopoly_id)
    if mon.game.created_by != request.user:
        messages.error(request, 'Нет доступа')
        return redirect('games:list')

    players = list(mon.players_ordered())
    current = mon.current_player()

    return render(request, 'games/monopoly_host.html', {
        'monopoly': mon,
        'game': mon.game,
        'players': players,
        'current': current,
        'map': MONOPOLY_MAP,
        'max_position': MONOPOLY_MAX_POSITION,
    })


@login_required
def monopoly_start(request, monopoly_id):
    mon = get_object_or_404(MonopolyGame, pk=monopoly_id)
    if mon.game.created_by != request.user:
        return redirect('games:list')

    if mon.players.count() < 2:
        messages.error(request, 'Нужно минимум 2 игрока')
        return redirect('games:monopoly_host', monopoly_id=mon.id)

    mon.status = 'playing'
    mon.started_at = timezone.now()
    mon.current_turn_index = 0
    mon.turn_number = 0
    mon.save()
    mon.bump_version()

    messages.success(request, 'Игра началась!')
    return redirect('games:monopoly_host', monopoly_id=mon.id)


@login_required
def monopoly_join(request, game_id):
    if not request.user.is_student():
        return redirect('games:list')

    game = get_object_or_404(Game, pk=game_id)
    if not hasattr(game, 'monopoly'):
        messages.error(request, 'Партия не создана')
        return redirect('games:detail', game_id=game.id)

    mon = game.monopoly

    quiz_score = StudentAnswer.objects.filter(
        student=request.user, question__game=game, is_correct=True
    ).aggregate(t=Sum('question__points'))['t'] or 0

    MonopolyPlayer.objects.get_or_create(
        monopoly=mon, student=request.user,
        defaults={'wallet_start': quiz_score, 'has_extra_turn': False},
    )

    messages.success(request, 'Вы подключились к Монополии!')
    return redirect('games:monopoly_shop', monopoly_id=mon.id)


# ============================================================
# МАГАЗИН КАРТ
# ============================================================
@login_required
def monopoly_shop(request, monopoly_id):
    mon = get_object_or_404(MonopolyGame, pk=monopoly_id)
    if not request.user.is_student():
        return redirect('games:list')

    player, _ = MonopolyPlayer.objects.get_or_create(
        monopoly=mon, student=request.user,
        defaults={'wallet_start': 0},
    )

    if player.card_type:
        if mon.status == 'waiting':
            return redirect('games:monopoly_play', monopoly_id=mon.id)

    max_score = mon.game.questions.aggregate(s=Sum('points'))['s'] or 0
    prices = calc_card_prices(max_score)

    quiz_score = StudentAnswer.objects.filter(
        student=request.user, question__game=mon.game, is_correct=True
    ).aggregate(t=Sum('question__points'))['t'] or 0

    if player.wallet_start != quiz_score:
        player.wallet_start = quiz_score
        player.save()

    cards = []
    for card_id in [CARD_SHIELD, CARD_DOUBLE, CARD_SEVEN]:
        info = CARD_INFO[card_id]
        price = prices[card_id]
        percent = int(round(price / max_score * 100)) if max_score else 0
        cards.append({
            'id': card_id,
            'name': info['name'],
            'emoji': info['emoji'],
            'desc': info['desc'],
            'price': price,
            'percent': percent,
            'affordable': player.wallet >= price,
        })

    return render(request, 'games/monopoly_shop.html', {
        'monopoly': mon,
        'player': player,
        'cards': cards,
        'wallet': player.wallet,
        'max_score': max_score,
        'game': mon.game,
    })


@login_required
@require_POST
def monopoly_buy_card(request, monopoly_id):
    mon = get_object_or_404(MonopolyGame, pk=monopoly_id)
    if not request.user.is_student():
        return JsonResponse({'error': 'not_student'}, status=400)

    player = get_object_or_404(
        MonopolyPlayer, monopoly=mon, student=request.user
    )

    if player.card_type:
        return JsonResponse({'error': 'already_bought'}, status=400)

    card_type = request.POST.get('card_type', '')
    if card_type not in [CARD_SHIELD, CARD_DOUBLE, CARD_SEVEN]:
        return JsonResponse({'error': 'invalid_card'}, status=400)

    max_score = mon.game.questions.aggregate(s=Sum('points'))['s'] or 0
    prices = calc_card_prices(max_score)
    price = prices[card_type]

    if player.wallet < price:
        return JsonResponse({
            'error': 'not_enough_points',
            'wallet': player.wallet,
            'price': price,
        }, status=400)

    player.points_spent += price
    player.card_type = card_type
    player.card_used = False
    player.save()

    ScoreTransaction.objects.create(
        student=request.user,
        teacher=mon.game.created_by,
        points=-price,
        reason='manual',
        comment=f'🛒 Карта: {CARD_INFO[card_type]["name"]}',
    )

    mon.bump_version()

    return JsonResponse({
        'ok': True,
        'card_type': card_type,
        'wallet_after': player.wallet,
    })


# ============================================================
# БРОСОК КУБИКА
# ============================================================
@login_required
@require_POST
def monopoly_roll(request, monopoly_id):
    mon = get_object_or_404(MonopolyGame, pk=monopoly_id, status='playing')
    player = get_object_or_404(MonopolyPlayer, monopoly=mon, student=request.user)

    current = mon.current_player()
    if current is None or current.id != player.id:
        return JsonResponse({'error': 'not_your_turn'}, status=400)

    if player.is_finished:
        return JsonResponse({'error': 'already_finished'}, status=400)

    applied_card = None

    if player.has_extra_turn:
        player.has_extra_turn = False
        applied_card = CARD_DOUBLE
        dice = random.randint(1, 6)

    elif player.card_type == CARD_SEVEN and not player.card_used:
        dice = 7
        applied_card = CARD_SEVEN
        player.card_used = True

    else:
        dice = random.randint(1, 6)

    player.dice_value = dice
    old_pos = player.position

    pos_after_dice = min(old_pos + dice, MONOPOLY_MAX_POSITION)
    cell_after_dice = MONOPOLY_MAP[pos_after_dice]
    cell_type_after_dice = cell_after_dice['type']

    final_pos = pos_after_dice
    final_cell_type = cell_type_after_dice
    modifier = 0
    modifier_type = 'none'

    player.position = pos_after_dice
    player.last_event = cell_after_dice['label']

    if cell_type_after_dice == 'boost':
        modifier = cell_after_dice.get('effect', 3)
        modifier_type = 'boost'
        final_pos = min(pos_after_dice + modifier, MONOPOLY_MAX_POSITION)
        player.position = final_pos
        player.last_event = f'⚡ Ускорение +{modifier}'
        final_cell_type = MONOPOLY_MAP[final_pos]['type']

    elif cell_type_after_dice == 'trap':
        modifier = cell_after_dice.get('effect', -2)
        modifier_type = 'trap'

        if player.card_type == CARD_SHIELD and not player.card_used:
            player.card_used = True
            modifier_type = 'shield'
            final_pos = pos_after_dice
            player.last_event = '🛡 Щит спас от ловушки!'
        else:
            final_pos = max(pos_after_dice + modifier, 0)
            player.position = final_pos
            player.last_event = f'💀 Ловушка {modifier}'
            final_cell_type = MONOPOLY_MAP[final_pos]['type']

    elif cell_type_after_dice == 'bonus':
        bonus_value = cell_after_dice.get('effect', 5)
        player.last_event = f'🎁 Бонус +{bonus_value}'
        ScoreTransaction.objects.create(
            student=player.student,
            teacher=mon.game.created_by,
            points=bonus_value,
            reason='manual',
            comment='🎁 Бонус в Монополии',
        )

    elif cell_type_after_dice == 'swap':
        others = [p for p in mon.players_ordered() if p.id != player.id]
        if others:
            last = others[-1]
            player.position, last.position = last.position, player.position
            last.save()
            final_pos = player.position
        player.last_event = '🔄 Обмен местами'
        final_cell_type = MONOPOLY_MAP[final_pos]['type']

    # ============ ФИНИШ (как в старой логике) ============
    if final_cell_type == 'finish' or player.position >= MONOPOLY_MAX_POSITION:
        player.position = MONOPOLY_MAX_POSITION
        player.is_finished = True
        player.finished_at = timezone.now()
        player.last_event = '🏆 ФИНИШ!'
        mon.status = 'finished'          # игра завершается сразу
        mon.finished_at = timezone.now()
        mon.save()
        ScoreTransaction.objects.create(
            student=player.student,
            teacher=mon.game.created_by,
            points=100,
            reason='manual',
            comment='🏆 Победа в Монополии',
        )

    if player.card_type == CARD_DOUBLE and not player.card_used:
        player.card_used = True
        player.has_extra_turn = True

    # Счётчик ходов игрока (для анимации у других клиентов)
    player.move_seq += 1
    player.save()

    if mon.status == 'playing' and not player.has_extra_turn:
        mon.next_turn()

    # Версия состояния — все клиенты увидят изменение
    mon.bump_version()

    return JsonResponse({
        'dice': dice,
        'from': old_pos,
        'pos_after_dice': pos_after_dice,
        'cell_type_after_dice': cell_type_after_dice,
        'cell_label_after_dice': cell_after_dice['label'],
        'modifier_type': modifier_type,
        'modifier': modifier,
        'to': player.position,
        'cell_type': final_cell_type,
        'cell_label': MONOPOLY_MAP[player.position]['label'],
        'is_finished': player.is_finished,
        'applied_card': applied_card,
        'wallet': player.wallet,
        'has_extra_turn': player.has_extra_turn,
    })


@login_required
def monopoly_state(request, monopoly_id):
    mon = get_object_or_404(MonopolyGame, pk=monopoly_id)
    players = list(mon.players_ordered())
    current = mon.current_player()

    me = next((p for p in players if p.student_id == request.user.id), None)

    return JsonResponse({
        'status': mon.status,
        'state_version': mon.state_version,
        'turn_number': mon.turn_number,
        'current_player_id': current.id if current else None,
        'current_player_name': (current.student.get_full_name() or current.student.username) if current else None,
        'my_wallet': me.wallet if me else 0,
        'my_card_type': me.card_type if me else '',
        'my_card_used': me.card_used if me else False,
        'my_has_extra_turn': me.has_extra_turn if me else False,
        'players': [
            {
                'id': p.id,
                'name': p.student.get_full_name() or p.student.username,
                'username': p.student.username,
                'emoji': p.student.avatar_emoji or '🧑',
                'avatar': p.student.avatar.url if p.student.avatar else None,
                'position': p.position,
                'dice_value': p.dice_value,
                'last_event': p.last_event,
                'card_type': p.card_type,
                'card_used': p.card_used,
                'has_extra_turn': p.has_extra_turn,
                'is_finished': p.is_finished,
                'move_seq': p.move_seq,
            }
            for p in players
        ],
    })


@login_required
def monopoly_play(request, monopoly_id):
    mon = get_object_or_404(MonopolyGame, pk=monopoly_id)

    if mon.status == 'finished':
        return redirect('games:monopoly_results', monopoly_id=mon.id)

    player, _ = MonopolyPlayer.objects.get_or_create(
        monopoly=mon, student=request.user,
        defaults={'wallet_start': 0},
    )

    if mon.status == 'waiting' and not player.card_type:
        return redirect('games:monopoly_shop', monopoly_id=mon.id)

    players = list(mon.players_ordered())
    current = mon.current_player()

    card_info = CARD_INFO.get(player.card_type, None)

    return render(request, 'games/monopoly_play.html', {
        'monopoly': mon,
        'player': player,
        'players': players,
        'current': current,
        'map': MONOPOLY_MAP,
        'max_position': MONOPOLY_MAX_POSITION,
        'card_info': card_info,
    })


@login_required
def monopoly_results(request, monopoly_id):
    mon = get_object_or_404(MonopolyGame, pk=monopoly_id)
    players = list(mon.players_ordered())
    players.sort(key=lambda p: (
        not p.is_finished,
        p.finished_at or timezone.now(),
        -p.position,
    ))

    return render(request, 'games/monopoly_results.html', {
        'monopoly': mon,
        'players': players,
    })