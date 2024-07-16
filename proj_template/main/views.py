from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.models import User
from django.db import transaction
import copy

from django.contrib.auth import authenticate, login as auth_login, logout
from django.shortcuts import render, redirect, get_object_or_404
from .forms import CreateUserForm, CustomPasswordResetForm
from .models import NFLTeam, Projection, UpcomingGames
from django.http import HttpRequest, HttpResponse
import json

# name:       home
# purpose:    Renders the home page.
# parameters:
# request:    HttpRequest object
# returns:    HttpResponse object rendering 'main/home.html'
def home(request: HttpRequest) -> HttpResponse:

    return render(request, 'main/home.html')

# name:       historical_data
# purpose:    Renders the historical data page.
# parameters:
# request:    HttpRequest object
# returns:    HttpResponse object rendering 'main/historical_data.html'
def historical_data(request):
    team_abbreviation = request.GET.get('team_abbreviation')
    selected_team = None
    historical_games = []

    if team_abbreviation:
        selected_team = get_object_or_404(NFLTeam, abbreviation=team_abbreviation)
        historical_games = list(selected_team.historical_games.values(
            'date', 'elo1_post', 'elo2_post', 'team1', 'team2', 'score1', 'score2', 'elo_prob1', 'elo_prob2', 'playoff', 'season'
        ))

        # Map the correct Elo score based on the selected team
        for game in historical_games:
            if game['team1'] == team_abbreviation:
                game['elo_post'] = game['elo1_post']
            else:
                game['elo_post'] = game['elo2_post']

    context = {
        'nfl_teams': NFLTeam.objects.all(),
        'selected_team': selected_team,
        'historical_games': json.dumps(historical_games, default=str),
    }
    return render(request, 'main/historical_data.html', context)

# name:       live_projections
# purpose:    Renders the live projections page.
# parameters:
# request:    HttpRequest object
# returns:    HttpResponse object rendering 'main/live_projections.html'
def live_projections(request):

    # Ensure user is signed in
    if not request.user.is_authenticated:
        messages.error(request, 'Must be signed in to access this page.')
        return render(request, 'main/home.html')

    # Grab user and teams from db
    currentUser = request.user
    AllTeams = NFLTeam.objects.all()


    selected_teams = request.GET.get('selectedTeams')
    all_projections = selected_teams.split(',') if selected_teams else []
    print(all_projections)
    method = request.method
    
    projectionSet = set(all_projections)
    allGames = UpcomingGames.objects.all()
    allProjections = Projection.objects.select_related('team')
    
    adminUser = User.objects.get(username='admin')
    baseProjections = allProjections.filter(user=adminUser)
    userGames = allGames.filter(user=request.user.id)
    userProjections = allProjections.filter(user=request.user.id)
    baseGames = allGames.filter(user=adminUser)
    
    projections = baseProjections
    
    # Ensure user has game entries if none exist
    

    if len(userGames) == 0 and request.user.id is not None:
        with transaction.atomic():
            for game in baseGames:
                userGame = copy.copy(game)
                userGame.id = None
                userGame.user = request.user
                userGame.save()
        userGames = allGames.filter(user=request.user)
    print(len(userGames))
    '''
    # Generate user projections if none exist
    if len(userProjections) == 0:
        with transaction.atomic():
            for projection in baseProjections:
                userProjection = copy.copy(projection)
                userProjection.id = None
                userProjection.user = request.user.id
                userProjection.save()
        userProjections = allProjections.filter(user=request.user)
    
    # Determine if projections need to be updated
    if len(all_projections) == 0:
        picked = 'No'
        for game in userGames:
            game.isPicked = False
            game.save()
        genProjections = False
    else:
        picked = 'Yes'
        userPicks = {f"{game.teamPicked.name}-{game.week}" for game in userGames.filter(isPicked=True)}
        genProjections = (userPicks != projectionSet)
    
    # Update projections based on user selections
    if genProjections:
        with transaction.atomic():
            gamesToUndo = userPicks - projectionSet
            gamesToDo = projectionSet - userPicks
            
            for game in gamesToUndo:
                gameTeamStr, gameWeek = game.split('-')
                gameTeam = AllTeams.get(name=gameTeamStr)
                gameObject = allGames.get(isPicked=True, week=gameWeek, teamPicked=gameTeam)
                gameObject.isPicked = False
                gameObject.save()
            
            for game in gamesToDo:
                gameTeamStr, gameWeek = game.split('-')
                gameTeam = AllTeams.get(name=gameTeamStr)
                ifHome = allGames.filter(week=gameWeek, homeTeam=gameTeam)
                ifAway = allGames.filter(week=gameWeek, awayTeam=gameTeam)
                
                if ifHome.exists():
                    gameToChange = ifHome.first()
                    gameToChange.isPicked = True
                    gameToChange.teamPicked = gameTeam
                    gameToChange.save()
                elif ifAway.exists():
                    gameToChange = ifAway.first()
                    gameToChange.isPicked = True
                    gameToChange.teamPicked = gameTeam
                    gameToChange.save()
    '''
    sort_by = request.GET.get('sort_by', 'team__name')
    valid_sort_fields = ['team__name', '-team__elo', '-madePlayoffs', '-wonDivision', '-wonConference', '-wonSuperBowl']
    
    if sort_by not in valid_sort_fields:
        sort_by = 'team__name'
    
    projections = projections.order_by(sort_by)
    
    context = {
        'projections': projections,
        'picks': all_projections,
        'len': len(all_projections),
        'method': method
    }
    
    return render(request, 'main/live_projections.html', context)

# name:       register
# purpose:    Handles user registration.
# parameters:
# request:    HttpRequest object
# returns:    HttpResponse object rendering 'main/register.html'
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

    context = {'form': form
               }
    return render(request, 'main/register.html', context)

# name:       user_login
# purpose:    Handles user login.
# parameters:
# request:    HttpRequest object
# returns:    HttpResponse object rendering 'main/login.html'
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


# name:       logout_view
# purpose:    Logs out the current user.
# parameters:
# request:    HttpRequest object
# returns:    HttpResponse redirecting to 'main.home'
def logout_view(request: HttpRequest) -> HttpResponse:

    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect('main.home')


# name:       profile
# purpose:    Renders the user profile page.
# parameters:
# request:    HttpRequest object
# returns:    HttpResponse object rendering 'main/profile.html'
def profile(request: HttpRequest) -> HttpResponse:

    if not request.user.is_authenticated:
        messages.error(request, 'Must be signed in to access this page.')
        return render(request, 'main/home.html')
    return render(request, 'main/profile.html')

class CustomPasswordResetView(PasswordResetView):
    form_class = CustomPasswordResetForm
