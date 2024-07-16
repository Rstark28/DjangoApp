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

class Quarterbacks(models.Model):
    name = models.CharField(max_length=100)
    QBR = models.FloatField()
    
    def __str__(self):
        return self.name

class NFLTeam(models.Model):
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=100, blank=True)
    abbreviation = models.CharField(max_length=3, unique=True)
    color_hex = models.CharField(max_length=7)
    totWins = models.IntegerField(default=0)
    divWins = models.IntegerField(default=0)
    confWins = models.IntegerField(default=0)
    elo = models.FloatField(default=float(0))

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
    isNeutral = models.BooleanField()
    homeTeam = models.ForeignKey(NFLTeam, related_name='home_teams', on_delete=models.CASCADE)
    awayTeam = models.ForeignKey(NFLTeam, related_name='away_teams', on_delete=models.CASCADE)
    isComplete = models.BooleanField()
    homeScore = models.IntegerField()
    awayScore = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)
    isCustom = models.BooleanField(default=False, null=True, blank=True)
    isPicked = models.BooleanField(default=False, null=True, blank=True)
    teamPicked = models.ForeignKey(NFLTeam, on_delete=models.CASCADE, null=True, blank=True)  

    def __str__(self):
        return f"{self.date} - {self.awayTeam} @ {self.homeTeam}"

class Season(models.Model):
    team = models.ForeignKey(NFLTeam, on_delete=models.CASCADE)
    wins = models.IntegerField()
    playoffRound = models.CharField(max_length=50)
    seeding = models.IntegerField()
    
class City(models.Model):
    name = models.CharField(max_length=50)   
    long = models.FloatField()
    lat = models.FloatField()
    
class Projection(models.Model):
    team = models.ForeignKey(NFLTeam, on_delete=models.CASCADE)
    n = models.IntegerField()
    mean = models.FloatField()
    median = models.FloatField()
    madePlayoffs = models.IntegerField()
    wonDivision = models.IntegerField()
    wonConference = models.IntegerField()
    wonSuperBowl = models.IntegerField()
    stdv = models.FloatField()
    firstquartile = models.FloatField()
    thirdquartile = models.FloatField()
    currWeek = models.IntegerField(default=0)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    isCustom = models.BooleanField()
    
    def __str__(self):
        return f"A projection to win {round(self.median)}, making the playoffs {round(self.madePlayoffs / self.n, 4) * 100}% of the time"
