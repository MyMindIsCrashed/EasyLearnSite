from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/avatar/delete/', views.profile_delete_avatar, name='profile_delete_avatar'),
    path('user/<int:user_id>/', views.user_profile, name='user_profile'),
]