from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
  path("", RedirectView.as_view(url="/dashboard/", permanent=False), name="home"),
  path("dashboard/", views.dashboard, name="dashboard"),
  path("food/", views.food_checkin, name="food_checkin"),
  path("presentations/<int:project_id>/", views.presentation_viewer, name="presentation_viewer"),
  path("projects/", views.project_list, name="project_list"),
  path("my-project/", views.my_project_entry, name="team_project_entry"),
  path("projects/<int:project_id>/", views.project_detail, name="project_detail"),
]
