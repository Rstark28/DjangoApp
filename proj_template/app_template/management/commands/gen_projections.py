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
import random
from geopy.distance import geodesic

class Command(BaseCommand):
    help = 'Updates/Generates the projections'

        
    def handle(self, *args, **kwargs):
        
        
        kFactor = 20
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
        def addWin(winner: str, loser: str, df: pd.DataFrame, divisionDict: dict):
            df.loc[winner, 'TotWins'] +=  1 
            winnerDiv = divisionDict[winner]
            loserDiv = divisionDict[loser]
            if winnerDiv == loserDiv:
                df.loc[winner, 'DivWins'] += 1
                df.loc[winner, 'ConfWins'] += 1
            elif winnerDiv.split()[0] == loserDiv.split()[0]:
                df.loc[winner, 'ConfWins'] += 1
            
            df.loc[winner, 'TeamsBeat'] += f";{loser}"
            df.loc[loser, 'TeamsLostTo'] += f";{winner}"
            
        def adjustElo(winner: str, loser: str, winnerOdds: float):
            pass
        divisionDict = {
            "Buffalo Bills": "AFC East",
            "Miami Dolphins": "AFC East",
            "New England Patriots": "AFC East",
            "New York Jets": "AFC East",
            "Baltimore Ravens": "AFC North",
            "Cincinnati Bengals": "AFC North",
            "Cleveland Browns": "AFC North",
            "Pittsburgh Steelers": "AFC North",
            "Houston Texans": "AFC South",
            "Indianapolis Colts": "AFC South",
            "Jacksonville Jaguars": "AFC South",
            "Tennessee Titans": "AFC South",
            "Denver Broncos": "AFC West",
            "Kansas City Chiefs": "AFC West",
            "Las Vegas Raiders": "AFC West",
            "Los Angeles Chargers": "AFC West",
            "Dallas Cowboys": "NFC East",
            "New York Giants": "NFC East",
            "Philadelphia Eagles": "NFC East",
            "Washington Commanders": "NFC East",
            "Chicago Bears": "NFC North",
            "Detroit Lions": "NFC North",
            "Green Bay Packers": "NFC North",
            "Minnesota Vikings": "NFC North",
            "Atlanta Falcons": "NFC South",
            "Carolina Panthers": "NFC South",
            "New Orleans Saints": "NFC South",
            "Tampa Bay Buccaneers": "NFC South",
            "Arizona Cardinals": "NFC West",
            "Los Angeles Rams": "NFC West",
            "San Francisco 49ers": "NFC West",
            "Seattle Seahawks": "NFC West"
        }   
        
        
        
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
        
        
        games = UpcomingGames.objects.all().filter(isComplete=False)
        for i in range(1, 18):
            weeklyGames = games.filter(week=i)
            for game in weeklyGames:
                homeTeam = game.homeTeam
                awayTeam = game.awayTeam
                homeTeamName = homeTeam.team_name
                awayTeamName = awayTeam.team_name
                homeOdds = getHomeOddsStandard(game, trackerDF)
                randNumber = random.random()
                if randNumber < homeOdds:
                    addWin(homeTeamName, awayTeamName, trackerDF, divisionDict)
                    adjustElo(homeTeamName, awayTeamName, homeOdds)
                else:
                    addWin(awayTeamName, homeTeamName, trackerDF, divisionDict)
                    adjustElo(awayTeamName, homeTeamName, 1 - homeOdds)
                    
        trackerDF.to_csv("test.csv", mode='w+', index=False)  
                
        