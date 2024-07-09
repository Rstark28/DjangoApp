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
        self.cityCoordinatesCache = {}

        allGames = UpcomingGames.objects.all().filter(isComplete=False)
        self.gamesByWeek = {}
        for game in allGames:
            if game.week not in self.gamesByWeek:
                self.gamesByWeek[game.week] = []
            self.gamesByWeek[game.week].append(game)

        # Initialize a DataFrame to track the current state of the simulation
        self.trackerDF = pd.DataFrame(columns=['Team', 'Elo', 'TotWins', 'DivWins', 'ConfWins', 'TeamsLostTo', 'TeamsBeat', 'Division', 'Conference', 'Seed', 'Playoff Round'])
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
        self.AFCEast = ["New England Patriots", "Buffalo Bills", "Miami Dolphins", "New York Jets"]
        self.AFCWest = ["Kansas City Chiefs", "Los Angeles Chargers", "Denver Broncos", "Las Vegas Raiders"]
        self.AFCNorth = ["Pittsburgh Steelers", "Baltimore Ravens", "Cleveland Browns", "Cincinnati Bengals"]
        self.AFCSouth = ["Tennessee Titans", "Indianapolis Colts", "Houston Texans", "Jacksonville Jaguars"]

        self.NFCEast = ["Dallas Cowboys", "Philadelphia Eagles", "New York Giants", "Washington Commanders"]
        self.NFCWest = ["San Francisco 49ers", "Seattle Seahawks", "Los Angeles Rams", "Arizona Cardinals"]
        self.NFCNorth = ["Green Bay Packers", "Chicago Bears", "Minnesota Vikings", "Detroit Lions"]
        self.NFCSouth = ["Tampa Bay Buccaneers", "New Orleans Saints", "Carolina Panthers", "Atlanta Falcons"]

        self.AllDivisions = [self.AFCEast, self.AFCWest, self.AFCNorth, self.AFCSouth, self.NFCEast, self.NFCWest, self.NFCSouth, self.NFCNorth]

        self.AFC = self.AFCNorth + self.AFCEast + self.AFCWest + self.AFCSouth
        self.NFC = self.NFCNorth + self.NFCEast + self.NFCWest + self.NFCSouth
          
    def add_arguments(self, parser):

        parser.add_argument(
            '-n', '--num',
            type = int,
            help = 'Number of Simulations',
            default = '100'
        )

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
        
        # Generate game results
        self.allGameResults = [np.random.random(285) for _ in range(numSeasons)]
        
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

    def getCityCoordinates(self, cityName):
        if cityName not in self.cityCoordinatesCache:
            city = self.cities.get(name=cityName)
            self.cityCoordinatesCache[cityName] = (city.lat, city.long)
        return self.cityCoordinatesCache[cityName]

    def getHomeOddsStandard(self, game: UpcomingGames, df: pd.DataFrame) -> float:
        home = game.homeTeam
        away = game.awayTeam

        gameCoords = self.getCityCoordinates(game.city)
        homeCoords = self.getCityCoordinates(home.city)
        awayCoords = self.getCityCoordinates(away.city)

        homeDistance = geodesic(gameCoords, homeCoords).miles
        awayDistance = geodesic(gameCoords, awayCoords).miles

        eloDiff = home.elo - away.elo
        if game.after_bye_home:
            eloDiff += 25
        if game.after_bye_away:
            eloDiff -= 25
        if not game.isNeutral:
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
            
        gameCoords = self.getCityCoordinates(gameCity)
        homeCoords = self.getCityCoordinates(home.city)
        awayCoords = self.getCityCoordinates(away.city)
        homeDistance = geodesic(gameCoords, homeCoords).miles
        awayDistance = geodesic(gameCoords, awayCoords).miles
        
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

        if df.loc[winner, 'Division'] == df.loc[loser, 'Division']:
            df.loc[winner, 'DivWins'] += 1
            df.loc[winner, 'ConfWins'] += 1

        elif df.loc[winner, 'Conference'] == df.loc[loser, 'Conference']:
            df.loc[winner, 'ConfWins'] += 1

        df.at[winner, 'TeamsBeat'] = f"{df.at[winner, 'TeamsBeat']};{loser}".strip(';')
        df.at[loser, 'TeamsLostTo'] = f"{df.at[loser, 'TeamsLostTo']};{winner}".strip(';')

    # TODO
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

    # TODO       
    def divisionTieBreaker(self, division: list[str], df: pd.DataFrame) -> str:
        firstPlace = division[0]
        tiedForFirst = [firstPlace]
        for team in division[1:]:
            if df.loc[team, 'TotWins'] == df.loc[firstPlace, 'TotWins']:
                tiedForFirst.append(team)
        winner = self.divBreakTieHelper(tiedForFirst, division, df)
        return winner
    
    # TODO
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

    # TODO 
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
                
                
    # TODO
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
    
    # TODO
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

        # Get AFC and NFC champions
        AFCChamp = NFLTeam.objects.get(name=list(AFC.values())[0])
        NFCChamp = NFLTeam.objects.get(name=list(NFC.values())[0])

        # Simulate the SuperBowl
        NFCOdds = self.getPlayoffOddsStandard(AFCChamp, NFCChamp, df, False, isSuperBowl=True)
        outcome = self.gameResults[self.currGame]
        winner, loser = (NFCChamp.name, AFCChamp.name) if outcome < NFCOdds else (AFCChamp.name, NFCChamp.name)

        # Adjust ELO ratings and update DF to reflect champion
        self.adjustElo(winner, loser, NFCOdds, self.kFactor, df)
        df.loc[winner, 'Playoff Round'] = "Super Bowl Champ"

        return winner
        
    def adjustElo(self, winner: str, loser: str, winnerOdds: float, kFactor: float, df: pd.DataFrame):

        eloChange = (1 - winnerOdds) * kFactor
        df.loc[winner, 'Elo'] += eloChange
        df.loc[loser, 'Elo'] -= eloChange

    # TODO
    def setSeasonTracker(self):

        for team in self.teams:
            self.trackerDF.loc[team.name] = {
                'Team': team.name,
                'Elo': team.elo,
                'ConfWins': team.confWins,
                'TotWins': team.totWins,
                'DivWins': team.divWins,
                'TeamsLostTo': '',
                'TeamsBeat': '',
                'Division': self.divisionDict[team.name],
                'Conference': self.divisionDict[team.name].split()[0],
                'Seed': -1,
                'Playoff Round': 'None'
            }
    
    # TODO     
    def simSeason(self, currSeason: int):

        self.gameResults = self.allGameResults[currSeason]
    
        self.currGame = 0

        start_time = time.time()
        print(f"Starting season {currSeason + 1}")

        # Initialize tracker for new season sim
        self.setSeasonTracker()

        # Simulate each week of games
        for currWeek in range(1, 18):

            weeklyGames = self.gamesByWeek[currWeek]
            
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
            
        AFCDivisionWinners = []
        NFCDivisionWinners = []

        # Determine division winners
        for division in self.AllDivisions:
            division.sort(key=lambda x: -self.trackerDF.loc[x, 'TotWins'])
            divisionChamp = self.divisionTieBreaker(division, self.trackerDF)
            self.trackerDF.loc[divisionChamp, 'Seed'] = 1

            if (self.trackerDF.loc[divisionChamp, 'Division'].split())[0] == 'AFC':
                AFCDivisionWinners.append(divisionChamp)
            else:
                NFCDivisionWinners.append(divisionChamp)

        # Determine wildcard teams
        AFCWildcard = list(set(self.AFC) - set(AFCDivisionWinners))
        NFCWildcard = list(set(self.NFC) - set(NFCDivisionWinners))
        
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
        for i in range(4):
            AFCPlayoffs[i + 1] = AFCDivisionWinners[i]
            NFCPlayoffs[i + 1] = NFCDivisionWinners[i]
        for i in range(3):
            AFCPlayoffs[i + 5] = AFCWildcard[i]
            NFCPlayoffs[i + 5] = NFCWildcard[i]

        # Assign playoff rounds
        for seed in range(1, 8):
            if seed == 1:
                self.trackerDF.loc[AFCPlayoffs[seed], 'Playoff Round'] = 'Divisional'
                self.trackerDF.loc[NFCPlayoffs[seed], 'Playoff Round'] = 'Divisional'
            else:
                self.trackerDF.loc[AFCPlayoffs[seed], 'Playoff Round'] = 'Wildcard'
                self.trackerDF.loc[NFCPlayoffs[seed], 'Playoff Round'] = 'Wildcard'
        
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