from io import StringIO
from django.core.management.base import BaseCommand
from app_template.models import NFLTeam, UpcomingGames, Season, Projection, City
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

    def __init__(self):

        self.kFactor = 20.0
        self.superBowlCity = 'New Orleans'
        self.teams = NFLTeam.objects.all()
        self.cities = City.objects.all()

        self.divisionDict = {
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
        
    
    def add_arguments(self, parser):

        parser.add_argument(
            '-n', '--num',
            type = int,
            help = 'Number of Simulations',
            default = '3'
        )

    def calculateDistance(self, city1: float, city2: float) -> float:
        return geodesic(city1, city2).miles
    
    #Note: This is non-QB Adjusted, I plan to add a QB-Adjusted model and try 
    #And create another model that takes other positions into account
    def getHomeOddsStandard(self, Game: UpcomingGames, df: pd.DataFrame) -> float:
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
    
        homeDistance = self.calculateDistance(gameCords, homeCords)
        awayDistance = self.calculateDistance(gameCords, awayCords)
        
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
    
    def getPlayoffOddsStandard(self, homeTeam: str, awayTeam: str, df: pd.DataFrame, homeBye: bool = False, isSuperBowl = True) -> float:
        awayElo = df.loc[awayTeam, 'Elo']
        homeElo = df.loc[homeTeam, 'Elo']
        if not isSuperBowl:
            homeCityName = ' '.join((homeTeam.split(' '))[:-1])
        else:
            homeCityName = self.superBowlCity
        awayCityName = ' '.join((awayTeam.split(' '))[:-1])
        homeCity = self.cities.get(name=homeCityName)
        awayCity = self.cities.get(name=awayCityName)
        homeCords = (homeCity.lat, homeCity.long)
        awayCords = (awayCity.lat, awayCity.long)
        
        
        distanceTraveled = self.calculateDistance(homeCords, awayCords)
        homeDiff = (homeElo - awayElo + distanceTraveled * 4 / 1000) 
        if not isSuperBowl: 
            homeDiff += 48
        else: 
            homeTravelCityName = ' '.join((homeTeam.split(' '))[:-1])
            homeTravelCity = self.cities.get(name=homeTravelCityName)
            homeTravelCords = (homeTravelCity.lat, homeTravelCity.long)
            distanceHomeTravels = self.calculateDistance(homeTravelCords, homeCords)
            homeDiff -= distanceHomeTravels * 4 / 1000
            
        if homeBye:
            homeDiff += 25
        homeDiff *= 1.2
        homeOdds = 1/(10**(-1*homeDiff/400)+1)
        return homeOdds
        
    def addWin(self, winner: str, loser: str, df: pd.DataFrame):
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
            df.loc[loser, 'TeamsLostTo'] = winner
        else:
            df.loc[loser, 'TeamsLostTo'] += f";{winner}"    


    def divBreakTieHelper(self, tied: list[str], div: list[str], df: pd.DataFrame):
        if len(tied) == 1:
            return tied[0]
        
        tiedOrig = len(tied)
        
        #H2H Tie Breaker
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
            return self.divBreakTieHelper(tied, div, df)
        
        #Divisional Tie Breaker
        tied.sort(key = lambda x: -df.loc[x, 'DivWins'])
        highest = tied[0]
        tied = [team for team in tied if commonScore[team] == commonScore[highest]]
        if tiedOrig > len(tied):
            return self.divBreakTieHelper(tied, div, df)
        
        #Conference Tie Breaker
        tied.sort(key = lambda x: -df.loc[x, 'ConfWins'])
        highest = tied[0]
        tied = [team for team in tied if commonScore[team] == commonScore[highest]]
        if tiedOrig > len(tied):
            return self.divBreakTieHelper(tied, div, df)
        
        #Random at this point. Unlikely to affect projections early on, and plan 
        #To add other tie breakers later on
        return random.choice(tied)
        
    def divTieBreaker(self, div: list[str], df: pd.DataFrame) -> str:
        firstPlace = div[0]
        tiedForFirst = [firstPlace]
        for team in div[1:]:
            if df.loc[team, 'TotWins'] == df.loc[firstPlace, 'TotWins']:
                tiedForFirst.append(team)
        winner = self.divBreakTieHelper(tiedForFirst, div, df)
        return winner
    
    
    def findTies(self, teams: list[str], isWildCard: bool, df: pd.DataFrame, key) -> list[list[str]]:
        res = []
        currTieList = [teams[0]]
        currWins = key(teams[0])
        for i in range(1, len(teams)):
            team = teams[i]
            if key(team) == currWins:
                currTieList.append(team)
            else:
                res.append(currTieList)
                #Not tracking seeding if not in playoffs
                if (i >= 3) and isWildCard: 
                    return res
                currWins = key(team)
                currTieList = [team]
        res.append(currTieList)

        return res
            
    def resolveTies(self, tie: list[str], df: pd.DataFrame) -> list[str]:
        ogLen = len(tie)
        if ogLen == 1:
            return tie
        sweptIndex = -1
        sweeperIndex = -1
        for i in range(len(tie)):
            team = tie[i]
            teamsBeat = df.loc[team, 'TeamsBeat'].split(';')
            teamsLost = df.loc[team, 'TeamsLostTo'].split(';')
            otherTeams = tie[:i] + tie[i+1:]
            swept = True
            wasSwept = True
            
            for otherTeam in otherTeams:
                if otherTeam not in teamsBeat or otherTeam in teamsLost:
                    swept = False
                if otherTeam in teamsBeat or otherTeam not in teamsLost:
                    swept = True
            
            if swept:
                sweeperIndex = i
            if wasSwept:
                sweptIndex = i
        if sweeperIndex != -1 and sweptIndex != -1:
            return [team[sweeperIndex]] + [team for i, team in enumerate(tie) if i not in {sweeperIndex, sweptIndex}] + [team[sweptIndex]]
        if sweeperIndex != -1:
            return [team[sweeperIndex]] + [team for i, team in enumerate(tie) if i == sweeperIndex]
        if sweptIndex != -1:
            return [team for i, team in enumerate(tie) if i == sweptIndex] + [team[sweptIndex]]
        
        tie.sort(key = lambda x: -df.loc[x, 'ConfWins'])
        
        newTies = self.findTies(tie, False, df, lambda x: df.loc[x, 'ConfWins'])
        if len(newTies) == 1:
            return random.sample(newTies[0], len(newTies[0]))
        res = []
        for tie in newTies:
            res += self.resolveTies(tie)
        return res
                
                
    #Assumes List is already sorted by total wins     
    def seed(self, teams: list[str], df: pd.DataFrame, isWildCard: bool) -> list[str]:
        tieList = self.findTies(teams, isWildCard, df, lambda x: df.loc[x, 'TotWins'])
        newList = []
        for tie in tieList:
            tie = self.resolveTies(tie, df)
        for tie in tieList:
            newList += tie
            
        if isWildCard:
            shift = 5
        else:
            shift = 1
        for i, team in enumerate(newList):
            df.loc[team, 'Seed'] = i +shift
        
        return newList 
    
    def simRound(self, playoffs: dict, df: pd.DataFrame, round: int, roundDict: dict) -> None:
        if round == 0:
            beginning = 1
            end = 4
        if round == 1:
            beginning = 0
            end = 2
        else:
            beginning = 0
            end = 1
        totalTeams = (beginning - end) * 2
        
        seeds = sorted(list(playoffs.keys()))
        for i in range(beginning, end):
            offBye = i == 0 and round == 2
            HigherSeed = seeds[i]
            j = -1-i
            LowerSeed = seeds[j]
            Home = playoffs[HigherSeed]
            Away = playoffs[LowerSeed]
            homeOdds = self.getPlayoffOddsStandard(Home, Away, df, offBye)
            randVar = random.random()
            if randVar < homeOdds:
                winner = Home
                loser = Away
                losingSeed = LowerSeed
            else:
                winner = Away
                loser = Home
                losingSeed = HigherSeed
            self.adjustElo(winner, loser, homeOdds, self.kFactor, df)
            df.loc[winner, 'Playoff Round'] = roundDict[round]
            del playoffs[losingSeed]
            
            
            
        
    def simPlayoffs(self, playoffs: dict, df: pd.DataFrame):
        roundDict = {0: 'Divisional', 1: 'Conference', 2: 'Super Bowl'}
        self.simRound(playoffs, df, 0, roundDict)
        self.simRound(playoffs, df, 1, roundDict)
        self.simRound(playoffs, df, 2, roundDict)
        
    def simSuperBowl(self, NFC: dict, AFC: dict, df: pd.DataFrame) -> None:
        NFCChamp = list(NFC.values())[0]
        AFCChamp = list(AFC.values())[0]
        NFCOdds = self.getPlayoffOddsStandard(AFCChamp, NFCChamp, df, False, isSuperBowl=True)
        randVal = random.random()
        if randVal < NFCOdds:
            winner = NFCChamp
            loser = AFCChamp
        else:
            winner = AFCChamp
            loser = NFCChamp
        self.adjustElo(winner, loser, NFCOdds, self.kFactor, df)
        df.loc[winner, 'Playoff Round'] = "Super Bowl Champ"
        return winner
        
    def adjustElo(self, winner: str, loser: str, winnerOdds: float, kFactor: float, df: pd.DataFrame):
        proportion = 1 - winnerOdds
        change = proportion * kFactor
        df.loc[winner, 'Elo'] += change
        df.loc[loser, 'Elo'] -= change
                        
    def handle(self, *args, **kwargs):

        # Number of simulations to run
        num = kwargs['num']

        # Create a DataFrame to store results with specified columns
        resultsDF = pd.DataFrame(columns=['Team', 'SuperBowl', 'DivChamps', '1Seed', 'Mean', 'Median', '25', '75', 'stdev'])

        # Initialize results DataFrame with team names and zero values
        for team in self.teams:
            resultsDF.loc[team.team_name] = [team.team_name, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

        # Initialize a dictionary to store results for each team
        resultDict = {team.team_name: [] for team in self.teams} 

        for i in range(num):           
            # Initialize a DataFrame to track the current state of the simulation
            trackerDF = pd.DataFrame(columns=['Team', 'Elo', 'TotWins', 'DivWins', 'ConfWins', 'TeamsLostTo', 'TeamsBeat'])
            trackerDF.set_index('Team', inplace=True)
            for team in self.teams:
                name = team.team_name
                trackerDF.loc[name, 'Team'] = name
                trackerDF.loc[name, 'Elo'] = team.elo
                trackerDF.loc[name, 'ConfWins'] = team.confWins
                trackerDF.loc[name, 'TotWins'] = team.totWins
                trackerDF.loc[name, 'DivWins'] = team.divWins
                trackerDF.loc[name, 'TeamsLostTo'] = ''
                trackerDF.loc[name, 'TeamsBeat'] = ''
                trackerDF.loc[name, 'Division'] = self.divisionDict[name]
                trackerDF.loc[name, 'Seed'] = -1
                trackerDF.loc[name, 'Playoff Round'] = 'None'

            # Get the list of upcoming games that are not yet complete
            games = UpcomingGames.objects.all().filter(isComplete=False)
            
            # Simulate each week of games
            for i in range(1, 18):
                weeklyGames = games.filter(week=i)
                
                for game in weeklyGames:
                    homeTeam = game.homeTeam
                    awayTeam = game.awayTeam

                    # Calculate home team odds of winning
                    homeOdds = self.getHomeOddsStandard(game, trackerDF)
                    randNumber = random.random()

                    if randNumber < homeOdds:
                        self.addWin(homeTeam.team_name, awayTeam.team_name, trackerDF)
                        self.adjustElo(homeTeam.team_name, awayTeam.team_name, homeOdds, self.kFactor, trackerDF)
                    else:
                        self.addWin(awayTeam.team_name, homeTeam.team_name, trackerDF)
                        self.adjustElo(awayTeam.team_name, homeTeam.team_name, 1 - homeOdds, self.kFactor, trackerDF)

            # Separate teams by division
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

            # Determine division winners
            for div in AllDivisions:
                div.sort(key=lambda x: -trackerDF.loc[x, 'TotWins'])
                winner = self.divTieBreaker(div, trackerDF)
                trackerDF.loc[winner, 'Seed'] = 1
                if (trackerDF.loc[winner, 'Division'].split())[0] == 'AFC':
                    AFCDivisionWinners.append(winner)
                else:
                    NFCDivisionWinners.append(winner)

            # Determine wildcard teams
            AFCWildcard = list(set(AFC) - set(AFCDivisionWinners))
            NFCWildcard = list(set(NFC) - set(NFCDivisionWinners))
            
            AFCWildcard.sort(key = lambda x: -trackerDF.loc[x, 'TotWins'])
            NFCWildcard.sort(key = lambda x: -trackerDF.loc[x, 'TotWins'])
            AFCDivisionWinners.sort(key = lambda x: -trackerDF.loc[x, 'TotWins'])
            NFCDivisionWinners.sort(key = lambda x: -trackerDF.loc[x, 'TotWins'])

            AFCWildcard = self.seed(AFCWildcard, trackerDF, True)[:3]
            NFCWildcard = self.seed(NFCWildcard, trackerDF, True)[:3]
            AFCDivisionWinners = self.seed(AFCDivisionWinners, trackerDF, False)
            NFCDivisionWinners = self.seed(NFCDivisionWinners, trackerDF, False)

            # Prepare playoff brackets
            AFCPlayoffs = dict()
            NFCPlayoffs = dict()
            for i, team in enumerate(AFCDivisionWinners):
                AFCPlayoffs[i+1] = team
            for i, team in enumerate(AFCWildcard):
                AFCPlayoffs[i+5] = team
            for i, team in enumerate(NFCDivisionWinners):
                NFCPlayoffs[i+1] = team
            for i, team in enumerate(NFCWildcard):
                NFCPlayoffs[i+5] = team

            # Assign playoff rounds
            for seed in AFCPlayoffs:
                team = AFCPlayoffs[seed]
                if seed == 1:
                    trackerDF.loc[team, 'Playoff Round'] = 'Divisional'
                else:
                    trackerDF.loc[team, 'Playoff Round'] = 'Wildcard'

            for seed in NFCPlayoffs:
                team = NFCPlayoffs[seed]
                if seed == 1:
                    trackerDF.loc[team, 'Playoff Round'] = 'Divisional'
                else:
                    trackerDF.loc[team, 'Playoff Round'] = 'Wildcard'

            # Simulate playoffs and Super Bowl
            self.simPlayoffs(NFCPlayoffs, trackerDF)
            self.simPlayoffs(AFCPlayoffs, trackerDF)
            champs = self.simSuperBowl(NFCPlayoffs, AFCPlayoffs, trackerDF)
            resultsDF.loc[champs, 'SuperBowl'] += 1

            # Update results DataFrame with division championships and top seeds
            for team in self.teams:
                teamName = team.team_name
                if trackerDF.loc[teamName, 'Seed'] <= 4 and trackerDF.loc[teamName, 'Seed'] != -1:
                    resultsDF.loc[teamName, 'DivChamps'] += 1
                if trackerDF.loc[teamName, 'Seed'] == 1:
                    resultsDF.loc[teamName, '1Seed'] += 1
                resultDict[teamName].append(trackerDF.loc[teamName, 'TotWins'])

        # Calculate and store statistics in results DataFrame
        for team in resultDict:
            resultsDF.loc[team, 'Mean'] = np.mean(resultDict[team])
            resultsDF.loc[team, 'Median'] = np.median(resultDict[team])
            resultsDF.loc[team, '25'] = np.percentile(resultDict[team], 25)
            resultsDF.loc[team, '75'] = np.percentile(resultDict[team], 75)
            resultsDF.loc[team, 'stdev'] = np.std(resultDict[team])

        # Save results to CSV file
        resultsDF.to_csv('test2.csv', mode='w+', index=False)
