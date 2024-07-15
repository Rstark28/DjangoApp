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

# name:       home
# purpose:    Renders the home page.
# parameters:
# request:    HttpRequest object
# returns:    HttpResponse object rendering 'app_template/home.html'
def home(request: HttpRequest) -> HttpResponse:

    return render(request, 'app_template/home.html')

# name:       historical_data
# purpose:    Renders the historical data page.
# parameters:
# request:    HttpRequest object
# returns:    HttpResponse object rendering 'app_template/historical_data.html'
def historical_data(request):
    team_abbreviation = request.GET.get('team_abbreviation')
    selected_team = None
    historical_games = []

    if team_abbreviation:
        selected_team = get_object_or_404(NFLTeam, abbreviation=team_abbreviation)
        historical_games = selected_team.historical_games.values('date', 'elo1_post', 'season')

    context = {
        'nfl_teams': NFLTeam.objects.all(),
        'selected_team': selected_team,
        'historical_games': list(historical_games),
    }
    return render(request, 'app_template/historical_data.html', context)

# name:       live_projections
# purpose:    Renders the live projections page.
# parameters:
# request:    HttpRequest object
# returns:    HttpResponse object rendering 'app_template/live_projections.html'
def live_projections(request):
    currentUser = request.user
    AllTeams = NFLTeam.objects.all()

    
    week1_projection = request.POST.getlist('week1[]')
    week2_projection = request.POST.getlist('week2[]')
    week3_projection = request.POST.getlist('week3[]')
    all_projections = week1_projection + week2_projection + week3_projection
    method = request.method
    
    projectionSet = set(all_projections)
    allGames = UpcomingGames.objects.all()
    allProjections = Projection.objects.select_related('team')
    
    adminUser = User.objects.get(username='admin')
    baseProjections = allProjections.filter(user=adminUser)
    userGames = allGames.filter(user=request.user.id, isPicked=True)
    userProjections = allProjections.filter(user=request.user.id)
    baseGames = allGames.filter(user=adminUser)
    
    projections = baseProjections
    
    # Ensure user has game entries if none exist
    '''
    if len(userGames) == 0:
        with transaction.atomic():
            for game in baseGames:
                userGame = copy.copy(game)
                userGame.id = None
                userGame.user = request.user
                userGame.save()
        userGames = allGames.filter(user=request.user)
    
    # Generate user projections if none exist
    if len(userProjections) == 0:
        with transaction.atomic():
            for projection in baseProjections:
                userProjection = copy.copy(projection)
                userProjection.id = None
                userProjection.user = request.user
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
    
    return render(request, 'app_template/live_projections.html', context)

# name:       register
# purpose:    Handles user registration.
# parameters:
# request:    HttpRequest object
# returns:    HttpResponse object rendering 'app_template/register.html'
def register(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, 'Registration successful. You are now logged in.')
            return redirect('app_template.home')
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
    return render(request, 'app_template/register.html', context)

# name:       user_login
# purpose:    Handles user login.
# parameters:
# request:    HttpRequest object
# returns:    HttpResponse object rendering 'app_template/login.html'
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
                return redirect('app_template.home')
            else:
                messages.error(request, 'Invalid username or password')
        else:
            messages.error(request, 'Invalid username or password')
    else:
        form = AuthenticationForm()

    context = {'form': form}
    return render(request, 'app_template/login.html', context)


# name:       logout_view
# purpose:    Logs out the current user.
# parameters:
# request:    HttpRequest object
# returns:    HttpResponse redirecting to 'app_template.home'
def logout_view(request: HttpRequest) -> HttpResponse:

    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect('app_template.home')


# name:       profile
# purpose:    Renders the user profile page.
# parameters:
# request:    HttpRequest object
# returns:    HttpResponse object rendering 'app_template/profile.html'
def profile(request: HttpRequest) -> HttpResponse:

    return render(request, 'app_template/profile.html')

class CustomPasswordResetView(PasswordResetView):
    form_class = CustomPasswordResetForm
