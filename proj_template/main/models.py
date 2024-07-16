# from django_app/models.py

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()

class Post(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    date_posted = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(User, on_delete=models.CASCADE)

class HistoricalData(models.Model):
    date = models.DateField()
    season = models.PositiveIntegerField()
    neutral = models.BooleanField()
    playoff = models.CharField(max_length=1, null=True, blank=True)
    team1 = models.CharField(max_length=50)
    team2 = models.CharField(max_length=50)
    elo1_pre = models.FloatField(default=0.0)
    elo2_pre = models.FloatField(default=0.0)
    elo_prob1 = models.FloatField(default=0.0)
    elo_prob2 = models.FloatField(default=0.0)
    elo1_post = models.FloatField(default=0.0)
    elo2_post = models.FloatField(default=0.0)
    qbelo1_pre = models.FloatField(default=0.0)
    qbelo2_pre = models.FloatField(default=0.0)
    qb1 = models.CharField(max_length=50, default='')
    qb2 = models.CharField(max_length=50, default='')
    qb1_value_pre = models.FloatField(default=0.0)
    qb2_value_pre = models.FloatField(default=0.0)
    qb1_adj = models.FloatField(default=0.0)
    qb2_adj = models.FloatField(default=0.0)
    qbelo_prob1 = models.FloatField(default=0.0)
    qbelo_prob2 = models.FloatField(default=0.0)
    qb1_game_value = models.FloatField(default=0.0)
    qb2_game_value = models.FloatField(default=0.0)
    qb1_value_post = models.FloatField(default=0.0)
    qb2_value_post = models.FloatField(default=0.0)
    qbelo1_post = models.FloatField(default=0.0)
    qbelo2_post = models.FloatField(default=0.0)
    score1 = models.FloatField(default=0)
    score2 = models.FloatField(default=0)
    quality = models.FloatField(default=0.0)
    importance = models.FloatField(default=0.0)
    total_rating = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.date} - {self.team1} vs {self.team2}"

class Quarterback(models.Model):
    name = models.CharField(max_length=100)
    qbr = models.FloatField()

    def __str__(self):
        return self.name

class NFLTeam(models.Model):
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=100, blank=True)
    abbreviation = models.CharField(max_length=3, unique=True)
    color_hex = models.CharField(max_length=7)
    tot_wins = models.IntegerField(default=0)
    div_wins = models.IntegerField(default=0)
    conf_wins = models.IntegerField(default=0)
    elo = models.FloatField(default=0.0)

    historical_games = models.ManyToManyField(HistoricalData, related_name='teams', blank=True)

    def __str__(self):
        return self.name

class UpcomingGames(models.Model):
    date = models.DateField()
    season = models.IntegerField()
    week = models.IntegerField()
    after_bye_home = models.BooleanField()
    after_bye_away = models.BooleanField()
    city = models.CharField(max_length=100)
    is_neutral = models.BooleanField()
    home_team = models.ForeignKey(NFLTeam, related_name='home_teams', on_delete=models.CASCADE)
    away_team = models.ForeignKey(NFLTeam, related_name='away_teams', on_delete=models.CASCADE)
    is_complete = models.BooleanField()
    home_score = models.IntegerField(default=0)
    away_score = models.IntegerField(default=0)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)
    is_custom = models.BooleanField(default=False, null=True, blank=True)
    is_picked = models.BooleanField(default=False, null=True, blank=True)
    team_picked = models.ForeignKey(NFLTeam, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.date} - {self.away_team} @ {self.home_team}"

class Season(models.Model):
    team = models.ForeignKey(NFLTeam, on_delete=models.CASCADE)
    wins = models.IntegerField()
    playoff_round = models.CharField(max_length=50)
    seeding = models.IntegerField()

class City(models.Model):
    name = models.CharField(max_length=50)
    longitude = models.FloatField()
    latitude = models.FloatField()

class Projection(models.Model):
    team = models.ForeignKey(NFLTeam, on_delete=models.CASCADE)
    n = models.IntegerField()
    mean = models.FloatField()
    median = models.FloatField()
    made_playoffs = models.IntegerField()
    won_division = models.IntegerField()
    won_conference = models.IntegerField()
    won_super_bowl = models.IntegerField()
    standard_deviation = models.FloatField()
    first_quartile = models.FloatField()
    third_quartile = models.FloatField()
    current_week = models.IntegerField(default=0)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_custom = models.BooleanField()

    def __str__(self):
        return f"A projection to win {round(self.median)}, making the playoffs {round(self.made_playoffs / self.n, 4) * 100}% of the time"
