from django.contrib import admin
from .models import (
  Team,
  Project,
  ProjectList,
  ProjectListEntry,
  UsefulLink,
  SiteContent,
  ScheduleItem,
  FormDefinition,
  FormSubmission,
  JudgingAppointment,
  PresentationSubmission,
  ScoreRecord,
  FoodCheckInStatus,
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


@admin.register(ProjectList)
class ProjectListAdmin(admin.ModelAdmin):
  list_display = ("title", "slug", "audience", "is_default", "sort_field", "sort_descending", "limit", "updated_at")
  list_filter = ("audience", "is_default", "sort_field", "sort_descending")
  search_fields = ("title", "slug")
  prepopulated_fields = {"slug": ("title",)}


@admin.register(ProjectListEntry)
class ProjectListEntryAdmin(admin.ModelAdmin):
  list_display = ("project_list", "project", "is_whitelisted", "is_blacklisted", "manual_rank", "updated_at")
  list_filter = ("project_list", "is_whitelisted", "is_blacklisted")
  search_fields = ("project__title", "project__team__team_name", "project_list__title")


@admin.register(UsefulLink)
class UsefulLinkAdmin(admin.ModelAdmin):
  list_display = ("title", "audience", "is_active")
  list_filter = ("audience", "is_active")


@admin.register(SiteContent)
class SiteContentAdmin(admin.ModelAdmin):
  list_display = ("wifi_name", "updated_at")


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


@admin.register(PresentationSubmission)
class PresentationSubmissionAdmin(admin.ModelAdmin):
  list_display = ("project", "submitted_at", "link_url")
  search_fields = ("project__title", "project__team__team_name")


@admin.register(JudgingAppointment)
class JudgingAppointmentAdmin(admin.ModelAdmin):
  list_display = ("project", "team", "room", "round_name", "category", "start_time", "end_time")
  list_filter = ("round_name", "room", "category")
  search_fields = ("project__title", "team__team_name")
  filter_horizontal = ("judges",)
  
  
@admin.register(ScoreRecord)
class ScoreRecordAdmin(admin.ModelAdmin):
  list_display = ("project", "judge", "appointment", "raw_score", "scaled_score", "updated_at")
  list_filter = ("judge",)
  search_fields = ("project__title", "judge__username", "judge__email", "appointment__room")

@admin.register(FoodCheckInStatus)
class FoodCheckInStatusAdmin(admin.ModelAdmin):
  list_display = ("badge_id", "breakfast", "lunch", "dinner", "midnight_snack", "last_checked_in_at")
  search_fields = ("badge_id",)


@admin.register(IntegrityReport)
class IntegrityReportAdmin(admin.ModelAdmin):
  list_display = ("project", "status", "updated_at")
  list_filter = ("status",)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
  list_display = ("title", "audience", "is_active", "created_at")
  list_filter = ("audience", "is_active")
