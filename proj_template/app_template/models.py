from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Post(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    date_posted = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(User, on_delete=models.CASCADE)

class HistoricalData(models.Model):
    date = models.DateField()
    season = models.IntegerField()
    neutral = models.BooleanField()
    playoff = models.BooleanField()
    team1 = models.CharField(max_length=50)
    team2 = models.CharField(max_length=50)
    elo1_pre = models.FloatField()
    elo2_pre = models.FloatField()
    elo_prob1 = models.FloatField()
    elo_prob2 = models.FloatField()
    elo1_post = models.FloatField()
    elo2_post = models.FloatField()
    score1 = models.IntegerField()
    score2 = models.IntegerField()
    is_home = models.BooleanField()
    is_win = models.BooleanField()
    gm_no = models.IntegerField()

    def __str__(self):
        return f"{self.date} - {self.team1} vs {self.team2}"

class Quarterbacks(models.Model):
    name = models.CharField(max_length=100)
    QBR = models.FloatField()
    
    def __str__(self):
        return self.name

class NFLTeam(models.Model):
    team_name = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=3, unique=True)
    color_hex = models.CharField(max_length=7)

    # Many-to-Many relationship with HistoricalData
    historical_games = models.ManyToManyField(HistoricalData, related_name='teams', blank=True)

    def __str__(self):
        return self.team_name

class UpcomingGames(models.Model):
    date = models.DateField()
    season = models.IntegerField()
    week = models.IntegerField()
    after_bye_home = models.BooleanField()
    after_bye_away = models.BooleanField()
    city = models.CharField(max_length=100)
    isNeutral = models.BooleanField()
    homeTeam = models.ForeignKey(NFLTeam, related_name='home_teams', on_delete=models.CASCADE)
    awayTeam = models.ForeignKey(NFLTeam, related_name='away_teams', on_delete=models.CASCADE)
    isComplete = models.BooleanField()
    homeScore = models.IntegerField()
    awayScore = models.IntegerField()
    def __str__(self):
        return f"{self.date} - {self.awayTeam} @ {self.homeTeam}"

