from django.urls import path
from . import views

urlpatterns = [
  path("admin/", views.admin_dashboard, name="admin-dashboard"),
  path("judge/", views.judge_dashboard, name="judge-dashboard"),
  path("team/", views.team_dashboard, name="team-dashboard"),
]
