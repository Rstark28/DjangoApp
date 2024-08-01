# from django_app/management/commands/update_projections.py

from io import StringIO
from django.core.management.base import BaseCommand
from main.models import NFLTeam, UpcomingGames, Season, Projection, City
from django.contrib.auth.models import User
import pandas as pd
import requests
from datetime import datetime, date
import numpy as np
import random, time
from geopy.distance import geodesic

class Command(BaseCommand):
    help = 'Updates/Generates the projections'

    def __init__(self):
        self.admin_user = User.objects.get(username='admin')
        self.k_factor = 20.0
        self.super_bowl_city = 'New Orleans'
        self.teams = NFLTeam.objects.all()
        self.cities = City.objects.all()
        self.city_coordinates_cache = {}
        self.games_by_week = {}
        self.tracker_df = pd.DataFrame(columns=['team', 'elo', 'tot_wins', 'div_wins', 'conf_wins', 'teams_lost_to', 'teams_beat', 'division', 'conference', 'seed', 'playoffRound'])
        self.tracker_df.set_index('team', inplace=True)
        self.results_df = pd.DataFrame(columns=['team', 'playoffs', 'won_conference', 'super_bowl', 'div_champs', 'first_seed', 'mean', 'median', '25', '75', 'stdev', 'weekly_results'])

        for team in self.teams:
            self.results_df.loc[team.name] = [team.name, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, [0] * 18]

        self.division_dict = {
            "Buffalo Bills": "AFC East", "Miami Dolphins": "AFC East", "New England Patriots": "AFC East", "New York Jets": "AFC East",
            "Baltimore Ravens": "AFC North", "Cincinnati Bengals": "AFC North", "Cleveland Browns": "AFC North", "Pittsburgh Steelers": "AFC North",
            "Houston Texans": "AFC South", "Indianapolis Colts": "AFC South", "Jacksonville Jaguars": "AFC South", "Tennessee Titans": "AFC South",
            "Denver Broncos": "AFC West", "Kansas City Chiefs": "AFC West", "Las Vegas Raiders": "AFC West", "Los Angeles Chargers": "AFC West",
            "Dallas Cowboys": "NFC East", "New York Giants": "NFC East", "Philadelphia Eagles": "NFC East", "Washington Commanders": "NFC East",
            "Chicago Bears": "NFC North", "Detroit Lions": "NFC North", "Green Bay Packers": "NFC North", "Minnesota Vikings": "NFC North",
            "Atlanta Falcons": "NFC South", "Carolina Panthers": "NFC South", "New Orleans Saints": "NFC South", "Tampa Bay Buccaneers": "NFC South",
            "Arizona Cardinals": "NFC West", "Los Angeles Rams": "NFC West", "San Francisco 49ers": "NFC West", "Seattle Seahawks": "NFC West"
        }

        self.all_divisions = [
            ["New England Patriots", "Buffalo Bills", "Miami Dolphins", "New York Jets"],
            ["Kansas City Chiefs", "Los Angeles Chargers", "Denver Broncos", "Las Vegas Raiders"],
            ["Pittsburgh Steelers", "Baltimore Ravens", "Cleveland Browns", "Cincinnati Bengals"],
            ["Tennessee Titans", "Indianapolis Colts", "Houston Texans", "Jacksonville Jaguars"],
            ["Dallas Cowboys", "Philadelphia Eagles", "New York Giants", "Washington Commanders"],
            ["San Francisco 49ers", "Seattle Seahawks", "Los Angeles Rams", "Arizona Cardinals"],
            ["Green Bay Packers", "Chicago Bears", "Minnesota Vikings", "Detroit Lions"],
            ["Tampa Bay Buccaneers", "New Orleans Saints", "Carolina Panthers", "Atlanta Falcons"]
        ]

        self.afc = [team for division in self.all_divisions[:4] for team in division]
        self.nfc = [team for division in self.all_divisions[4:] for team in division]

        all_games = UpcomingGames.objects.filter(is_complete=False, user=self.admin_user)
        for game in all_games:
            if game.week not in self.games_by_week:
                self.games_by_week[game.week] = []
            self.games_by_week[game.week].append(game)

    def add_arguments(self, parser):
        parser.add_argument('-n', '--num', type=int, help='Number of Simulations', default=100)
        parser.add_argument('-w', '--week', type=int, help='Week of Simulation', default=0)

    def handle(self, *args, **kwargs):
        self.curr_week = kwargs['week']
        Projection.objects.filter(current_week=self.curr_week, user=self.admin_user).delete()
        num_seasons = kwargs['num']
        self.result_dict = {team.name: [] for team in self.teams}
        self.all_game_results = [np.random.random(285) for _ in range(num_seasons)]

        for curr_season in range(num_seasons):
            self.sim_season(curr_season)

        for team in self.result_dict:
            self.results_df.at[team, 'mean'] = np.mean(self.result_dict[team])
            self.results_df.at[team, 'median'] = np.median(self.result_dict[team])
            self.results_df.at[team, '25'] = np.percentile(self.result_dict[team], 25)
            self.results_df.at[team, '75'] = np.percentile(self.result_dict[team], 75)
            self.results_df.at[team, 'stdev'] = np.std(self.result_dict[team])

            Projection.objects.create(
                team=self.teams.get(name=team), n=num_seasons,
                mean=float(self.results_df.at[team, 'mean']),
                median=float(self.results_df.at[team, 'median']),
                made_playoffs=self.results_df.at[team, 'playoffs'],
                won_division=self.results_df.at[team, 'div_champs'],
                won_conference=self.results_df.at[team, 'won_conference'],
                won_super_bowl=self.results_df.at[team, 'super_bowl'],
                standard_deviation=self.results_df.at[team, 'stdev'],
                first_quartile=self.results_df.at[team, '25'],
                third_quartile=self.results_df.at[team, '75'],
                current_week=self.curr_week, user=self.admin_user, is_custom=False
            )
        self.results_df.to_csv('test2.csv', mode='w+', index=False)

# Function Name: `get_city_coordinates`
# Purpose: Retrieve the latitude and longitude coordinates for a given city.
# Parameters: 
#   - city_name (str): The name of the city to retrieve coordinates for.
# Returns: 
#   - tuple[float, float]: A tuple containing the latitude and longitude of the city.
    def get_city_coordinates(self, city_name: str) -> tuple[float, float]:
        if city_name not in self.city_coordinates_cache:
            city = self.cities.get(name=city_name)
            self.city_coordinates_cache[city_name] = (city.latitude, city.longitude)
        return self.city_coordinates_cache[city_name]

# Function Name: `get_home_odds_standard`
# Purpose: Calculate the odds of the home team winning a standard game.
# Parameters: 
#   - game (UpcomingGames): The upcoming game to calculate the odds for.
# Returns: 
#   - float: The probability of the home team winning.
    def get_home_odds_standard(self, game: UpcomingGames) -> float:
        home = game.home_team
        away = game.away_team
        game_coords = self.get_city_coordinates(game.city)
        home_coords = self.get_city_coordinates(home.city)
        away_coords = self.get_city_coordinates(away.city)
        home_distance = geodesic(game_coords, home_coords).miles
        away_distance = geodesic(game_coords, away_coords).miles
        elo_diff = home.elo - away.elo
        if game.after_bye_home:
            elo_diff += 25
        if game.after_bye_away:
            elo_diff -= 25
        if not game.is_neutral:
            elo_diff += 48
        elo_diff -= home_distance * 4 / 1000
        elo_diff += away_distance * 4 / 1000
        home_odds = 1 / (10 ** (-elo_diff / 400) + 1)
        return home_odds

# Function Name: `get_playoff_odds_standard`
# Purpose: Calculate the odds of the home team winning a playoff game.
# Parameters: 
#   - home (NFLTeam): The home team.
#   - away (NFLTeam): The away team.
#   - home_bye (bool): Whether the home team has a bye week before the game (default: False).
#   - is_super_bowl (bool): Whether the game is the Super Bowl (default: False).
# Returns: 
#   - float: The probability of the home team winning the playoff game.
    def get_playoff_odds_standard(self, home: NFLTeam, away: NFLTeam, home_bye: bool = False, is_super_bowl: bool = False) -> float:
        game_city = home.city if not is_super_bowl else self.super_bowl_city
        game_coords = self.get_city_coordinates(game_city)
        home_coords = self.get_city_coordinates(home.city)
        away_coords = self.get_city_coordinates(away.city)
        home_distance = geodesic(game_coords, home_coords).miles
        away_distance = geodesic(game_coords, away_coords).miles
        elo_diff = home.elo - away.elo
        if home_bye:
            elo_diff += 25
        if not is_super_bowl:
            elo_diff += 48
        elo_diff -= home_distance * 4 / 1000
        elo_diff += away_distance * 4 / 1000
        elo_diff *= 1.2
        home_odds = 1 / (10 ** (-elo_diff / 400) + 1)
        return home_odds

# Function Name: `add_win`
# Purpose: Update the tracker dataframe to record a win for a team.
# Parameters: 
#   - winner (str): The name of the winning team.
#   - loser (str): The name of the losing team.
# Returns: None
    def add_win(self, winner: str, loser: str) -> None:
        self.tracker_df.at[winner, 'tot_wins'] += 1
        if self.tracker_df.at[winner, 'division'] == self.tracker_df.at[loser, 'division']:
            self.tracker_df.at[winner, 'div_wins'] += 1
            self.tracker_df.at[winner, 'conf_wins'] += 1
        elif self.tracker_df.at[winner, 'conference'] == self.tracker_df.at[loser, 'conference']:
            self.tracker_df.at[winner, 'conf_wins'] += 1
        self.tracker_df.at[winner, 'teams_beat'] = f"{self.tracker_df.at[winner, 'teams_beat']};{loser}".strip(';')
        self.tracker_df.at[loser, 'teams_lost_to'] = f"{self.tracker_df.at[loser, 'teams_lost_to']};{winner}".strip(';')
        self.results_df.at[winner, 'weekly_results'][self.simulation_week - 1] += 1

# Function Name: `div_break_tie_helper`
# Purpose: Break ties between teams within a division.
# Parameters: 
#   - tied (list[str]): A list of teams that are tied.
#   - division (list[str]): A list of teams in the division.
# Returns: 
#   - str: The name of the team that won the tiebreaker.
    def div_break_tie_helper(self, tied: list[str], division: list[str]) -> str:
        if len(tied) == 1:
            return tied[0]

        tied_orig = len(tied)

        def update_common_score(tied: list[str]) -> dict[str, int]:
            common_score = {team: 0 for team in tied}
            for i, team in enumerate(tied):
                teams_beat = self.tracker_df.at[team, 'teams_beat'].split(';')
                teams_lost = self.tracker_df.at[team, 'teams_lost_to'].split(';')
                other_teams = tied[:i] + tied[i+1:]
                for other_team in other_teams:
                    common_score[team] += teams_beat.count(other_team)
                    common_score[team] -= teams_lost.count(other_team)
            return common_score

        def apply_tie_breaker(tied: list[str], column: str, reverse: bool = True) -> list[str]:
            tied.sort(key=lambda x: -self.tracker_df.at[x, column] if reverse else self.tracker_df.at[x, column])
            highest = tied[0]
            return [team for team in tied if self.tracker_df.at[team, column] == self.tracker_df.at[highest, column]]

        common_score = update_common_score(tied)
        tied.sort(key=lambda x: -common_score[x])
        highest = tied[0]
        tied = [team for team in tied if common_score[team] == common_score[highest]]
        if tied_orig > len(tied):
            return self.div_break_tie_helper(tied, division)

        tied = apply_tie_breaker(tied, 'div_wins')
        if tied_orig > len(tied):
            return self.div_break_tie_helper(tied, division)

        tied = apply_tie_breaker(tied, 'conf_wins')
        if tied_orig > len(tied):
            return self.div_break_tie_helper(tied, division)

        return random.choice(tied)

# Function Name: `division_tie_breaker`
# Purpose: Determine the division champion when there are ties.
# Parameters: 
#   - division (list[str]): A list of teams in the division.
# Returns: 
#   - str: The name of the division champion.
    def division_tie_breaker(self, division: list[str]) -> str:
        tied_for_first = [team for team in division if self.tracker_df.at[team, 'tot_wins'] == self.tracker_df.at[division[0], 'tot_wins']]
        return self.div_break_tie_helper(tied_for_first, division)

# Function Name: `find_ties`
# Purpose: Identify groups of teams that are tied based on a given key.
# Parameters: 
#   - teams (list[str]): A list of teams to check for ties.
#   - is_wild_card (bool): Whether the tie check is for wild card teams.
#   - key (function): A function to determine the value to check ties on.
# Returns: 
#   - list[list[str]]: A list of lists, where each sublist contains teams that are tied.
    def find_ties(self, teams: list[str], is_wild_card: bool, key) -> list[list[str]]:
        tied = []
        curr_tie_list = [teams[0]]
        curr_wins = key(teams[0])
        num_of_teams = 0

        for team in teams[1:]:
            num_of_teams += 1
            if key(team) == curr_wins:
                curr_tie_list.append(team)
            else:
                tied.append(curr_tie_list)
                if is_wild_card and num_of_teams >= 3:
                    return tied
                curr_tie_list = [team]
                curr_wins = key(team)

        tied.append(curr_tie_list)
        return tied

# Function Name: `resolve_ties`
# Purpose: Resolve ties between teams.
# Parameters: 
#   - tie (list[str]): A list of teams that are tied.
# Returns: 
#   - list[str]: A list of teams ordered by the resolved tie-breaking process.
    def resolve_ties(self, tie: list[str]) -> list[str]:
        if len(tie) == 1:
            return tie

        def get_sweep_status(team: str, other_teams: list[str]) -> tuple[bool, bool]:
            teams_beat = set(self.tracker_df.at[team, 'teams_beat'].split(';'))
            teams_lost = set(self.tracker_df.at[team, 'teams_lost_to'].split(';'))
            swept = all(other in teams_beat and other not in teams_lost for other in other_teams)
            was_swept = all(other not in teams_beat and other in teams_lost for other in other_teams)
            return swept, was_swept

        sweeper, swept = None, None
        for team in tie:
            other_teams = [t for t in tie if t != team]
            swept_status, was_swept_status = get_sweep_status(team, other_teams)
            if swept_status:
                sweeper = team
            if was_swept_status:
                swept = team

        if sweeper and swept:
            return [sweeper] + [t for t in tie if t not in {sweeper, swept}] + [swept]
        if sweeper:
            return [sweeper] + [t for t in tie if t != sweeper]
        if swept:
            return [t for t in tie if t != swept] + [swept]

        tie.sort(key=lambda x: -self.tracker_df.at[x, 'conf_wins'])
        new_ties = self.find_ties(tie, False, lambda x: self.tracker_df.at[x, 'conf_wins'])

        if len(new_ties) == 1:
            return random.sample(new_ties[0], len(new_ties[0]))

        return [team for sub_tie in new_ties for team in self.resolve_ties(sub_tie)]

# Function Name: `seed`
# Purpose: Seed teams for the playoffs based on their performance.
# Parameters: 
#   - teams (list[str]): A list of teams to seed.
#   - is_wild_card (bool): Whether the seeding is for wild card teams.
# Returns: 
#   - list[str]: A list of teams ordered by their seed.
    def seed(self, teams: list[str], is_wild_card: bool) -> list[str]:
        tie_list = self.find_ties(teams, is_wild_card, lambda x: self.tracker_df.at[x, 'tot_wins'])
        new_list = []
        for tie in tie_list:
            new_list += self.resolve_ties(tie)
        shift = 5 if is_wild_card else 1
        for i, team in enumerate(new_list):
            self.tracker_df.at[team, 'Seed'] = i + shift
        return new_list

# Function Name: `sim_round`
# Purpose: Simulate a round of playoff games.
# Parameters: 
#   - playoffs (dict[int, str]): A dictionary mapping seeds to team names for the playoffs.
#   - round (int): The current round of the playoffs.
#   - round_dict (dict[int, str]): A dictionary mapping round numbers to round names.
# Returns: None
    def sim_round(self, playoffs: dict[int, str], round: int, round_dict: dict[int, str]) -> None:
        if round == 0:
            matchups = [(2, 7), (3, 6), (4, 5)]
        else:
            seeds = list(playoffs.keys())
            matchups = [(seeds[i], seeds[-(i + 1)]) for i in range(len(seeds) // 2)]

        for higher_seed, lower_seed in matchups:
            off_bye = (higher_seed == 1 and round == 1)
            home_team = NFLTeam.objects.get(name=playoffs[higher_seed])
            away_team = NFLTeam.objects.get(name=playoffs[lower_seed])
            home_odds = self.get_playoff_odds_standard(home_team, away_team, off_bye)
            rand_var = self.game_results[self.curr_game]
            self.curr_game += 1
            winner, loser, winning_odds = (higher_seed, lower_seed, home_odds) if rand_var < home_odds else (lower_seed, higher_seed, 1 - home_odds)
            self.adjust_elo(playoffs[winner], playoffs[loser], winning_odds, self.k_factor)
            self.tracker_df.at[playoffs[winner], 'PlayoffRound'] = round_dict[round]
            del playoffs[loser]

# Function Name: `sim_playoffs`
# Purpose: Simulate the entire playoff series.
# Parameters: 
#   - playoffs (dict[int, str]): A dictionary mapping seeds to team names for the playoffs.
# Returns: None
    def sim_playoffs(self, playoffs: dict[int, str]) -> None:
        round_dict = {0: 'Divisional', 1: 'Conference', 2: 'Super Bowl'}
        self.sim_round(playoffs, 0, round_dict)
        self.sim_round(playoffs, 1, round_dict)
        self.sim_round(playoffs, 2, round_dict)

# Function Name: `sim_super_bowl`
# Purpose: Simulate the Super Bowl game.
# Parameters: 
#   - nfc (dict[int, str]): A dictionary mapping seeds to team names for the NFC.
#   - afc (dict[int, str]): A dictionary mapping seeds to team names for the AFC.
# Returns: 
#   - str: The name of the Super Bowl winning team.
    def sim_super_bowl(self, nfc: dict[int, str], afc: dict[int, str]) -> str:
        afc_champ = NFLTeam.objects.get(name=list(afc.values())[0])
        nfc_champ = NFLTeam.objects.get(name=list(nfc.values())[0])
        self.results_df.at[afc_champ.name, 'won_conference'] += 1
        self.results_df.at[nfc_champ.name, 'won_conference'] += 1
        nfc_odds = self.get_playoff_odds_standard(nfc_champ, afc_champ, False, is_super_bowl=True)
        outcome = self.game_results[self.curr_game]
        winner, loser = (nfc_champ.name, afc_champ.name) if outcome < nfc_odds else (afc_champ.name, nfc_champ.name)
        winner_odds = nfc_odds if outcome < nfc_odds else 1 - nfc_odds
        self.adjust_elo(winner, loser, winner_odds, self.k_factor)
        self.tracker_df.at[winner, 'PlayoffRound'] = "Super Bowl Champ"
        return winner

# Function Name: `adjust_elo`
# Purpose: Adjust the Elo ratings of the winner and loser teams.
# Parameters: 
#   - winner (str): The name of the winning team.
#   - loser (str): The name of the losing team.
#   - winner_odds (float): The odds of the winner winning the game.
#   - k_factor (float): The K-factor used in the Elo rating adjustment.
# Returns: None
    def adjust_elo(self, winner: str, loser: str, winner_odds: float, k_factor: float) -> None:
        elo_change = (1 - winner_odds) * k_factor
        self.tracker_df.at[winner, 'elo'] += elo_change
        self.tracker_df.at[loser, 'elo'] -= elo_change

# Function Name: `set_season_tracker`
# Purpose: Initialize the season tracker dataframe with the current season's data.
# Parameters: None
# Returns: None
    def set_season_tracker(self) -> None:
        for team in self.teams:
            self.tracker_df.loc[team.name] = {
                'team': team.name, 'elo': team.elo, 'conf_wins': team.conf_wins,
                'tot_wins': team.tot_wins, 'div_wins': team.div_wins, 'teams_lost_to': '',
                'teams_beat': '', 'division': self.division_dict[team.name],
                'conference': self.division_dict[team.name].split()[0], 'seed': -1,
                'playoff_round': 'None'
            }

# Function Name: `sim_season`
# Purpose: Simulate an entire NFL season.
# Parameters: 
#   - curr_season (int): The current season being simulated.
# Returns: None
    def sim_season(self, curr_season: int):
        self.game_results = self.all_game_results[curr_season]
        self.curr_game = 0
        start_time = time.time()
        print(f"Starting season {curr_season + 1}")
        self.set_season_tracker()

        for curr_week in range(1, 19):
            self.simulation_week = curr_week
            weekly_games = self.games_by_week.get(curr_week, [])

            for game in weekly_games:
                home_team = game.home_team
                away_team = game.away_team
                home_odds = self.get_home_odds_standard(game)
                rand_number = self.game_results[self.curr_game]
                self.curr_game += 1

                if rand_number < home_odds:
                    self.add_win(home_team.name, away_team.name)
                    self.adjust_elo(home_team.name, away_team.name, home_odds, self.k_factor)
                else:
                    self.add_win(away_team.name, home_team.name)
                    self.adjust_elo(away_team.name, home_team.name, 1 - home_odds, self.k_factor)

        afc_division_winners = []
        nfc_division_winners = []

        for division in self.all_divisions:
            division.sort(key=lambda x: -self.tracker_df.at[x, 'tot_wins'])
            division_champ = self.division_tie_breaker(division)
            self.tracker_df.at[division_champ, 'seed'] = 1

            if self.tracker_df.at[division_champ, 'division'].split()[0] == 'AFC':
                afc_division_winners.append(division_champ)
            else:
                nfc_division_winners.append(division_champ)

        afc_wildcard = list(set(self.afc) - set(afc_division_winners))
        nfc_wildcard = list(set(self.nfc) - set(nfc_division_winners))
        afc_wildcard.sort(key=lambda x: -self.tracker_df.at[x, 'tot_wins'])
        nfc_wildcard.sort(key=lambda x: -self.tracker_df.at[x, 'tot_wins'])
        afc_division_winners.sort(key=lambda x: -self.tracker_df.at[x, 'tot_wins'])
        nfc_division_winners.sort(key=lambda x: -self.tracker_df.at[x, 'tot_wins'])

        afc_wildcard = self.seed(afc_wildcard, True)[:3]
        nfc_wildcard = self.seed(nfc_wildcard, True)[:3]
        afc_division_winners = self.seed(afc_division_winners, False)
        nfc_division_winners = self.seed(nfc_division_winners, False)

        afc_playoffs = {i + 1: afc_division_winners[i] for i in range(4)}
        nfc_playoffs = {i + 1: nfc_division_winners[i] for i in range(4)}
        afc_playoffs.update({i + 5: afc_wildcard[i] for i in range(3)})
        nfc_playoffs.update({i + 5: nfc_wildcard[i] for i in range(3)})

        for seed in range(1, 8):
            if seed == 1:
                self.tracker_df.at[afc_playoffs[seed], 'playoff_round'] = 'Divisional'
                self.tracker_df.at[nfc_playoffs[seed], 'playoff_round'] = 'Divisional'
            else:
                self.tracker_df.at[afc_playoffs[seed], 'playoff_round'] = 'Wildcard'
                self.tracker_df.at[nfc_playoffs[seed], 'playoff_round'] = 'Wildcard'

        self.sim_playoffs(nfc_playoffs)
        self.sim_playoffs(afc_playoffs)
        champs = self.sim_super_bowl(nfc_playoffs, afc_playoffs)
        self.results_df.at[champs, 'super_bowl'] += 1

        for team in self.teams:
            team_name = team.name
            if self.tracker_df.at[team_name, 'Seed'] <= 4 and self.tracker_df.at[team_name, 'Seed'] != -1:
                self.results_df.at[team_name, 'div_champs'] += 1
            if self.tracker_df.at[team_name, 'Seed'] == 1:
                self.results_df.at[team_name, 'first_seed'] += 1
            if self.tracker_df.at[team_name, 'Seed'] <= 7 and self.tracker_df.at[team_name, 'Seed'] != -1:
                self.results_df.at[team_name, 'playoffs'] += 1
            self.result_dict[team_name].append(self.tracker_df.at[team_name, 'tot_wins'])

        print(f"Finished season {curr_season + 1} in {time.time() - start_time:.2f} seconds")

