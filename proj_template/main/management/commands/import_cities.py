import csv
from django.core.management.base import BaseCommand
from main.models import City

class Command(BaseCommand):
    help = 'Import NFL teams from a CSV file'

    def handle(self, *args, **kwargs):
        file_path = 'main/static/csv/cities.csv'
        with open(file_path, mode='r', newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                City.objects.create(
                    name=row["City"],
                    lat = float(row['Latitude']),
                    long = float(row['Longitude'])
                )

        self.stdout.write(self.style.SUCCESS('Successfully imported Cities'))
