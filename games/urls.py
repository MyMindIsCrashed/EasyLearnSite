from django.urls import path
from . import views

app_name = 'games'

urlpatterns = [
    path('', views.game_list, name='list'),
    path('create/', views.game_create, name='create'),
    path('join/', views.game_join, name='join'),

    path('<int:game_id>/manage/', views.game_manage, name='manage'),
    path('<int:game_id>/start-quiz/', views.start_quiz, name='start_quiz'),
    path('<int:game_id>/start-maze/', views.start_maze, name='start_maze'),

    path('<int:game_id>/', views.game_detail, name='detail'),
    path('<int:game_id>/play/', views.game_play, name='play'),
    path('<int:game_id>/quiz-done/', views.quiz_done, name='quiz_done'),
    path('<int:game_id>/maze/', views.maze_view, name='maze'),
    path('<int:game_id>/maze/move/', views.maze_move, name='maze_move'),
    path('<int:game_id>/finish/', views.game_finish, name='finish'),
    path('<int:game_id>/results/', views.game_results, name='results'),

    path('question/<int:question_id>/answer/', views.answer_question, name='answer'),
    path('<int:game_id>/question/add/', views.question_add, name='question_add'),
    path('question/<int:question_id>/edit/', views.question_edit, name='question_edit'),
    path('question/<int:question_id>/delete/', views.question_delete, name='question_delete'),

    # Монополия
    path('<int:game_id>/monopoly/create/', views.monopoly_create, name='monopoly_create'),
    path('<int:game_id>/monopoly/join/', views.monopoly_join, name='monopoly_join'),
    path('monopoly/<int:monopoly_id>/host/', views.monopoly_host, name='monopoly_host'),
    path('monopoly/<int:monopoly_id>/start/', views.monopoly_start, name='monopoly_start'),
    path('monopoly/<int:monopoly_id>/shop/', views.monopoly_shop, name='monopoly_shop'),
    path('monopoly/<int:monopoly_id>/buy/', views.monopoly_buy_card, name='monopoly_buy_card'),
    path('monopoly/<int:monopoly_id>/play/', views.monopoly_play, name='monopoly_play'),
    path('monopoly/<int:monopoly_id>/roll/', views.monopoly_roll, name='monopoly_roll'),
    path('monopoly/<int:monopoly_id>/state/', views.monopoly_state, name='monopoly_state'),
    path('monopoly/<int:monopoly_id>/results/', views.monopoly_results, name='monopoly_results'),
]