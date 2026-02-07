from django.urls import path
from . import views

urlpatterns = [
  path("", views.dashboard, name="home"),
  path("dashboard/", views.dashboard, name="dashboard"),
  path("presentations/<int:project_id>/", views.presentation_viewer, name="presentation_viewer"),
]
