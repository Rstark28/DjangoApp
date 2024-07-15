from io import StringIO
from django.core.management.base import BaseCommand
from app_template.models import NFLTeam, UpcomingGames, Season, Projection, City
from django.contrib.auth.models import User
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
        self.adminUser = User.objects.all().get(username='admin')
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

        # Create a DataFrame to store results with specified columns
        self.resultsDF = pd.DataFrame(columns=['Team', 'Playoffs', 'WonConference', 'SuperBowl', 'DivChamps', '1Seed', 'Mean', 'Median', '25', '75', 'stdev', 'WeeklyResults'])

        # Initialize results DataFrame with team names and zero values
        for team in self.teams:
            self.resultsDF.loc[team.name] = [team.name, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, [0] * 18]


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
          
    # Adds command-line arguments to the parser.
    # Parameters:
    # - parser: ArgumentParser object to which arguments will be added.
    def add_arguments(self, parser):

        parser.add_argument(
            '-n', '--num',
            type = int,
            help = 'Number of Simulations',
            default = '2'
        )
        parser.add_argument(
            '-w', '--week',
            type = int,
            help = 'Week of Simuation',
            default = '0'
        )
        

    # Manages simulation and handles writing to csv.
    # Parameters:
    # - args, kwargs.
    def handle(self, *args, **kwargs):
        #Week of simulation
        self.currWeek = kwargs['week']

        #Resets Projections For Now. Will Remove later to store historical projections
        Projection.objects.all().filter(currWeek=self.currWeek, user=self.adminUser).delete()
        
        # Number of simulations to run
        numSeasons = kwargs['num']

        # Initialize a dictionary to store results for each team
        self.resultDict = {team.name: [] for team in self.teams} 
        
        # Generate game results
        self.allGameResults = [np.random.random(285) for _ in range(numSeasons)]
        
        for currSeason in range(numSeasons):
            self.simSeason(currSeason)

        # Calculate and store statistics in results DataFrame
        for team in self.resultDict:
            self.resultsDF.at[team, 'Mean'] = np.mean(self.resultDict[team])
            self.resultsDF.at[team, 'Median'] = np.median(self.resultDict[team])
            self.resultsDF.at[team, '25'] = np.percentile(self.resultDict[team], 25)
            self.resultsDF.at[team, '75'] = np.percentile(self.resultDict[team], 75)
            self.resultsDF.at[team, 'stdev'] = np.std(self.resultDict[team])
            
            Projection.objects.create(team=self.teams.get(name=team), 
                                      n= numSeasons,
                                      mean=float(self.resultsDF.at[team, 'Mean']),
                                      median = float(self.resultsDF.at[team, 'Median'] ),
                                      madePlayoffs=self.resultsDF.at[team, 'Playoffs'],
                                      wonDivision=self.resultsDF.at[team, 'DivChamps'],
                                      wonConference=self.resultsDF.at[team, 'WonConference'],
                                      wonSuperBowl=self.resultsDF.at[team, 'SuperBowl'],
                                      stdv=self.resultsDF.at[team, 'stdev'],
                                      firstquartile = self.resultsDF.at[team, '25'],
                                      thirdquartile = self.resultsDF.at[team, '75'],
                                      currWeek = self.currWeek,
                                      user = self.adminUser,
                                      isCustom=False
                                      )
            
        # Save results to CSV file
        self.resultsDF.to_csv('test2.csv', mode='w+', index=False)

    # Retrieves the coordinates (latitude, longitude) for a given city.
    # Parameters:
    # - cityName: The name of the city for which coordinates are requested.
    # Returns:
    # - A tuple containing the latitude and longitude of the city.
    def getCityCoordinates(self, cityName: str) -> tuple[float, float]:
        if cityName not in self.cityCoordinatesCache:
            city = self.cities.get(name=cityName)
            self.cityCoordinatesCache[cityName] = (city.lat, city.long)
        return self.cityCoordinatesCache[cityName]

    # Calculates the home team's odds of winning a game.
    # Parameters:
    # - game: The game for which to calculate the odds.
    # - df: DataFrame containing tracking data.
    # Returns:
    # - The odds of the home team winning the game as a float.
    def getHomeOddsStandard(self, game: UpcomingGames) -> float:
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

    # Calculates the home team's odds of winning a playoff game.
    # Parameters:
    # - home: The home team.
    # - away: The away team.
    # - df: DataFrame containing tracking data.
    # - homeBye: Indicates if the home team is coming off a bye week.
    # - isSuperBowl: Indicates if the game is the Super Bowl.
    # Returns:
    # - The odds of the home team winning the playoff game as a float.
    def getPlayoffOddsStandard(self, home: NFLTeam, away: NFLTeam, homeBye: bool = False, isSuperBowl: bool = False) -> float:
        
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
        
    # Updates the DataFrame with a win for the specified team.
    # Parameters:
    # - winner: The name of the winning team. 
    # - loser: The name of the losing team.
    # - df: DataFrame containing tracking data.
    def addWin(self, winner: str, loser: str) -> None:

        self.trackerDF.at[winner, 'TotWins'] +=  1 

        if self.trackerDF.at[winner, 'Division'] == self.trackerDF.at[loser, 'Division']:
            self.trackerDF.at[winner, 'DivWins'] += 1
            self.trackerDF.at[winner, 'ConfWins'] += 1

        elif self.trackerDF.at[winner, 'Conference'] == self.trackerDF.at[loser, 'Conference']:
            self.trackerDF.at[winner, 'ConfWins'] += 1

        self.trackerDF.at[winner, 'TeamsBeat'] = f"{self.trackerDF.at[winner, 'TeamsBeat']};{loser}".strip(';')
        self.trackerDF.at[loser, 'TeamsLostTo'] = f"{self.trackerDF.at[loser, 'TeamsLostTo']};{winner}".strip(';')

        self.resultsDF.at[winner, 'WeeklyResults'][self.simulationWeek - 1] += 1

    # Resolves tie-breakers within a division.
    # Parameters:
    # - tied: List of tied teams.
    # - division: List of teams in the division.
    # - df: DataFrame containing tracking data.
    # Returns:
    # - The name of the team that wins the tie-breaker.
    def divBreakTieHelper(self, tied: list[str], division: list[str]) -> str:
        if len(tied) == 1:
            return tied[0]  # If only one team is tied, return it

        tiedOrig = len(tied)

        def update_common_score(tied: list[str]) -> dict[str, int]:
            # Calculate head-to-head common score for each team
            common_score = {team: 0 for team in tied}
            for i, team in enumerate(tied):
                teams_beat = self.trackerDF.at[team, 'TeamsBeat'].split(';')
                teams_lost = self.trackerDF.at[team, 'TeamsLostTo'].split(';')
                other_teams = tied[:i] + tied[i+1:]
                for other_team in other_teams:
                    common_score[team] += teams_beat.count(other_team)
                    common_score[team] -= teams_lost.count(other_team)
            return common_score

        def apply_tie_breaker(tied: list[str], column: str, reverse: bool = True) -> list[str]:
            # Apply tie breaker based on a specific column in the DataFrame
            tied.sort(key=lambda x: -self.trackerDF.at[x, column] if reverse else self.trackerDF.at[x, column])
            highest = tied[0]
            return [team for team in tied if self.trackerDF.at[team, column] == self.trackerDF.at[highest, column]]

        # Head-to-head tie breaker
        common_score = update_common_score(tied)
        tied.sort(key=lambda x: -common_score[x])
        highest = tied[0]
        tied = [team for team in tied if common_score[team] == common_score[highest]]
        if tiedOrig > len(tied):
            return self.divBreakTieHelper(tied, division)

        # Divisional tie breaker
        tied = apply_tie_breaker(tied, 'DivWins')
        if tiedOrig > len(tied):
            return self.divBreakTieHelper(tied, division)

        # Conference tie breaker
        tied = apply_tie_breaker(tied, 'ConfWins')
        if tiedOrig > len(tied):
            return self.divBreakTieHelper(tied, division)

        # Random choice as a last resort
        return random.choice(tied)


    # Determines the division winner when there is a tie.
    # Parameters:
    # - division: List of teams in the division.
    # - df: DataFrame containing tracking data.
    # Returns:
    # - The name of the division-winning team.
    def divisionTieBreaker(self, division: list[str]) -> str:
        # Identify teams tied for first place based on total wins and break tie
        tiedForFirst = [team for team in division if self.trackerDF.at[team, 'TotWins'] == self.trackerDF.at[division[0], 'TotWins']]
        return self.divBreakTieHelper(tiedForFirst, division)

    
    # Finds ties within a list of teams.
    # Parameters:
    # - teams: List of teams.
    # - isWildCard: Boolean indicating if the tie is for a wildcard spot.
    # - df: DataFrame containing tracking data.
    # - key: Function to use as the key for finding ties.
    # Returns:
    # - A list of lists, each containing groups of teams that are tied.
    def findTies(self, teams: list[str], isWildCard: bool, key) -> list[list[str]]:
        tied = []
        currTieList = [teams[0]]
        currWins = key(teams[0])
        numOfTeams = 0

        # Iterate over the remaining teams
        for team in teams[1:]:
            numOfTeams += 1
            if key(team) == currWins:
                currTieList.append(team)  # If the current team has the same value, add to the current tie list
            else:
                tied.append(currTieList)  # Otherwise, finalize the current tie list
                if isWildCard and numOfTeams >= 3:
                    return tied  # If processing wildcard teams, stop after finding the tie for the 7 seed
                currTieList = [team] 
                currWins = key(team)  # Update the win comparison value

        tied.append(currTieList)
        return tied

    # Resolves ties within a list of teams.
    # Parameters:
    # - tie: List of tied teams.
    # - df: DataFrame containing tracking data.
    # Returns:
    # - A list of teams in order after resolving ties.
    def resolveTies(self, tie: list[str]) -> list[str]:
        if len(tie) == 1:
            return tie  # If there's only one team, return it immediately

        def get_sweep_status(team: str, other_teams: list[str]) -> tuple[bool, bool]:
            # Determine if a team has swept or was swept by all other teams
            teams_beat = set(self.trackerDF.at[team, 'TeamsBeat'].split(';'))
            teams_lost = set(self.trackerDF.at[team, 'TeamsLostTo'].split(';'))
            swept = all(other in teams_beat and other not in teams_lost for other in other_teams)
            was_swept = all(other not in teams_beat and other in teams_lost for other in other_teams)
            return swept, was_swept

        sweeper, swept = None, None
        for team in tie:
            other_teams = [t for t in tie if t != team]
            swept_status, was_swept_status = get_sweep_status(team, other_teams)
            if swept_status:
                sweeper = team  # Mark the team as a sweeper if it swept all others
            if was_swept_status:
                swept = team  # Mark the team as swept if it was swept by all others

        if sweeper and swept:
            # If both a sweeper and swept team exist, return the ordered list with them at the ends
            return [sweeper] + [t for t in tie if t not in {sweeper, swept}] + [swept]
        if sweeper:
            # If only a sweeper exists, return it first
            return [sweeper] + [t for t in tie if t != sweeper]
        if swept:
            # If only a swept team exists, return it last
            return [t for t in tie if t != swept] + [swept]

        # Sort tied teams based on conference wins
        tie.sort(key=lambda x: -self.trackerDF.at[x, 'ConfWins'])
        # Find new ties based on conference wins
        new_ties = self.findTies(tie, False, lambda x: self.trackerDF.at[x, 'ConfWins'])

        if len(new_ties) == 1:
            # If only one tie group is found, shuffle and return it
            return random.sample(new_ties[0], len(new_ties[0]))

        # Recursively resolve ties for each subgroup and combine results
        return [team for sub_tie in new_ties for team in self.resolveTies(sub_tie)]

                
                
    # Finds ties within a list of teams.
    # Parameters:
    # - teams: List of teams.
    # - isWildCard: Boolean indicating if the tie is for a wildcard spot.
    # - df: DataFrame containing tracking data.
    # - key: Function to use as the key for finding ties.
    # Returns:
    # - A list of lists, each containing teams that are tied.
    def seed(self, teams: list[str], isWildCard: bool) -> list[str]:
        # Identify tie groups based on total wins
        tieList = self.findTies(teams, isWildCard, lambda x: self.trackerDF.at[x, 'TotWins'])
        
        newList = []
        # Resolve ties within each tie group
        for tie in tieList:
            newList += self.resolveTies(tie)
        
        # Determine the seed shift based on whether it's a wildcard seeding
        shift = 5 if isWildCard else 1
        
        # Assign seeds to teams
        for i, team in enumerate(newList):
            self.trackerDF.at[team, 'Seed'] = i + shift
        
        return newList
    
    # Simulates a round of the playoffs.
    # Parameters:
    # - playoffs: Dictionary of playoff teams and their seeds.
    # - df: DataFrame containing tracking data.
    # - round: Integer indicating the current playoff round.
    # - roundDict: Dictionary mapping round numbers to round names.
    def simRound(self, playoffs: dict[int, str], round: int, roundDict: dict[int, str]) -> None:
        # Determine the matchups based on the round
        if round == 0:
            matchups = [(2, 7), (3, 6), (4, 5)]
        else:
            seeds = list(playoffs.keys())
            matchups = [(seeds[i], seeds[-(i + 1)]) for i in range(len(seeds) // 2)]

        # Iterate over the matchups in the current round
        for higherSeed, lowerSeed in matchups:

            offBye = (higherSeed == 1 and round == 1)  # Determine if the higher seed has a bye

            # Get the home and away teams based on their seeds
            homeTeam = NFLTeam.objects.get(name=playoffs[higherSeed])
            awayTeam = NFLTeam.objects.get(name=playoffs[lowerSeed])

            # Calculate the home team's odds of winning
            homeOdds = self.getPlayoffOddsStandard(homeTeam, awayTeam, offBye)

            # Simulate the game result
            randVar = self.gameResults[self.currGame]
            self.currGame += 1

            # Determine the winner and loser
            winner, loser, winningOdds = (higherSeed, lowerSeed, homeOdds) if randVar < homeOdds else (lowerSeed, higherSeed, 1 - homeOdds)

            print(f"{playoffs[winner]} beat {playoffs[loser]} in round {round}")

            # Adjust ELO ratings based on the game result
            self.adjustElo(playoffs[winner], playoffs[loser], winningOdds, self.kFactor)

            # Update the DataFrame to reflect the playoff round for the winner
            self.trackerDF.at[playoffs[winner], 'Playoff Round'] = roundDict[round]

            # Remove the losing team from the playoffs
            del playoffs[loser]


            
    # Simulates a round of the playoffs.
    # Parameters:
    # - playoffs: Dictionary of playoff teams and their seeds.
    # - df: DataFrame containing tracking data.
    # - round: Integer indicating the current playoff round.
    # - roundDict: Dictionary mapping round numbers to round names.
    def simPlayoffs(self, playoffs: dict[int, str]) -> None:
        roundDict = {0: 'Divisional', 1: 'Conference', 2: 'Super Bowl'}
        print(playoffs)
        self.simRound(playoffs, 0, roundDict)
        print(playoffs)
        self.simRound(playoffs, 1, roundDict)
        print(playoffs)
        self.simRound(playoffs, 2, roundDict)
    
    
    # Simulates the Super Bowl.
    # Parameters:
    # - NFC: Dictionary of NFC playoff teams and their seeds.
    # - AFC: Dictionary of AFC playoff teams and their seeds.
    # - df: DataFrame containing tracking data.
    # Returns:
    # - The name of the Super Bowl champion team.
    def simSuperBowl(self, NFC: dict[int, str], AFC: dict[int, str]) -> str:

        # Get AFC and NFC champions
        AFCChamp = NFLTeam.objects.get(name=list(AFC.values())[0])
        NFCChamp = NFLTeam.objects.get(name=list(NFC.values())[0])
        self.resultsDF.at[AFCChamp.name, 'WonConference'] += 1
        self.resultsDF.at[NFCChamp.name, 'WonConference'] += 1
        # Simulate the SuperBowl
        NFCOdds = self.getPlayoffOddsStandard(NFCChamp, AFCChamp, False, isSuperBowl=True)
        outcome = self.gameResults[self.currGame]
        winner, loser = (NFCChamp.name, AFCChamp.name) if outcome < NFCOdds else (AFCChamp.name, NFCChamp.name)
        winnerOdds = NFCOdds if outcome < NFCOdds else 1 - NFCOdds
        # Adjust ELO ratings and update DF to reflect champion
        self.adjustElo(winner, loser, winnerOdds, self.kFactor)
        self.trackerDF.at[winner, 'Playoff Round'] = "Super Bowl Champ"

        print(f"{winner} beat {loser} in the SuperBowl")

        return winner
    
    # Adjusts ELO ratings for the winner and loser of a game.
    # Parameters:
    # - winner: The name of the winning team.
    # - loser: The name of the losing team.
    # - winnerOdds: The odds of the winner winning the game.
    # - kFactor: The K-factor used in the ELO rating calculation.
    # - df: DataFrame containing tracking data.
    def adjustElo(self, winner: str, loser: str, winnerOdds: float, kFactor: float) -> None:
        eloChange = (1 - winnerOdds) * kFactor
        self.trackerDF.at[winner, 'Elo'] += eloChange
        self.trackerDF.at[loser, 'Elo'] -= eloChange

    # Sets the season tracker for all teams.
    # Initializes the trackerDF DataFrame with initial team data.
    def setSeasonTracker(self) -> None:

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
    
    # Simulates an entire season.
    # Parameters:
    # - currSeason: The current season number being simulated.    
    def simSeason(self, currSeason: int):

        self.gameResults = self.allGameResults[currSeason]
    
        self.currGame = 0

        start_time = time.time()
        print(f"Starting season {currSeason + 1}")

        # Initialize tracker for new season sim
        self.setSeasonTracker()

        # Simulate each week of games
        for currWeek in range(1, 19):
            self.simulationWeek = currWeek
            
            weeklyGames = self.gamesByWeek[currWeek]
            
            for game in weeklyGames:
                homeTeam = game.homeTeam
                awayTeam = game.awayTeam

                # Calculate home team odds of winning
                homeOdds = self.getHomeOddsStandard(game)
                randNumber = self.gameResults[self.currGame]
                self.currGame += 1

                if randNumber < homeOdds:
                    self.addWin(homeTeam.name, awayTeam.name)
                    self.adjustElo(homeTeam.name, awayTeam.name, homeOdds, self.kFactor)
                else:
                    self.addWin(awayTeam.name, homeTeam.name)
                    self.adjustElo(awayTeam.name, homeTeam.name, 1 - homeOdds, self.kFactor)
            
        AFCDivisionWinners = []
        NFCDivisionWinners = []

        # Determine division winners
        for division in self.AllDivisions:
            division.sort(key=lambda x: -self.trackerDF.at[x, 'TotWins'])
            divisionChamp = self.divisionTieBreaker(division)
            self.trackerDF.at[divisionChamp, 'Seed'] = 1

            if (self.trackerDF.at[divisionChamp, 'Division'].split())[0] == 'AFC':
                AFCDivisionWinners.append(divisionChamp)
            else:
                NFCDivisionWinners.append(divisionChamp)

        # Determine wildcard teams
        AFCWildcard = list(set(self.AFC) - set(AFCDivisionWinners))
        NFCWildcard = list(set(self.NFC) - set(NFCDivisionWinners))
        
        AFCWildcard.sort(key = lambda x: -self.trackerDF.at[x, 'TotWins'])
        NFCWildcard.sort(key = lambda x: -self.trackerDF.at[x, 'TotWins'])
        AFCDivisionWinners.sort(key = lambda x: -self.trackerDF.at[x, 'TotWins'])
        NFCDivisionWinners.sort(key = lambda x: -self.trackerDF.at[x, 'TotWins'])

        AFCWildcard = self.seed(AFCWildcard, True)[:3]
        NFCWildcard = self.seed(NFCWildcard, True)[:3]
        AFCDivisionWinners = self.seed(AFCDivisionWinners, False)
        NFCDivisionWinners = self.seed(NFCDivisionWinners, False)

        # Prepare playoff brackets
        AFCPlayoffs = {}
        NFCPlayoffs = {}
        for i in range(4):
            AFCPlayoffs[i + 1] = AFCDivisionWinners[i]
            NFCPlayoffs[i + 1] = NFCDivisionWinners[i]
        for i in range(3):
            AFCPlayoffs[i + 5] = AFCWildcard[i]
            NFCPlayoffs[i + 5] = NFCWildcard[i]

        # Assign playoff rounds
        for seed in range(1, 8):
            if seed == 1:
                self.trackerDF.at[AFCPlayoffs[seed], 'Playoff Round'] = 'Divisional'
                self.trackerDF.at[NFCPlayoffs[seed], 'Playoff Round'] = 'Divisional'
            else:
                self.trackerDF.at[AFCPlayoffs[seed], 'Playoff Round'] = 'Wildcard'
                self.trackerDF.at[NFCPlayoffs[seed], 'Playoff Round'] = 'Wildcard'
        
        # Simulate playoffs and Super Bowl
        self.simPlayoffs(NFCPlayoffs)
        self.simPlayoffs(AFCPlayoffs)
        
        champs = self.simSuperBowl(NFCPlayoffs, AFCPlayoffs)
        self.resultsDF.at[champs, 'SuperBowl'] += 1

        print(self.trackerDF.sort_values(by='Seed'))

        # Update results DataFrame with division championships and top seeds
        for team in self.teams:
            teamName = team.name
            if self.trackerDF.at[teamName, 'Seed'] <= 4 and self.trackerDF.at[teamName, 'Seed'] != -1:
                self.resultsDF.at[teamName, 'DivChamps'] += 1
            if self.trackerDF.at[teamName, 'Seed'] == 1:
                self.resultsDF.at[teamName, '1Seed'] += 1
            if self.trackerDF.at[teamName, 'Seed'] <= 7 and self.trackerDF.at[teamName, 'Seed'] != -1:
                self.resultsDF.at[teamName, 'Playoffs'] += 1
            self.resultDict[teamName].append(self.trackerDF.at[teamName, 'TotWins'])

        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Finished season {currSeason + 1} in {elapsed_time:.2f} seconds")          