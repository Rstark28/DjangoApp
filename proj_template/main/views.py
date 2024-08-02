from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.models import User
from django.db import transaction
from geopy.distance import geodesic
import pandas as pd
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
    def adjust_elo(tracker_df: pd.DataFrame, winner: str, loser: str, winner_odds: float, k_factor: float) -> None:
        elo_change = (1 - winner_odds) * k_factor
        tracker_df.at[winner, 'elo'] += elo_change
        tracker_df.at[loser, 'elo'] -= elo_change

    def get_city_coordinates(self, city_name: str) -> tuple[float, float]:
        if city_name not in self.city_coordinates_cache:
            city = self.cities.get(name=city_name)
            #city_coordinates_cache[city_name] = (city.latitude, city.longitude) #Define this as variable within scome of functions
       # return self.city_coordinates_cache[city_name]
        return (0.0, 0.0)

    def get_home_odds_standard(game: UpcomingGames) -> float:
        home = game.home_team
        away = game.away_team
        game_coords = get_city_coordinates(game.city)
        home_coords = get_city_coordinates(home.city)
        away_coords = get_city_coordinates(away.city)
        home_distance = geodesic(game_coords, home_coords).miles
        away_distance = geodesic(game_coords, away_coords).miles
        elo_diff = home.elo - away.elo
        if game.after_bye_home:
            elo_diff += 25
        if game.after_bye_away:
            elo_diff -= 25
        if not game.is_neutral:
            elo_diff += 48
        elo_diff -= home_distance * 4 / 1000
        elo_diff += away_distance * 4 / 1000
        home_odds = 1 / (10 ** (-elo_diff / 400) + 1)
        return home_odds


    # Ensure user is signed in
    if not request.user.is_authenticated:
        messages.error(request, 'Must be signed in to access this page.')
        return render(request, 'main/home.html')

    # Grab user and teams from db
    currentUser = request.user
    AllTeams = NFLTeam.objects.all()

    selected_teams = request.GET.get('selectedTeams')
    all_projections = selected_teams.split(',') if selected_teams else []
    method = request.method

    projectionSet = set(all_projections)
    allGames = UpcomingGames.objects.all()
    allProjections = Projection.objects.select_related('team')
    
    adminUser = User.objects.get(username='admin')
    baseProjections = allProjections.filter(user=adminUser)
    print(f"base projections: {len(baseProjections)}")
    userGames = allGames.filter(user=request.user.id)
    userProjections = allProjections.filter(user=request.user.id)
    print(f"user projections: {len(userProjections)}")
    baseGames = allGames.filter(user=adminUser)
    print(f"user games: {len(userGames)}")
    print(f"base games: {len(baseGames)}")
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
        print("Generated User Games")
    print(len(userGames))
    
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
            game.is_picked = False
            game.save()
        genProjections = False
    else:
        picked = 'Yes'
        userPicks = {f"{game.teamPicked.name}-{game.week}" for game in userGames.filter(is_picked=True)}
        genProjections = (userPicks != projectionSet)
    
    # Update projections based on user selections
    if genProjections:
        with transaction.atomic():
            gamesToUndo = userPicks - projectionSet
            gamesToDo = projectionSet - userPicks
            print(gamesToUndo)
            print(gamesToDo)
            
            for game in gamesToUndo:
                print(game)
                gameTeamStr, gameWeek = game.split('-')[0], game.split('-')[1]
                gameTeam = AllTeams.get(name=gameTeamStr)

                if ifHome.exists():
                    gameToChange = ifHome.first()
                    gameToChange.is_picked = True
                    gameToChange.teamPicked = gameTeam if isWin else gameToChange.away_team 
                    gameToChange.save()
                elif ifAway.exists():
                    gameToChange = ifAway.first()
                    gameToChange.is_picked = True
                    gameToChange.teamPicked = gameTeam if isWin else gameToChange.home_team 
                    gameToChange.save()
            
            for game in gamesToDo:
                print(game)
                gameTeamStr, gameWeek = game.split('-')[0], game.split('-')[1]
                isWin = (game.split('-')[2] == 'W')
                gameTeam = AllTeams.get(name=gameTeamStr)
                ifHome = allGames.filter(week=gameWeek, home_team=gameTeam)
                ifAway = allGames.filter(week=gameWeek, away_team=gameTeam)
                
                
                if ifHome.exists():
                    gameToChange = ifHome.first()
                    gameToChange.is_picked = True
                    gameToChange.teamPicked = gameTeam if isWin else gameToChange.away_team 
                    gameToChange.save()
                elif ifAway.exists():
                    gameToChange = ifAway.first()
                    gameToChange.is_picked = True
                    gameToChange.teamPicked = gameTeam if isWin else gameToChange.home_team 
                    gameToChange.save()

    

    sort_by = request.GET.get('sort_by', 'team__name')
    valid_sort_fields = ['team__name', '-team__elo', '-made_playoffs', '-won_division', '-won_conference', '-won_super_bowl']
    
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
