from django.contrib import admin
from .models import (
  Team,
  Project,
  UsefulLink,
  ScheduleItem,
  FormDefinition,
  FormSubmission,
  JudgingAppointment,
  ScoreRecord,
  FoodRegistration,
  FoodCheckIn,
  IntegrityReport,
  Announcement,
)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
  list_display = ("team_name", "contact_email", "team_name_locked")
  search_fields = ("team_name", "contact_email")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
  list_display = ("title", "team", "main_category", "is_beginner")
  list_filter = ("main_category", "is_beginner", "uses_ai_ml")
  search_fields = ("title", "team__team_name")


@admin.register(UsefulLink)
class UsefulLinkAdmin(admin.ModelAdmin):
  list_display = ("title", "audience", "is_active")
  list_filter = ("audience", "is_active")


@admin.register(ScheduleItem)
class ScheduleItemAdmin(admin.ModelAdmin):
  list_display = ("title", "due_at", "audience", "is_deadline")
  list_filter = ("audience", "is_deadline")


@admin.register(FormDefinition)
class FormDefinitionAdmin(admin.ModelAdmin):
  list_display = ("title", "audience", "deadline")
  list_filter = ("audience",)
  prepopulated_fields = {"slug": ("title",)}


@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
  list_display = ("form", "team", "submitted_at")
  search_fields = ("team__team_name",)


@admin.register(JudgingAppointment)
class JudgingAppointmentAdmin(admin.ModelAdmin):
  list_display = ("project", "room", "round_name", "start_time")
  list_filter = ("round_name", "room")
  search_fields = ("project__title", "team__team_name")


@admin.register(ScoreRecord)
class ScoreRecordAdmin(admin.ModelAdmin):
  list_display = ("project", "judge", "raw_score", "scaled_score")
  list_filter = ("judge",)


@admin.register(FoodRegistration)
class FoodRegistrationAdmin(admin.ModelAdmin):
  list_display = ("person_name", "team", "meal_type", "badge_id")
  search_fields = ("person_name", "badge_id", "team__team_name")


@admin.register(FoodCheckIn)
class FoodCheckInAdmin(admin.ModelAdmin):
  list_display = ("registration", "checked_in_at", "recorded_by")
  list_filter = ("recorded_by",)


@admin.register(IntegrityReport)
class IntegrityReportAdmin(admin.ModelAdmin):
  list_display = ("project", "status", "updated_at")
  list_filter = ("status",)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
  list_display = ("title", "audience", "is_active", "created_at")
  list_filter = ("audience", "is_active")
