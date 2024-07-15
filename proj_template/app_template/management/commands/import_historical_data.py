import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from app_template.models import NFLTeam, HistoricalData

class Command(BaseCommand):
    help = 'Import historical data from CSV and associate with NFL teams'

    def handle(self, *args, **kwargs):
        file_path = 'app_template/static/csv/historical_data.csv'  # Update with your file path
        teams = NFLTeam.objects.all()

        with open(file_path, mode='r', newline='') as file:
            reader = csv.DictReader(file)
            row_count = 0
            for row in reader:
                # Find the corresponding team for team1 (assuming team1 is the abbreviation)
                team1_abbr = row['team1']
                team = teams.get(abbreviation=team1_abbr)

                # Create HistoricalData instance
                historical_data = HistoricalData.objects.create(
                    date=datetime.strptime(row['date'], '%d-%b-%Y').date(),
                    season=int(row['season']),
                    neutral=row['neutral'] == '1',
                    playoff=row['playoff'] == '1',
                    team1=row['team1'],
                    team2=row['team2'],
                    elo1_pre=float(row['elo1_pre']),
                    elo2_pre=float(row['elo2_pre']),
                    elo_prob1=float(row['elo_prob1']),
                    elo_prob2=float(row['elo_prob2']),
                    elo1_post=float(row['elo1_post']),
                    elo2_post=float(row['elo2_post']),
                    score1=int(row['score1']),
                    score2=int(row['score2']),
                    is_home=row['is_home'] == '1',
                    is_win=row['is_win'] == '1',
                    gm_no=int(row['gm_no'])
                )

                # Add the historical game to the team's historical_games
                team.historical_games.add(historical_data)

                row_count += 1
                if row_count % 100 == 0:
                    self.stdout.write(self.style.SUCCESS(f'Processed {row_count} rows'))

        self.stdout.write(self.style.SUCCESS('Successfully imported historical data'))
