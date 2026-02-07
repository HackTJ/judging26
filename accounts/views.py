from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from core.models import (
  Announcement,
  FoodCheckIn,
  FoodRegistration,
  FormDefinition,
  FormSubmission,
  IntegrityReport,
  JudgingAppointment,
  PresentationSubmission,
  Project,
  ScheduleItem,
  ScoreRecord,
  UsefulLink,
)
from .models import User


BASIC_EVENT_INFO = [
  {"label": "Location", "value": "Cvent HQ Tysons Corner"},
  {"label": "Contact", "value": "hello@hacktj.org"},
]

USEFUL_LINK_PLACEHOLDERS = []


def _audience_filters(role):
  return ["all", role]


def _effective_role(user: User):
  if (user.is_superuser or user.is_staff) and user.role != User.Role.ADMIN:
    return User.Role.ADMIN
  return user.role


def _forms_for_user(role, team):
  now = timezone.now()
  forms = FormDefinition.objects.filter(
    audience__in=_audience_filters(role),
  ).order_by("deadline")
  data = []

  for form in forms:
    submission = None
    if team:
      submission = FormSubmission.objects.filter(form=form, team=team).first()

    data.append(
      {
        "form": form,
        "submission": submission,
        "is_submitted": submission is not None,
        "deadline_passed": form.deadline < now,
        "total_submissions": form.submissions.count(),
      }
    )

  return data


def _schedule_for_user(role):
  now = timezone.now()
  lookback = now - timedelta(days=1)
  return ScheduleItem.objects.filter(
    audience__in=_audience_filters(role),
    due_at__gte=lookback,
  ).order_by("due_at")


def _links_for_user(role):
  links = UsefulLink.objects.filter(
    is_active=True,
    audience__in=_audience_filters(role),
  ).order_by("title")

  if links.exists():
    return links

  return USEFUL_LINK_PLACEHOLDERS


def _presentation_embed_url(presentation: PresentationSubmission | None) -> str | None:
  if not presentation or not presentation.link_url:
    return None

  url = presentation.link_url.strip()

  if "docs.google.com/presentation" in url:
    if "/embed" in url:
      return url
    if "/edit" in url:
      return url.replace("/edit", "/embed")
    if "edit?" in url:
      return url.replace("edit?", "embed?")
    return url

  return None


@login_required
def dashboard(request):
  user: User = request.user
  team = getattr(user, "team_profile", None)
  project = getattr(team, "project", None) if team else None
  presentation = getattr(project, "presentation", None) if project else None
  presentation_embed_url = _presentation_embed_url(presentation)

  role = _effective_role(user)
  role_display = dict(User.Role.choices).get(role, role.title())

  is_team_role = role == User.Role.TEAM
  show_forms = is_team_role
  show_project_sections = is_team_role
  show_category_section = is_team_role
  show_judging = (is_team_role or role in (User.Role.JUDGE, User.Role.ADMIN, User.Role.HACKTJ))
  show_food_team = is_team_role
  show_food_ops = role in (User.Role.VOLUNTEER, User.Role.ADMIN, User.Role.HACKTJ)
  show_master_projects = role in (User.Role.ADMIN, User.Role.JUDGE, User.Role.HACKTJ)
  show_integrity = role in (User.Role.ADMIN, User.Role.JUDGE)
  show_scoreboard = role in (User.Role.ADMIN, User.Role.JUDGE)
  show_admin_panel = role == User.Role.ADMIN

  forms = _forms_for_user(role, team) if show_forms else []
  schedule_items = _schedule_for_user(role)
  useful_links = _links_for_user(role)
  announcements = Announcement.objects.filter(
    is_active=True,
    audience__in=_audience_filters(role),
  ).order_by("-created_at")[:5]

  upcoming_appointments = []
  if show_judging:
    if is_team_role:
      if team:
        upcoming_appointments = JudgingAppointment.objects.filter(team=team)
      else:
        upcoming_appointments = []
    elif role == User.Role.JUDGE:
      upcoming_appointments = JudgingAppointment.objects.filter(judges=user)
    else:
      upcoming_appointments = JudgingAppointment.objects.all()[:10]

  food_registrations = []
  food_checkins = []
  if show_food_team and team:
    food_registrations = FoodRegistration.objects.filter(team=team).prefetch_related("checkins")
  if show_food_ops:
    food_checkins = FoodCheckIn.objects.select_related("registration").order_by("-checked_in_at")[:25]

  master_projects = Project.objects.select_related("team").all() if show_master_projects else []
  integrity_reports = IntegrityReport.objects.select_related("project").all() if show_integrity else []
  top_scores = ScoreRecord.objects.select_related("project", "judge").order_by("-scaled_score", "-raw_score")[:5] if show_scoreboard else []

  context = {
    "basic_event_info": BASIC_EVENT_INFO,
    "forms": forms,
    "schedule_items": schedule_items,
    "useful_links": useful_links,
    "announcements": announcements,
    "team": team,
    "project": project,
    "presentation": presentation,
    "presentation_embed_url": presentation_embed_url,
    "upcoming_appointments": upcoming_appointments,
    "food_registrations": food_registrations,
    "food_checkins": food_checkins,
    "master_projects": master_projects,
    "integrity_reports": integrity_reports,
    "top_scores": top_scores,
    "role": role,
    "role_display": role_display,
    "show_forms": show_forms,
    "show_project_sections": show_project_sections,
    "show_category_section": show_category_section,
    "show_judging": show_judging,
    "show_food_team": show_food_team,
    "show_food_ops": show_food_ops,
    "show_master_projects": show_master_projects,
    "show_integrity": show_integrity,
    "show_scoreboard": show_scoreboard,
    "show_admin_panel": show_admin_panel,
  }

  return render(request, "dashboard.html", context)


@login_required
def presentation_viewer(request, project_id: int):
  user: User = request.user
  team = getattr(user, "team_profile", None)
  role = _effective_role(user)

  project = get_object_or_404(Project.objects.select_related("team"), id=project_id)
  presentation = getattr(project, "presentation", None)

  if role == User.Role.TEAM:
    if not team or getattr(team, "project_id", None) != project.id:
      raise PermissionDenied("You do not have access to this presentation.")
  elif role not in (User.Role.JUDGE, User.Role.ADMIN, User.Role.HACKTJ):
    raise PermissionDenied("You do not have access to this presentation.")

  context = {
    "project": project,
    "presentation": presentation,
    "presentation_embed_url": _presentation_embed_url(presentation),
  }
  return render(request, "presentation_viewer.html", context)
