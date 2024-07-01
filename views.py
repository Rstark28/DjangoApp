from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth import authenticate, login as auth_login, logout
from django.shortcuts import render, redirect, get_object_or_404
from .forms import CreateUserForm, CustomPasswordResetForm
from .models import NFLTeam
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
        selected_team = NFLTeam.objects.get(abbreviation=team_abbreviation)
        historical_games = selected_team.historical_games.all().values('date', 'elo1_post', 'season')

    context = {
        'nfl_teams': NFLTeam.objects.all(),
        'selected_team': selected_team,
        'historical_games': list(historical_games),
    }
    return render(request, 'app_template/historical_data.html', context)

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

    context = {'form': form}
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
