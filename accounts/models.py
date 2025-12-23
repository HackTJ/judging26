from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
  class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    JUDGE = "judge", "Judge"
    TEAM = "team", "Team"

  role = models.CharField(
    max_length=10,
    choices=Role.choices,
    default=Role.TEAM,
  )

  def __str__(self):
    return f"{self.username} ({self.role})"
  
  @property
  def is_admin(self):
    return self.role == self.Role.ADMIN

  @property
  def is_judge(self):
    return self.role == self.Role.JUDGE

  @property
  def is_team(self):
    return self.role == self.Role.TEAM
