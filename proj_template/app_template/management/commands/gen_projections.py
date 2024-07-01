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
import math
from geopy.distance import geodesic

class Command(BaseCommand):
    help = 'Updates/Generates the projections'

        
    def handle(self, *args, **kwargs):
        
        teams = NFLTeam.objects.all()
        cities = City.objects.all()
        
        def calculateDistance(city1: float, city2: float) -> float:
            return geodesic(city1, city2).miles
        
        
        def getHomeOddsStandard(Game: UpcomingGames, df: pd.DataFrame) -> float:
            cities = City.objects.all()
            awayTeam = Game.awayTeam
            homeTeam = Game.homeTeam
            homeName = homeTeam.team_name
            awayName = awayTeam.team_name
            awayElo = df.loc[awayName, 'Elo']
            homeElo = df.loc[homeName, 'Elo']
            cityName = Game.city
            homeCityName = ' '.join((homeName.split(' '))[:-1])
            awayCityName = ' '.join((awayName.split(' '))[:-1])
            gameCity = cities.get(name=cityName)
            homeCity = cities.get(name=homeCityName)
            awayCity = cities.get(name=awayCityName)
            gameCords = (gameCity.lat,  gameCity.long)
            homeCords = (homeCity.lat, homeCity.long)
            awayCords = (awayCity.lat, awayCity.long)
            
            homeDistance = calculateDistance(gameCords, homeCords)
            awayDistance = calculateDistance(gameCords, awayCords)
            
            homeDiff = homeElo - awayElo
            if Game.after_bye_home:
                homeDiff += 25
            if Game.after_bye_away:
                homeDiff -= 25
            if not Game.isNeutral:
                homeDiff += 48
            homeDiff -= homeDistance * 4 / 1000
            homeDiff += awayDistance * 4 / 1000
            homeOdds = 1/(10**(-1*homeDiff/400)+1)
            return homeOdds
             
            
            
        
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
            weeklyGames = games.filter(week=i)
            getHomeOdds(weeklyGames.first(), trackerDF)
        