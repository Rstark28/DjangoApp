# from django_app/views.py

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordResetView
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse
import json
import copy

from .forms import CreateUserForm, CustomPasswordResetForm
from .models import NFLTeam, Projection, UpcomingGames

def home(request: HttpRequest) -> HttpResponse:
    return render(request, 'main/home.html')

def historical_data(request: HttpRequest) -> HttpResponse:
    team_abbreviation = request.GET.get('team_abbreviation')
    selected_team = None
    historical_games = []

    if team_abbreviation:
        selected_team = get_object_or_404(NFLTeam, abbreviation=team_abbreviation)
        historical_games = list(selected_team.historical_games.values(
            'date', 'elo1_post', 'elo2_post', 'team1', 'team2', 'score1', 'score2', 'elo_prob1', 'elo_prob2', 'playoff', 'season'
        ))

        for game in historical_games:
            game['elo_post'] = game['elo1_post'] if game['team1'] == team_abbreviation else game['elo2_post']

    context = {
        'nfl_teams': NFLTeam.objects.all(),
        'selected_team': selected_team,
        'historical_games': json.dumps(historical_games, default=str),
    }
    return render(request, 'main/historical_data.html', context)

def live_projections(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        messages.error(request, 'Must be signed in to access this page.')
        return render(request, 'main/home.html')

    current_user = request.user
    all_teams = NFLTeam.objects.all()

    selected_teams = request.GET.get('selected_teams')
    all_projections = selected_teams.split(',') if selected_teams else []
    method = request.method
    
    projection_set = set(all_projections)
    all_games = UpcomingGames.objects.all()
    all_projections = Projection.objects.select_related('team')
    
    admin_user = User.objects.get(username='admin')
    base_projections = all_projections.filter(user=admin_user)
    user_games = all_games.filter(user=request.user.id)
    user_projections = all_projections.filter(user=request.user.id)
    base_games = all_games.filter(user=admin_user)
    
    projections = base_projections
    

    if len(user_games) == 0 and request.user.id is not None:
        with transaction.atomic():
            for game in base_games:
                user_game = copy.copy(game)
                user_game.id = None
                user_game.user = request.user
                user_game.save()
        user_games = all_games.filter(user=request.user)

    sort_by = request.GET.get('sort_by', 'team__name')
    valid_sort_fields = ['team__name', '-team__elo', '-made_playoffs', '-won_division', '-won_conference', '-won_super_bowl']
    
    if sort_by not in valid_sort_fields:
        sort_by = 'team__name'
    
    projections = projections.order_by(sort_by)
    print(projections.first().made_playoffs)
    context = {
        'projections': projections,
        'picks': all_projections,
        'len': len(all_projections),
        'method': method
    }
    return render(request, 'main/live_projections.html', context)

def register(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, 'Registration successful. You are now logged in.')
            return redirect('main.home')
        else:
            for field in form:
                for error in field.errors:
                    messages.error(request, error)
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = CreateUserForm()

    context = {'form': form}
    return render(request, 'main/register.html', context)

def user_login(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                auth_login(request, user)
                messages.success(request, "Logged in successfully!")
                return redirect('main.home')
            else:
                messages.error(request, 'Invalid username or password')
        else:
            messages.error(request, 'Invalid username or password')
    else:
        form = AuthenticationForm()

    context = {'form': form}
    return render(request, 'main/login.html', context)

def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect('main.home')

def profile(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        messages.error(request, 'Must be signed in to access this page.')
        return render(request, 'main/home.html')
    return render(request, 'main/profile.html')

class CustomPasswordResetView(PasswordResetView):
    form_class = CustomPasswordResetForm
