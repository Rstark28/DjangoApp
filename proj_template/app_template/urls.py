from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='app_template.home'),

    path('historical_data/', views.historical_data, name='app_template.historical_data'),

    path('register/', views.register, name='app_template.register'),
    path('login/', views.user_login, name='app_template.login'),
    path('logout/', views.logout_view, name='app_template.logout'),

    path('profile/', views.profile, name='app_template.profile'),

    path('reset_password/', views.CustomPasswordResetView.as_view(template_name="app_template/password_reset.html"), name="reset_password"),
    path('reset_password_sent/', auth_views.PasswordResetDoneView.as_view(template_name="app_template/password_reset_sent.html"), name="password_reset_done"),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name="app_template/password_reset_form.html"), name="password_reset_confirm"),
    path('reset_password_complete/', auth_views.PasswordResetCompleteView.as_view(template_name="app_template/password_reset_complete.html"), name="password_reset_complete"),
]
