from django.urls import path
from . import views

app_name = 'scores'

urlpatterns = [
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('give/<int:student_id>/', views.give_points, name='give_points'),
]