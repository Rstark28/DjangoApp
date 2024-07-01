from django.core.management.base import BaseCommand
from app_template.models import NFLTeam
from app_template.models import UpcomingGames
from app_template.models import Season
from app_template.models import Projection
import pandas as pd
import requests
from datetime import datetime
from datetime import date

class Command(BaseCommand):
    help = 'Updates/Generates the projections'

        
    def handle(self, *args, **kwargs):
        teams = NFLTeam.objects.all()
        trackerDict = {team.team_name: {
            'Elo': team.elo,
            'TotWins': team.totWins,
            'DivWins': team.divWins,
            'ConfWins': team,
            'TeamsLostTo': [],
            'TeamsBeat': []
        } for team in teams}
        games = UpcomingGames.objects.all().filter(isComplete=False)
        for i in range(17):
            ...
        