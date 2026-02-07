from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
  path("", RedirectView.as_view(url="/dashboard/", permanent=False), name="home"),
  path("dashboard/", views.dashboard, name="dashboard"),
  path("food/", views.food_checkin, name="food_checkin"),
  path("presentations/<int:project_id>/", views.presentation_viewer, name="presentation_viewer"),
]
