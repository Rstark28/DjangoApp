from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='main.home'),

    path('live_projections/', views.live_projections, name='main.live_projections'),
    path('historical_data/', views.historical_data, name='main.historical_data'),

    path('register/', views.register, name='main.register'),
    path('login/', views.user_login, name='main.login'),
    path('logout/', views.logout_view, name='main.logout'),

    path('profile/', views.profile, name='main.profile'),

    path('reset_password/', views.CustomPasswordResetView.as_view(template_name="main/password_reset.html"), name="reset_password"),
    path('reset_password_sent/', auth_views.PasswordResetDoneView.as_view(template_name="main/password_reset_sent.html"), name="password_reset_done"),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name="main/password_reset_form.html"), name="password_reset_confirm"),
    path('reset_password_complete/', auth_views.PasswordResetCompleteView.as_view(template_name="main/password_reset_complete.html"), name="password_reset_complete"),
]
