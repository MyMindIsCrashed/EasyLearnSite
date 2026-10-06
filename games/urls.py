from django.urls import path
from . import views

app_name = 'games'

urlpatterns = [
    path('', views.game_list, name='list'),
    path('create/', views.game_create, name='create'),
    path('<int:game_id>/', views.game_detail, name='detail'),
    path('<int:game_id>/start/', views.game_start, name='start'),
    path('question/<int:question_id>/answer/', views.answer_question, name='answer'),
    path('<int:game_id>/finish/', views.game_finish, name='finish'),
]