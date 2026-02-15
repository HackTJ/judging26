from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.models import (
  Announcement,
  FormDefinition,
  FormSubmission,
  IntegrityReport,
  JudgingAppointment,
  PresentationSubmission,
  Project,
  ProjectList,
  ProjectListEntry,
  Team,
  ScheduleItem,
  ScoreRecord,
  SiteContent,
  UsefulLink,
  FoodCheckInStatus,
)
from .models import User
from .forms import ProjectCategoryForm, ProjectSubmissionForm

EVENT_TZ = timezone.get_default_timezone()
CATEGORY_FORM_DEADLINE = timezone.make_aware(datetime(2026, 3, 7, 23, 30), EVENT_TZ)
FULL_SUBMISSION_DEADLINE = timezone.make_aware(datetime(2026, 3, 8, 8, 0), EVENT_TZ)


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


PROJECT_FLAG_FIELD_MAP = {
  "beginner": "is_beginner",
  "is_beginner": "is_beginner",
  "mobile": "is_mobile",
  "is_mobile": "is_mobile",
  "web": "is_web",
  "is_web": "is_web",
  "ai_ml": "uses_ai_ml",
  "uses_ai_ml": "uses_ai_ml",
  "roam": "is_roam",
  "is_roam": "is_roam",
}


def _project_matches_filter(project: Project, filter_config: dict | None) -> bool:
  if not filter_config:
    return True

  main_categories = filter_config.get("main_categories") or filter_config.get("categories")
  if main_categories and project.main_category not in main_categories:
    return False

  eligible_required = filter_config.get("eligible_categories") or []
  if eligible_required:
    project_eligible = set(project.eligible_categories or [])
    if not any(code in project_eligible for code in eligible_required):
      return False

  require_flags = filter_config.get("require_flags") or []
  for flag in require_flags:
    field = PROJECT_FLAG_FIELD_MAP.get(flag, flag)
    if not getattr(project, field, False):
      return False

  exclude_flags = filter_config.get("exclude_flags") or []
  for flag in exclude_flags:
    field = PROJECT_FLAG_FIELD_MAP.get(flag, flag)
    if getattr(project, field, False):
      return False

  return True


def _members_list(team: Team | None) -> list[str]:
  if not team or team.members is None:
    return []

  if isinstance(team.members, list):
    return [m for m in team.members if m]

  if isinstance(team.members, str):
    value = team.members.strip()
    if not value:
      return []
    return [part.strip() for part in value.split(",") if part.strip()]

  return []


def _score_summary_from_records(records):
  if not records:
    return None

  raw_values = [record.raw_score for record in records if record.raw_score is not None]
  scaled_values = [record.scaled_score for record in records if record.scaled_score is not None]

  count = len(records)
  sum_raw = sum(raw_values, Decimal("0")) if raw_values else None
  sum_scaled = sum(scaled_values, Decimal("0")) if scaled_values else None

  return {
    "count": count,
    "avg_raw": (sum_raw / len(raw_values)) if raw_values else None,
    "avg_scaled": (sum_scaled / len(scaled_values)) if scaled_values else None,
    "max_raw": max(raw_values) if raw_values else None,
    "max_scaled": max(scaled_values) if scaled_values else None,
    "min_raw": min(raw_values) if raw_values else None,
    "min_scaled": min(scaled_values) if scaled_values else None,
  }


def _describe_filters(filter_config: dict | None) -> list[str]:
  if not filter_config:
    return []

  descriptions = []

  categories = filter_config.get("main_categories") or filter_config.get("categories")
  if categories:
    category_labels = dict(Project.Category.choices)
    labels = [category_labels.get(code, code.replace("_", " ").title()) for code in categories]
    descriptions.append("Main categories: " + ", ".join(labels))

  eligible = filter_config.get("eligible_categories") or []
  if eligible:
    labels = [code.replace("_", " ").title() for code in eligible]
    descriptions.append("Eligible for: " + ", ".join(labels))

  require_flags = filter_config.get("require_flags") or []
  if require_flags:
    labels = [flag.replace("_", " ").title() for flag in require_flags]
    descriptions.append("Must have: " + ", ".join(labels))

  exclude_flags = filter_config.get("exclude_flags") or []
  if exclude_flags:
    labels = [flag.replace("_", " ").title() for flag in exclude_flags]
    descriptions.append("Exclude: " + ", ".join(labels))

  if filter_config.get("whitelist_only"):
    descriptions.append("Whitelist entries only")

  return descriptions


def _category_form_initial(team: Team, project: Project) -> dict:
  eligible = set(project.eligible_categories or [])
  return {
    "team_name": team.team_name,
    "main_category": project.main_category,
    "side_beginner": project.is_beginner,
    "side_social_impact": "social_impact" in eligible,
    "side_mobile_web": "mobile" if project.is_mobile else "web",
    "side_ai_ml": project.uses_ai_ml,
    "side_roam": project.is_roam,
    "side_coder": "coder" in eligible,
  }


def _apply_side_track_flags(project: Project, tracks: dict):
  eligible = set(project.eligible_categories or [])

  for key in ("social_impact", "coder"):
    if tracks.get(key):
      eligible.add(key)
    else:
      eligible.discard(key)

  project.eligible_categories = sorted(eligible)


def _media_url_or_none(file_field):
  if not file_field:
    return None

  try:
    name = getattr(file_field, "name", "")
    if not name:
      return None
    if file_field.storage.exists(name):
      return file_field.url
  except Exception:
    return None

  return None


@login_required
def dashboard(request):
  user: User = request.user
  team = getattr(user, "team_profile", None)
  project = getattr(team, "project", None) if team else None
  site_content = SiteContent.objects.first()
  presentation = getattr(project, "presentation", None) if project else None
  presentation_embed_url = _presentation_embed_url(presentation)
  site_content_files = {
    "all": _media_url_or_none(site_content.additional_all) if site_content else None,
    "team": _media_url_or_none(site_content.additional_team) if site_content else None,
    "judge": _media_url_or_none(site_content.additional_judge) if site_content else None,
    "hacktj": _media_url_or_none(site_content.additional_hacktj) if site_content else None,
    "admin": _media_url_or_none(site_content.additional_admin) if site_content else None,
    "volunteer": _media_url_or_none(site_content.additional_volunteer) if site_content else None,
  }

  role = _effective_role(user)
  role_display = dict(User.Role.choices).get(role, role.title())

  is_team_role = role == User.Role.TEAM
  show_forms = is_team_role
  show_project_sections = is_team_role
  show_category_section = is_team_role
  show_judging = (is_team_role or role in (User.Role.JUDGE, User.Role.ADMIN, User.Role.HACKTJ))
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

  master_projects = Project.objects.select_related("team").all() if show_master_projects else []
  integrity_reports = IntegrityReport.objects.select_related("project").all() if show_integrity else []
  top_scores = ScoreRecord.objects.select_related("project", "judge").order_by("-scaled_score", "-raw_score")[:5] if show_scoreboard else []

  context = {
    "basic_event_info": BASIC_EVENT_INFO,
    "forms": forms,
    "schedule_items": schedule_items,
    "useful_links": useful_links,
    "announcements": announcements,
    "site_content": site_content,
    "team": team,
    "project": project,
    "presentation": presentation,
    "presentation_embed_url": presentation_embed_url,
    "site_content_files": site_content_files,
    "upcoming_appointments": upcoming_appointments,
    "master_projects": master_projects,
    "integrity_reports": integrity_reports,
    "top_scores": top_scores,
    "role": role,
    "role_display": role_display,
    "show_forms": show_forms,
    "show_project_sections": show_project_sections,
    "show_category_section": show_category_section,
    "show_judging": show_judging,
    "show_master_projects": show_master_projects,
    "show_integrity": show_integrity,
    "show_scoreboard": show_scoreboard,
    "show_admin_panel": show_admin_panel,
    "category_deadline": CATEGORY_FORM_DEADLINE,
    "submission_deadline": FULL_SUBMISSION_DEADLINE,
  }

  return render(request, "dashboard.html", context)


@login_required
def food_checkin(request):
  user: User = request.user
  role = _effective_role(user)

  if role not in (User.Role.ADMIN, User.Role.VOLUNTEER, User.Role.HACKTJ):
    raise PermissionDenied("You do not have access to the food check-in page.")

  meal_options = [
    ("breakfast", "Breakfast"),
    ("lunch", "Lunch"),
    ("dinner", "Dinner"),
    ("midnight_snack", "Midnight Snack"),
  ]

  context = {
    "meal_options": meal_options,
    "status": None,
    "status_data": None,
    "submitted_badge_id": None,
    "selected_meal": None,
  }

  if request.method == "POST":
    badge_id = request.POST.get("badge_id", "").strip()
    meal = request.POST.get("meal", "").strip()

    context["submitted_badge_id"] = badge_id
    context["selected_meal"] = meal

    valid_meals = {key for key, _ in meal_options}
    if not badge_id or not meal:
      context["status"] = ("error", "Scan a badge ID and select a meal.")
    elif meal not in valid_meals:
      context["status"] = ("error", "Invalid meal selection.")
    else:
      status_obj, _ = FoodCheckInStatus.objects.get_or_create(badge_id=badge_id)
      already_checked = getattr(status_obj, meal)
      if already_checked:
        context["status"] = ("warn", f"Already eaten ({meal.replace('_', ' ')})")
      else:
        setattr(status_obj, meal, True)
        status_obj.last_checked_in_by = user
        status_obj.last_checked_in_at = timezone.now()
        status_obj.save()
        context["status"] = ("success", f"Enjoy your {meal.replace('_', ' ')}!")

      context["status_data"] = {
        "breakfast": status_obj.breakfast,
        "lunch": status_obj.lunch,
        "dinner": status_obj.dinner,
        "midnight_snack": status_obj.midnight_snack,
  }

  return render(request, "food_checkin.html", context)


@login_required
def project_list(request):
  user: User = request.user
  role = _effective_role(user)
  allowed_roles = {User.Role.ADMIN, User.Role.JUDGE, User.Role.HACKTJ}

  if role not in allowed_roles:
    raise PermissionDenied("You do not have access to the master project list.")

  show_scores = role in (User.Role.ADMIN, User.Role.JUDGE)

  available_lists = ProjectList.objects.filter(
    audience__in=_audience_filters(role),
  ).order_by("title")

  list_slug = request.GET.get("list", "").strip()
  selected_list = None

  if list_slug:
    selected_list = available_lists.filter(slug=list_slug).first()
    if not selected_list:
      raise Http404("Project list not found.")
  else:
    default_candidates = available_lists.filter(is_default=True)

    if default_candidates.exists():
      selected_list = default_candidates.filter(audience=role).first() or default_candidates.first()

    if not selected_list:
      selected_list = available_lists.first()

  entries_map = {}
  if selected_list:
    entry_qs = ProjectListEntry.objects.filter(project_list=selected_list)
    entries_map = {entry.project_id: entry for entry in entry_qs}

  filter_config = (selected_list.filter_config if selected_list else {}) or {}
  sort_field = selected_list.sort_field if selected_list else ProjectList.SortField.ALPHABETICAL
  sort_desc = selected_list.sort_descending if selected_list else False
  limit = selected_list.limit if selected_list else None

  if not show_scores and sort_field in (ProjectList.SortField.SCORE_RAW, ProjectList.SortField.SCORE_SCALED):
    sort_field = ProjectList.SortField.ALPHABETICAL

  projects = list(
    Project.objects.select_related("team").prefetch_related(
      "score_records",
      "appointments",
    )
  )
  total_projects = len(projects)

  rows = []
  whitelist_only = filter_config.get("whitelist_only")

  for project in projects:
    entry = entries_map.get(project.id)
    include = True

    if entry and entry.is_blacklisted:
      include = False
    elif selected_list:
      include = _project_matches_filter(project, filter_config)
      if whitelist_only:
        include = bool(entry and entry.is_whitelisted)
      elif entry and entry.is_whitelisted:
        include = True

    if not include:
      continue

    team = project.team
    members = _members_list(team)
    appointments = sorted(project.appointments.all(), key=lambda appt: appt.start_time)
    next_appointment = appointments[0] if appointments else None
    score_records = list(project.score_records.all())
    score_summary = _score_summary_from_records(score_records) if score_records else None

    attributes = []
    if project.is_beginner:
      attributes.append("Beginner")
    if project.is_mobile:
      attributes.append("Mobile")
    if project.is_web:
      attributes.append("Web")
    if project.uses_ai_ml:
      attributes.append("AI/ML")
    if project.is_roam:
      attributes.append("Roam")

    rows.append(
      {
        "project": project,
        "team": team,
        "members": members,
        "entry": entry,
        "next_appointment": next_appointment,
        "appointments_count": len(appointments),
        "attributes": attributes,
        "score_summary": score_summary,
      }
    )

  def sort_key(item):
    if sort_field == ProjectList.SortField.ALPHABETICAL:
      return item["project"].title.lower()
    if sort_field == ProjectList.SortField.CREATED:
      return item["project"].created_at
    if sort_field == ProjectList.SortField.SCORE_RAW:
      summary = item["score_summary"] or {}
      return summary.get("avg_raw") or Decimal("-1")
    if sort_field == ProjectList.SortField.SCORE_SCALED:
      summary = item["score_summary"] or {}
      return summary.get("avg_scaled") or Decimal("-1")
    return item["project"].title.lower()

  manual_rows = [row for row in rows if row["entry"] and row["entry"].manual_rank is not None]
  auto_rows = [row for row in rows if row not in manual_rows]

  manual_rows.sort(key=lambda row: row["entry"].manual_rank)
  auto_rows.sort(key=sort_key, reverse=sort_desc)

  ordered_rows = manual_rows + auto_rows

  if limit:
    ordered_rows = ordered_rows[:limit]

  for idx, row in enumerate(ordered_rows, start=1):
    row["rank"] = idx

  active_filters = _describe_filters(filter_config)

  context = {
    "project_rows": ordered_rows,
    "selected_list": selected_list,
    "available_lists": available_lists,
    "list_slug": list_slug or (selected_list.slug if selected_list else ""),
    "show_scores": show_scores,
    "total_projects": total_projects,
    "display_count": len(ordered_rows),
    "limit": limit,
    "active_filters": active_filters,
    "role_display": dict(User.Role.choices).get(role, role.title()),
  }

  return render(request, "projects/list.html", context)


@login_required
def my_project_entry(request):
  user: User = request.user
  role = _effective_role(user)

  if role != User.Role.TEAM:
    messages.error(request, "Only team accounts can access the project submission page.")
    return redirect("dashboard")

  team = getattr(user, "team_profile", None)

  if not team:
    messages.error(request, "You need a team profile before submitting a project. Contact an organizer.")
    return redirect("dashboard")

  project = getattr(team, "project", None)

  if not project:
    default_title = f"{team.team_name} Project".strip() or f"Team {team.id} Project"
    project = Project.objects.create(
      team=team,
      title=default_title,
    )
    messages.success(request, "Project record created. You can now submit your forms.")

  return redirect("project_detail", project_id=project.id)


@login_required
def project_detail(request, project_id: int):
  user: User = request.user
  role = _effective_role(user)

  project = get_object_or_404(
    Project.objects.select_related("team").prefetch_related(
      "appointments",
      "score_records",
      "integrity_reports",
    ),
    pk=project_id,
  )
  team = project.team
  team_profile = getattr(user, "team_profile", None)
  team_account_matches = getattr(team, "account_id", None) == user.id
  team_profile_matches = team_profile and team_profile.id == team.id
  is_team_view = role == User.Role.TEAM and (team_account_matches or team_profile_matches)
  allowed_roles = {User.Role.ADMIN, User.Role.JUDGE, User.Role.HACKTJ}

  if not (is_team_view or role in allowed_roles):
    raise PermissionDenied("You do not have access to this project.")

  now = timezone.now()
  category_deadline = CATEGORY_FORM_DEADLINE
  submission_deadline = FULL_SUBMISSION_DEADLINE
  category_locked = now > category_deadline
  submission_locked = now > submission_deadline

  presentation = getattr(project, "presentation", None)
  presentation_embed_url = _presentation_embed_url(presentation)

  category_form = None
  submission_form = None

  if request.method == "POST" and is_team_view:
    form_type = request.POST.get("form_type")
    if form_type == "category":
      category_form = ProjectCategoryForm(request.POST)
      if category_locked:
        messages.error(request, "The category form deadline has passed.")
      elif category_form.is_valid():
        data = category_form.cleaned_data
        selection = data["side_mobile_web"]
        team.team_name = data["team_name"].strip()
        project.main_category = data["main_category"]
        project.is_beginner = data["side_beginner"]
        project.uses_ai_ml = data["side_ai_ml"]
        project.is_roam = data["side_roam"]
        project.is_mobile = selection == "mobile"
        project.is_web = selection == "web"
        _apply_side_track_flags(
          project,
          {
            "social_impact": data["side_social_impact"],
            "coder": data["side_coder"],
          },
        )
        project.category_submitted_at = timezone.now()
        team.save(update_fields=["team_name"])
        project.save(update_fields=[
          "main_category",
          "is_beginner",
          "uses_ai_ml",
          "is_roam",
          "is_mobile",
          "is_web",
          "eligible_categories",
          "category_submitted_at",
        ])
        messages.success(request, "Category preferences saved.")
        return redirect("project_detail", project_id=project.id)
    elif form_type == "full":
      submission_form = ProjectSubmissionForm(request.POST, instance=project)
      if submission_locked:
        messages.error(request, "The full submission deadline has passed.")
      elif submission_form.is_valid():
        project_obj = submission_form.save(commit=False)
        project_obj.full_submitted_at = timezone.now()
        project_obj.save()
        messages.success(request, "Project submission saved.")
        return redirect("project_detail", project_id=project.id)
    else:
      messages.error(request, "Unknown form submission.")

  form_submissions_qs = FormSubmission.objects.filter(team=team).select_related("form").order_by("form__deadline")
  forms_data = []
  for submission in form_submissions_qs:
    data_items = []
    if isinstance(submission.data, dict):
      data_items = sorted(submission.data.items())
    forms_data.append(
      {
        "form": submission.form,
        "submission": submission,
        "data_items": data_items,
      }
    )

  appointments = list(
    project.appointments.select_related("team").prefetch_related("judges").order_by("start_time")
  )

  show_scores = role in (User.Role.ADMIN, User.Role.JUDGE)
  show_integrity = role in (User.Role.ADMIN, User.Role.JUDGE)

  score_records_qs = project.score_records.select_related("judge", "appointment").order_by("-created_at") if show_scores else ScoreRecord.objects.none()
  score_records = list(score_records_qs)

  integrity_reports_qs = project.integrity_reports.select_related("last_reviewed_by").order_by("-updated_at") if show_integrity else project.integrity_reports.none()
  integrity_reports = list(integrity_reports_qs)

  raw_values = [record.raw_score for record in score_records if record.raw_score is not None]
  scaled_values = [record.scaled_score for record in score_records if record.scaled_score is not None]

  score_summary = None
  if score_records:
    count_raw = len(raw_values)
    count_scaled = len(scaled_values)
    sum_raw = sum(raw_values, Decimal("0")) if raw_values else None
    sum_scaled = sum(scaled_values, Decimal("0")) if scaled_values else None
    score_summary = {
      "count": len(score_records),
      "avg_raw": (sum_raw / count_raw) if sum_raw is not None and count_raw else None,
      "avg_scaled": (sum_scaled / count_scaled) if sum_scaled is not None and count_scaled else None,
      "max_raw": max(raw_values) if raw_values else None,
      "max_scaled": max(scaled_values) if scaled_values else None,
      "min_raw": min(raw_values) if raw_values else None,
      "min_scaled": min(scaled_values) if scaled_values else None,
    }

  eligible_categories_raw = project.eligible_categories or []
  category_map = dict(Project.Category.choices)
  eligible_categories = [category_map.get(code, code.title()) for code in eligible_categories_raw]

  members = []
  if isinstance(team.members, list):
    members = team.members
  elif isinstance(team.members, str) and team.members.strip():
    members = [team.members.strip()]

  project_attributes = []
  if project.is_beginner:
    project_attributes.append("Beginner team")
  if project.is_mobile:
    project_attributes.append("Mobile")
  if project.is_web:
    project_attributes.append("Web")
  if project.uses_ai_ml:
    project_attributes.append("Uses AI/ML")
  if project.is_roam:
    project_attributes.append("Roam eligible")
  if project.category_submitted_at:
    project_attributes.append(f"Category submitted {project.category_submitted_at:%b %d, %H:%M}")
  if project.full_submitted_at:
    project_attributes.append(f"Full submission {project.full_submitted_at:%b %d, %H:%M}")

  detail_sections = [
    ("Inspiration", project.inspiration),
    ("What does it do?", project.description),
    ("How did you build it?", project.build_summary),
    ("Challenges", project.challenges),
    ("Accomplishments", project.accomplishments),
    ("Generative AI usage", project.ai_usage),
    ("Notes", project.notes),
  ]
  detail_sections = [section for section in detail_sections if section[1]]

  role_display = dict(User.Role.choices).get(role, role.title())

  if is_team_view:
    if not category_form:
      category_form = ProjectCategoryForm(initial=_category_form_initial(team, project))
    if not submission_form:
      submission_form = ProjectSubmissionForm(instance=project)

  context = {
    "project": project,
    "team": team,
    "members": members,
    "presentation": presentation,
    "presentation_embed_url": presentation_embed_url,
    "forms_data": forms_data,
    "appointments": appointments,
    "show_scores": show_scores,
    "show_integrity": show_integrity,
    "score_records": score_records,
    "score_summary": score_summary,
    "integrity_reports": integrity_reports,
    "eligible_categories": eligible_categories,
    "project_attributes": project_attributes,
    "detail_sections": detail_sections,
    "is_team_view": is_team_view,
    "role": role,
    "role_display": role_display,
    "category_form": category_form,
    "submission_form": submission_form,
    "category_deadline": category_deadline,
    "submission_deadline": submission_deadline,
    "category_locked": category_locked,
    "submission_locked": submission_locked,
  }

  return render(request, "projects/detail.html", context)


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
