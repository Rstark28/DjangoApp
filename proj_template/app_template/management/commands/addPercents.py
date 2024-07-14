import csv
from django.core.management.base import BaseCommand
from app_template.models import Projection

class Command(BaseCommand):
    help = 'Import NFL teams from a CSV file'

    def handle(self, *args, **kwargs):
        projections = Projection.objects.all()
        for projection in projections:
            projection.playoffPercent = projection.madePlayoffs / projection.n * 100
            projection.save()