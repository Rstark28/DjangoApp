import csv
from django.core.management.base import BaseCommand
from app_template.models import NFLTeam

class Command(BaseCommand):
    help = 'Import NFL teams from a CSV file'

    def handle(self, *args, **kwargs):
        file_path = 'app_template/static/csv/nfl_teams.csv'
        with open(file_path, mode='r', newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                NFLTeam.objects.create(
                    name=row['Team Name'],
                    abbreviation=row['Abbreviation'],
                    color_hex=row['Color'],
                    elo = float(row['Elo'])
                )

        self.stdout.write(self.style.SUCCESS('Successfully imported NFL teams'))
