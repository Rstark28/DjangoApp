import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from main.models import HistoricalData, NFLTeam

class Command(BaseCommand):
    help = 'Import historical data from CSV and associate with NFL teams'

    def handle(self, *args, **kwargs):
        file_path = 'main/static/csv/nfl_elo.csv'
        teams = NFLTeam.objects.all()
        skipped_rows = 0

        with open(file_path, mode='r', newline='') as file:
            reader = csv.DictReader(file)
            row_count = 0
            for row in reader:
                team1_abbr = row['team1']
                team2_abbr = row['team2']
                try:
                    team1 = teams.get(abbreviation=team1_abbr)
                except NFLTeam.DoesNotExist:
                    team1 = None
                
                try:
                    team2 = teams.get(abbreviation=team2_abbr)
                except NFLTeam.DoesNotExist:
                    team2 = None

                # Skip the row if both teams do not exist
                if not team1 and not team2:
                    skipped_rows += 1
                    self.stdout.write(self.style.WARNING(f'Teams {team1_abbr} and {team2_abbr} do not exist. Skipping row.'))
                    continue

                playoff = row['playoff'] if row['playoff'] in ['w', 'd', 'c', 's'] else None

                # Helper function to convert values to float, default to 0.0 if empty
                def to_float(value):
                    try:
                        return float(value) if value else 0.0
                    except ValueError:
                        return 0.0

                historical_data = HistoricalData.objects.create(
                    date=datetime.strptime(row['date'], '%Y-%m-%d').date(),
                    season=int(row['season']),
                    neutral=row['neutral'] == '1',
                    playoff=playoff,
                    team1=row['team1'],
                    team2=row['team2'],
                    elo1_pre=to_float(row['elo1_pre']),
                    elo2_pre=to_float(row['elo2_pre']),
                    elo_prob1=to_float(row['elo_prob1']),
                    elo_prob2=to_float(row['elo_prob2']),
                    elo1_post=to_float(row['elo1_post']),
                    elo2_post=to_float(row['elo2_post']),
                    qbelo1_pre=to_float(row['qbelo1_pre']),
                    qbelo2_pre=to_float(row['qbelo2_pre']),
                    qb1=row['qb1'],
                    qb2=row['qb2'],
                    qb1_value_pre=to_float(row['qb1_value_pre']),
                    qb2_value_pre=to_float(row['qb2_value_pre']),
                    qb1_adj=to_float(row['qb1_adj']),
                    qb2_adj=to_float(row['qb2_adj']),
                    qbelo_prob1=to_float(row['qbelo_prob1']),
                    qbelo_prob2=to_float(row['qbelo_prob2']),
                    qb1_game_value=to_float(row['qb1_game_value']),
                    qb2_game_value=to_float(row['qb2_game_value']),
                    qb1_value_post=to_float(row['qb1_value_post']),
                    qb2_value_post=to_float(row['qb2_value_post']),
                    qbelo1_post=to_float(row['qbelo1_post']),
                    qbelo2_post=to_float(row['qbelo2_post']),
                    score1=to_float(row['score1']),
                    score2=to_float(row['score2']),
                    quality=to_float(row['quality']),
                    importance=to_float(row['importance']),
                    total_rating=to_float(row['total_rating'])
                )

                # Add the historical game to the existing teams' historical_games
                if team1:
                    team1.historical_games.add(historical_data)
                if team2:
                    team2.historical_games.add(historical_data)

                row_count += 1
                if row_count % 100 == 0:
                    self.stdout.write(self.style.SUCCESS(f'Processed {row_count} rows'))

        self.stdout.write(self.style.SUCCESS(f'Successfully imported historical data. Processed {row_count} rows, skipped {skipped_rows} rows.'))
