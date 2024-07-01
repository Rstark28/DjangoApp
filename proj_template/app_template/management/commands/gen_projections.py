from django.core.management.base import BaseCommand
from app_template.models import NFLTeam
from app_template.models import UpcomingGames
from app_template.models import Season
from app_template.models import Projection
from app_template.models import City
import pandas as pd
import requests
from datetime import datetime
from datetime import date

class Command(BaseCommand):
    help = 'Updates/Generates the projections'

        
    def handle(self, *args, **kwargs):
        
        teams = NFLTeam.objects.all()
        cities = City.objects.all()
        
        def getHomeOdds(Game: UpcomingGames, tracker: dict) -> float:
            awayTeam = Game.awayTeam
            homeTeam = Game.homeTeam
            homeName = homeTeam.team_name
            awayName = homeTeam.team_name
            awayElo = tracker[awayName]['Elo']
            homeElo = tracker[homeName]['Elo']
        
        trackerDict = {team.team_name: {
            'Elo': team.elo,
            'TotWins': team.totWins,
            'DivWins': team.divWins,
            'ConfWins': team,
            'TeamsLostTo': [],
            'TeamsBeat': []
        } for team in teams}
        games = UpcomingGames.objects.all().filter(isComplete=False)
        for i in range(17):
            ...
        