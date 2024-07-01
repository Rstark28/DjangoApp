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
import pandas as pd
import numpy as np

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
        
        #Created To Avoid Modifying the Team Class   
        trackerList = {team.team_name: {
            'Elo': team.elo,
            'TotWins': team.totWins,
            'DivWins': team.divWins,
            'ConfWins': team,
            'TeamsLostTo': [],
            'TeamsBeat': []
        } for team in teams}
        
        trackerDF = pd.DataFrame(columns=['Team', 'Elo', 'TotWins', 'DivWins', 'ConfWins', 'TeamsLostTo', 'TeamsBeat'])
        trackerDF.set_index('Team', inplace=True)
        for team in teams:
            name = team.team_name
            trackerDF.loc[name, 'Team'] = name
            trackerDF.loc[name, 'Elo'] = team.elo
            trackerDF.loc[name, 'ConfWins'] = team.confWins
            trackerDF.loc[name, 'TotWins'] = team.totWins
            trackerDF.loc[name, 'DivWins'] = team.divWins
            trackerDF.loc[name, 'TeamsLostTo'] = ''
            trackerDF.loc[name, 'TeamsBeat'] = ''
        trackerDF.to_csv("test.csv", mode='w+', index=False)  
        
        games = UpcomingGames.objects.all().filter(isComplete=False)
        for i in range(1, 18):
            ...
        