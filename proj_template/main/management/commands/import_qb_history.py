import csv
import os
from django.core.management.base import BaseCommand
from main.models import Quarterback, QuarterbackEloHistory

class Command(BaseCommand):
    help = 'Import quarterback Elo history from a CSV file'

    def handle(self, *args, **options):
        file_path = 'main/static/csv/nfl_elo.csv'
        with open(file_path, mode='r', newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                self.process_row(row)

    def process_row(self, row):
        date = row['date']
        qb1_name = row['qb1']
        qb2_name = row['qb2']
        qb1_value_post = row['qb1_value_post']
        qb2_value_post = row['qb2_value_post']

        if qb1_name:
            self.add_or_update_quarterback(qb1_name, date, qb1_value_post)

        if qb2_name:
            self.add_or_update_quarterback(qb2_name, date, qb2_value_post)

    def add_or_update_quarterback(self, qb_name, date, elo_value_post):
        # Create or get the quarterback
        quarterback, created = Quarterback.objects.get_or_create(name=qb_name)
        
        # Create or update the Elo history entry
        elo_history, created = QuarterbackEloHistory.objects.update_or_create(
            quarterback=quarterback,
            date=date,
            defaults={'elo_value': elo_value_post}
        )
        
        # Log the update
        self.stdout.write(self.style.SUCCESS(f'Updated {qb_name} on {date} with Elo {elo_value_post}'))
