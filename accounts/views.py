from django.http import HttpResponse
from .decorators import admin_required, judge_required, team_required

@admin_required
def admin_dashboard(request):
  return HttpResponse("Admin dashboard")

@judge_required
def judge_dashboard(request):
  return HttpResponse("Judge dashboard")

@team_required
def team_dashboard(request):
  return HttpResponse("Team dashboard")
