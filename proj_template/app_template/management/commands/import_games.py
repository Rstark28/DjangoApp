from django.core.management.base import BaseCommand
from app_template.models import NFLTeam
from app_template.models import UpcomingGames
from bs4 import BeautifulSoup
import pandas as pd
import requests
from datetime import datetime

class Command(BaseCommand):
    help = 'Adds Game Results IntoDataBase And Updates Team Elos'

        
    def handle(self, *args, **kwargs):
        teams = NFLTeam.objects.all()
        ByeDict = dict()
        for i in range(1, 19):
            ByeDict[i] = {}
        def get_html(url):
            response = requests.get(url)    
            if response.status_code == 200:
                return response.text
            else:
                return None
        url = f"https://www.pro-football-reference.com/years/{year}/games.htm"
        html = get_html(url)
        if html == None:
            return None
        soup = BeautifulSoup(html, 'html.parser')
        
        scheduleTable = soup.find('table', id='games')
        data = []
        for row in scheduleTable.find_all('tr'):
            cells = row.find_all('td')
            week = row.find_all('th')
            if len(cells) > 0 and week[0].get_text().isdigit(): 
                oldDateForm = cells[1].get_text().split()
                DateDict = {'September': 9, 'October': 10, 'November': 11, 'December': 12, 'January': 1, 'Febuary': 2}
                month = oldDateForm[0]
                if month not in DateDict:
                    self.stdout.write(self.style.ERROR(f"Invalid Month: {month}"))
                    continue
                monthNum = DateDict[month]
                day = oldDateForm[1]
                
                if day < 1 or day > 31:
                    self.stdout.write(self.style.ERROR(f"Invalid Day: {day}"))
                    continue
                
                if month == 1 or month == 2:
                    year = 2025
                else:
                    year = 2024
                currDate = f"{day}-{month}-year".date()

                awayStr = team_name=[2].get_text() 
                homeStr = team_name=cells[5].get_text()
                
                
                currHome = teams.get(homeStr)
                currAway = teams.get(awayStr)
                currWeek = int(week[0].get_text())
                ByeDict[int(currWeek)].add(currHome)
                ByeDict[int(currWeek)].add(currAway)
                
            
                awayBye = int(currWeek) > 1 and (currAway not in ByeDict[currWeek-1])
                homeBye = int(currWeek) > 1 and (currHome not in ByeDict[currWeek-1])
                
                    
                game = UpcomingGames.objects.create(
                    week = currWeek,
                    awayTeam=currAway,
                    homeTeam=currHome,
                    homeScore = 0,
                    awayScore = 0,
                    date=currDate,
                    season = 2024,
                    after_bye_home = homeBye,
                    after_bye_away = awayBye,
                    city = 'Placeholder',
                    isNeutral = False,
                    isComplete = False
                    
                )
                
        