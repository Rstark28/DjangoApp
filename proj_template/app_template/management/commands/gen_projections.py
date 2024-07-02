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
        
        
        kFactor = 20.0
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
        def addWin(winner: str, loser: str, df: pd.DataFrame):
            df.loc[winner, 'TotWins'] +=  1 
            winnerDiv = df.loc[winner, 'Division']
            loserDiv = df.loc[loser, 'Division']
            if winnerDiv == loserDiv:
                df.loc[winner, 'DivWins'] += 1
                df.loc[winner, 'ConfWins'] += 1
            elif winnerDiv.split()[0] == loserDiv.split()[0]:
                df.loc[winner, 'ConfWins'] += 1

            if df.loc[winner, 'TeamsBeat'] == '':
                df.loc[winner, 'TeamsBeat'] += f"{loser}"
            else:
                df.loc[winner, 'TeamsBeat'] += f";{loser}"
                
            if df.loc[loser, 'TeamsLostTo'] == '':
                df.loc[loser, 'TeamsLostTo'] = loser
            else:
                df.loc[loser, 'TeamsLostTo'] += f";{winner}"
            
        def adjustElo(winner: str, loser: str, winnerOdds: float, kFactor: float, df: pd.DataFrame):
            proportion = 1 - winnerOdds
            change = proportion * kFactor
            df.loc[winner, 'Elo'] += change
            df.loc[loser, 'Elo'] -= change
            
            
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
            trackerDF.loc[name, 'Division'] = divisionDict[name]
            trackerDF.loc[name, 'Seed'] = -1
            trackerDF.loc[name, 'Playoff Round'] = 'None'
        
        
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
                    addWin(homeTeamName, awayTeamName, trackerDF)
                    adjustElo(homeTeamName, awayTeamName, homeOdds, kFactor, trackerDF)
                else:
                    addWin(awayTeamName, homeTeamName, trackerDF)
                    adjustElo(awayTeamName, homeTeamName, 1 - homeOdds, kFactor, trackerDF)
        
        AFCEast = trackerDF[trackerDF['Division'] == 'AFC East']['Team'].to_list()
        AFCWest = trackerDF[trackerDF['Division'] == 'AFC West']['Team'].to_list()
        AFCNorth = trackerDF[trackerDF['Division'] == 'AFC North']['Team'].to_list()
        AFCSouth = trackerDF[trackerDF['Division'] == 'AFC South']['Team'].to_list()
        
        NFCEast = trackerDF[trackerDF['Division'] == 'NFC East']['Team'].to_list()
        NFCWest = trackerDF[trackerDF['Division'] == 'NFC West']['Team'].to_list()
        NFCSouth = trackerDF[trackerDF['Division'] == 'NFC South']['Team'].to_list()
        NFCNorth = trackerDF[trackerDF['Division'] == 'NFC North']['Team'].to_list()
        
        AllDivisions = [AFCEast, AFCWest, AFCNorth, AFCSouth, NFCEast, NFCWest, NFCSouth, NFCNorth]
        
        AFC = AFCNorth + AFCEast + AFCWest + AFCSouth
        NFC = NFCNorth + NFCEast + NFCWest + NFCSouth
        
        AFCDivisionWinners = []
        NFCDivisionWinners = []
        
        def divBreakTieHelper(tied: list[str], div: list[str], df: pd.DataFrame):
            
            if len(tied) == 1:
                return tied[0]
            
            tiedOrig = len(tied)
            
            commonScore = {team: 0 for team in tied}
            for i in range(len(tied)):
                team = tied[i]
                teamsBeat = df.loc[team, 'TeamsBeat'].split(';')
                teamsLost = df.loc[team, 'TeamsLostTo'].split(';')
                otherTeams = tied[:i] + tied[i+1:]
                for otherTeam in otherTeams:
                    commonScore[team] += teamsBeat.count(otherTeam)
                    commonScore[team] -= teamsLost.count(otherTeam)
            
            tied.sort(key=lambda x: -commonScore[x])
            
            highest = tied[0]
            tied = [team for team in tied if commonScore[team] == commonScore[highest]]
            if tiedOrig > len(tied):
                return divBreakTieHelper(tied, div, df)
            
            tied.sort(key = lambda x: -df.loc[x, 'DivWins'])
            highest = tied[0]
            tied = [team for team in tied if commonScore[team] == commonScore[highest]]
            if tiedOrig > len(tied):
                return divBreakTieHelper(tied, div, df)
            
            tied.sort(key = lambda x: -df.loc[x, 'ConfWins'])
            highest = tied[0]
            tied = [team for team in tied if commonScore[team] == commonScore[highest]]
            if tiedOrig > len(tied):
                return divBreakTieHelper(tied, div, df)
            
            return random.choice(tied)
            
        
        
        
            
            
            
        
                
            
        
        def divTieBreaker(div: list[str], df: pd.DataFrame) -> str:
            firstPlace = div[0]
            tiedForFirst = [firstPlace]
            for team in div[1:]:
                if df.loc[team, 'TotWins'] == df.loc[firstPlace, 'TotWins']:
                    tiedForFirst.append(team)
            winner = divBreakTieHelper(tiedForFirst, div, df)
            return winner
                
         
        for div in AllDivisions:
            div.sort(key=lambda x: -trackerDF.loc[x, 'TotWins'])
            winner = divTieBreaker(div, trackerDF)
            trackerDF.loc[winner, 'Seed'] = 1
            if (trackerDF.loc[winner, 'Division'].split())[0] == 'AFC':
                AFCDivisionWinners.append(winner)
            else:
                NFCDivisionWinners.append(winner)
            
        AFCWildcard = list(set(AFC) - set(AFCDivisionWinners))
        NFCWildcard = list(set(NFC) - set(NFCDivisionWinners))
                    
        trackerDF.to_csv("test.csv", mode='w+', index=False)  
                
        