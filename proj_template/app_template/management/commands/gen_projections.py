from io import StringIO
from django.core.management.base import BaseCommand
from app_template.models import NFLTeam, UpcomingGames, Season, Projection, City
import pandas as pd
import requests
from datetime import datetime
from datetime import date
import pandas as pd
import numpy as np
import math, random, time
from geopy.distance import geodesic

class Command(BaseCommand):
    
    help = 'Updates/Generates the projections'

    def __init__(self):

        self.kFactor = 20.0
        self.superBowlCity = 'New Orleans'
        self.teams = NFLTeam.objects.all()
        self.cities = City.objects.all()

        # Initialize a DataFrame to track the current state of the simulation
        self.trackerDF = pd.DataFrame(columns=['Team', 'Elo', 'TotWins', 'DivWins', 'ConfWins', 'TeamsLostTo', 'TeamsBeat', 'Division', 'Seed', 'Playoff Round'])
        self.trackerDF.set_index('Team', inplace=True)

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
    
    def getHomeOddsStandard(self, Game: UpcomingGames, df: pd.DataFrame) -> float:

        home = Game.homeTeam
        away = Game.awayTeam

        gameCords = (self.cities.get(name = Game.city).lat,  self.cities.get(name = Game.city).long)
        homeCords = (self.cities.get(name = home.city).lat, self.cities.get(name = home.city).long)
        awayCords = (self.cities.get(name = away.city).lat, self.cities.get(name = away.city).long)
        homeDistance = geodesic(gameCords, homeCords).miles
        awayDistance = geodesic(gameCords, awayCords).miles
        
        eloDiff = home.elo - away.elo
        if Game.after_bye_home:
            eloDiff += 25
        if Game.after_bye_away:
            eloDiff -= 25
        if not Game.isNeutral:
            eloDiff += 48
        eloDiff -= homeDistance * 4 / 1000
        eloDiff += awayDistance * 4 / 1000
        homeOdds = 1 / (10 ** (-1 * eloDiff / 400) + 1)
        return homeOdds    
    
    def getPlayoffOddsStandard(self, home: NFLTeam, away: NFLTeam, df: pd.DataFrame, homeBye: bool = False, isSuperBowl = False) -> float:
        
        if not isSuperBowl:
            gameCity = home.city
        else:
            gameCity = self.superBowlCity
            
        gameCords = (self.cities.get(name = gameCity).lat,  self.cities.get(name = gameCity).long)
        homeCords = (self.cities.get(name = home.city).lat, self.cities.get(name = home.city).long)
        awayCords = (self.cities.get(name = away.city).lat, self.cities.get(name = away.city).long)
        homeDistance = geodesic(gameCords, homeCords).miles
        awayDistance = geodesic(gameCords, awayCords).miles
        
        eloDiff = home.elo - away.elo
        if homeBye:
            eloDiff += 25
        if not isSuperBowl:
            eloDiff += 48
        eloDiff -= homeDistance * 4 / 1000
        eloDiff += awayDistance * 4 / 1000
        eloDiff *= 1.2

        homeOdds = 1 / (10 ** (-1 * eloDiff / 400) + 1)
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


    def divBreakTieHelper(self, tied: list[str], division: list[str], df: pd.DataFrame):
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
            return self.divBreakTieHelper(tied, division, df)
        
        #Divisional Tie Breaker
        tied.sort(key = lambda x: -df.loc[x, 'DivWins'])
        highest = tied[0]
        tied = [team for team in tied if commonScore[team] == commonScore[highest]]
        if tiedOrig > len(tied):
            return self.divBreakTieHelper(tied, division, df)
        
        #Conference Tie Breaker
        tied.sort(key = lambda x: -df.loc[x, 'ConfWins'])
        highest = tied[0]
        tied = [team for team in tied if commonScore[team] == commonScore[highest]]
        if tiedOrig > len(tied):
            return self.divBreakTieHelper(tied, division, df)
        
        #Random at this point. Unlikely to affect projections early on, and plan 
        #To add other tie breakers later on
        return random.choice(tied)
        
    def divisionTieBreaker(self, division: list[str], df: pd.DataFrame) -> str:
        firstPlace = division[0]
        tiedForFirst = [firstPlace]
        for team in division[1:]:
            if df.loc[team, 'TotWins'] == df.loc[firstPlace, 'TotWins']:
                tiedForFirst.append(team)
        winner = self.divBreakTieHelper(tiedForFirst, division, df)
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
            Home = NFLTeam.objects.get(name=playoffs[HigherSeed])
            Away = NFLTeam.objects.get(name=playoffs[LowerSeed])
            homeOdds = self.getPlayoffOddsStandard(Home, Away, df, offBye)
            Home = playoffs[HigherSeed]
            Away = playoffs[LowerSeed]
            randVar = self.gameResults[self.currGame]
            self.currGame += 1
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
        NFCChamp = NFLTeam.objects.get(name=list(NFC.values())[0])
        AFCChamp = NFLTeam.objects.get(name=list(AFC.values())[0])
        NFCOdds = self.getPlayoffOddsStandard(AFCChamp, NFCChamp, df, False, isSuperBowl=True)
        NFCChamp = list(NFC.values())[0]
        AFCChamp = list(AFC.values())[0]
        randVal = self.gameResults[self.currGame]
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

        eloChange = (1 - winnerOdds) * kFactor
        df.loc[winner, 'Elo'] += eloChange
        df.loc[loser, 'Elo'] -= eloChange
    
    def setSeasonTracker(self):

        for team in self.teams:
            name = team.name
            self.trackerDF.loc[name] = {
                'Team': name,
                'Elo': team.elo,
                'ConfWins': team.confWins,
                'TotWins': team.totWins,
                'DivWins': team.divWins,
                'TeamsLostTo': '',
                'TeamsBeat': '',
                'Division': self.divisionDict[name],
                'Seed': -1,
                'Playoff Round': 'None'
            }
            
    def simSeason(self, currSeason: int):
        self.gameResults = self.allGameResults[currSeason]
    
        self.currGame = 0

        start_time = time.time()
        print(f"Starting season {currSeason + 1}")

        # Initialize tracker for new season sim
        self.setSeasonTracker()

        # Get the list of upcoming games that are not yet complete
        games = UpcomingGames.objects.all().filter(isComplete=False)
        
        # Simulate each week of games
        for currWeek in range(1, 18):

            weeklyGames = games.filter(week = currWeek)
            
            for game in weeklyGames:
                homeTeam = game.homeTeam
                awayTeam = game.awayTeam

                # Calculate home team odds of winning
                homeOdds = self.getHomeOddsStandard(game, self.trackerDF)
                randNumber = self.gameResults[self.currGame]
                self.currGame += 1

                if randNumber < homeOdds:
                    self.addWin(homeTeam.name, awayTeam.name, self.trackerDF)
                    self.adjustElo(homeTeam.name, awayTeam.name, homeOdds, self.kFactor, self.trackerDF)
                else:
                    self.addWin(awayTeam.name, homeTeam.name, self.trackerDF)
                    self.adjustElo(awayTeam.name, homeTeam.name, 1 - homeOdds, self.kFactor, self.trackerDF)

        # Separate teams by division
        AFCEast = self.trackerDF[self.trackerDF['Division'] == 'AFC East'].index.to_list()
        AFCWest = self.trackerDF[self.trackerDF['Division'] == 'AFC West'].index.to_list()
        AFCNorth = self.trackerDF[self.trackerDF['Division'] == 'AFC North'].index.to_list()
        AFCSouth = self.trackerDF[self.trackerDF['Division'] == 'AFC South'].index.to_list()

        NFCEast = self.trackerDF[self.trackerDF['Division'] == 'NFC East'].index.to_list()
        NFCWest = self.trackerDF[self.trackerDF['Division'] == 'NFC West'].index.to_list()
        NFCSouth = self.trackerDF[self.trackerDF['Division'] == 'NFC South'].index.to_list()
        NFCNorth = self.trackerDF[self.trackerDF['Division'] == 'NFC North'].index.to_list()


        AllDivisions = [AFCEast, AFCWest, AFCNorth, AFCSouth, NFCEast, NFCWest, NFCSouth, NFCNorth]

        AFC = AFCNorth + AFCEast + AFCWest + AFCSouth
        NFC = NFCNorth + NFCEast + NFCWest + NFCSouth

        AFCDivisionWinners = []
        NFCDivisionWinners = []

        # Determine division winners
        for division in AllDivisions:
            division.sort(key=lambda x: -self.trackerDF.loc[x, 'TotWins'])
            divisionChamp = self.divisionTieBreaker(division, self.trackerDF)
            self.trackerDF.loc[divisionChamp, 'Seed'] = 1

            if (self.trackerDF.loc[divisionChamp, 'Division'].split())[0] == 'AFC':
                AFCDivisionWinners.append(divisionChamp)
            else:
                NFCDivisionWinners.append(divisionChamp)

        # Determine wildcard teams
        AFCWildcard = list(set(AFC) - set(AFCDivisionWinners))
        NFCWildcard = list(set(NFC) - set(NFCDivisionWinners))
        
        AFCWildcard.sort(key = lambda x: -self.trackerDF.loc[x, 'TotWins'])
        NFCWildcard.sort(key = lambda x: -self.trackerDF.loc[x, 'TotWins'])
        AFCDivisionWinners.sort(key = lambda x: -self.trackerDF.loc[x, 'TotWins'])
        NFCDivisionWinners.sort(key = lambda x: -self.trackerDF.loc[x, 'TotWins'])

        AFCWildcard = self.seed(AFCWildcard, self.trackerDF, True)[:3]
        NFCWildcard = self.seed(NFCWildcard, self.trackerDF, True)[:3]
        AFCDivisionWinners = self.seed(AFCDivisionWinners, self.trackerDF, False)
        NFCDivisionWinners = self.seed(NFCDivisionWinners, self.trackerDF, False)

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
                self.trackerDF.loc[team, 'Playoff Round'] = 'Divisional'
            else:
                self.trackerDF.loc[team, 'Playoff Round'] = 'Wildcard'

        for seed in NFCPlayoffs:
            team = NFCPlayoffs[seed]
            if seed == 1:
                self.trackerDF.loc[team, 'Playoff Round'] = 'Divisional'
            else:
                self.trackerDF.loc[team, 'Playoff Round'] = 'Wildcard'

        # Simulate playoffs and Super Bowl
        self.simPlayoffs(NFCPlayoffs, self.trackerDF)
        self.simPlayoffs(AFCPlayoffs, self.trackerDF)
        champs = self.simSuperBowl(NFCPlayoffs, AFCPlayoffs, self.trackerDF)
        self.resultsDF.loc[champs, 'SuperBowl'] += 1

        # Update results DataFrame with division championships and top seeds
        for team in self.teams:
            teamName = team.name
            if self.trackerDF.loc[teamName, 'Seed'] <= 4 and self.trackerDF.loc[teamName, 'Seed'] != -1:
                self.resultsDF.loc[teamName, 'DivChamps'] += 1
            if self.trackerDF.loc[teamName, 'Seed'] == 1:
                self.resultsDF.loc[teamName, '1Seed'] += 1
            self.resultDict[teamName].append(self.trackerDF.loc[teamName, 'TotWins'])

        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Finished season {currSeason + 1} in {elapsed_time:.2f} seconds")               
          
    def handle(self, *args, **kwargs):

        # Number of simulations to run
        numSeasons = kwargs['num']

        # Create a DataFrame to store results with specified columns
        self.resultsDF = pd.DataFrame(columns=['Team', 'SuperBowl', 'DivChamps', '1Seed', 'Mean', 'Median', '25', '75', 'stdev'])

        # Initialize results DataFrame with team names and zero values
        for team in self.teams:
            self.resultsDF.loc[team.name] = [team.name, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

        # Initialize a dictionary to store results for each team
        self.resultDict = {team.name: [] for team in self.teams} 
        
        self.allGameResults = []
        for i in range(numSeasons):
            self.allGameResults.append(np.random.random(285))
        
        

        for currSeason in range(numSeasons):
            self.simSeason(currSeason)


        # Calculate and store statistics in results DataFrame
        for team in self.resultDict:
            self.resultsDF.loc[team, 'Mean'] = np.mean(self.resultDict[team])
            self.resultsDF.loc[team, 'Median'] = np.median(self.resultDict[team])
            self.resultsDF.loc[team, '25'] = np.percentile(self.resultDict[team], 25)
            self.resultsDF.loc[team, '75'] = np.percentile(self.resultDict[team], 75)
            self.resultsDF.loc[team, 'stdev'] = np.std(self.resultDict[team])

        # Save results to CSV file
        self.resultsDF.to_csv('test2.csv', mode='w+', index=False)