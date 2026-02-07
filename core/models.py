from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

class TimeStampedModel(models.Model):
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)

  class Meta:
    abstract = True


class Team(TimeStampedModel):
  account = models.OneToOneField(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    blank=True,
    null=True,
    related_name="team_profile",
    help_text="Each team should map to exactly one login account.",
  )
  team_name = models.CharField(max_length=255, unique=True)
  contact_email = models.EmailField(blank=True)
  members = models.JSONField(default=list, blank=True)
  barcode_prefix = models.CharField(
    max_length=32,
    blank=True,
    help_text="Portion of the badge barcode used for quick lookups.",
  )
  team_name_locked = models.BooleanField(
    default=True,
    help_text="Team names are visible to judges and should rarely change.",
  )

  def __str__(self):
    return self.team_name


class Project(TimeStampedModel):
  class Category(models.TextChoices):
    BIOMED = "biomedical", "Biomedical Science"
    SUSTAINABILITY = "sustainability", "Sustainability"
    FINANCE = "finance", "Finance"
    LIFESTYLE = "lifestyle", "Lifestyle"
    CYBER = "cyber", "Cyber Technology"
    QUANTUM = "quantum", "Quantum"
    OTHER = "other", "Other"

  team = models.OneToOneField(
    Team,
    on_delete=models.CASCADE,
    related_name="project",
  )
  preliminary_title = models.CharField(max_length=255, blank=True)
  title = models.CharField(max_length=255)
  inspiration = models.TextField(blank=True)
  description = models.TextField(blank=True, help_text="What does it do?")
  ai_usage = models.TextField(
    blank=True,
    help_text="Detailed generative AI usage explanation.",
  )
  build_summary = models.TextField(blank=True, help_text="How did you build it?")
  challenges = models.TextField(blank=True)
  accomplishments = models.TextField(blank=True)
  repo_url = models.URLField(blank=True)
  notes = models.TextField(blank=True)
  main_category = models.CharField(
    max_length=32,
    choices=Category.choices,
    default=Category.OTHER,
  )
  eligible_categories = models.JSONField(
    default=list,
    blank=True,
    help_text="List of additional categories the project qualifies for.",
  )
  is_beginner = models.BooleanField(default=False)
  is_mobile = models.BooleanField(default=False)
  is_web = models.BooleanField(default=True)
  uses_ai_ml = models.BooleanField(default=False)
  is_roam = models.BooleanField(default=False)
  category_submitted_at = models.DateTimeField(blank=True, null=True)
  full_submitted_at = models.DateTimeField(blank=True, null=True)

  def __str__(self):
    return self.title


class PresentationSubmission(TimeStampedModel):
  project = models.OneToOneField(
    Project,
    on_delete=models.CASCADE,
    related_name="presentation",
  )
  link_url = models.URLField(blank=True)
  is_public_link_valid = models.BooleanField(
    blank=True,
    null=True,
    help_text="Whether the public link has been validated.",
  )
  submitted_at = models.DateTimeField(default=timezone.now)

  class Meta:
    constraints = [
      models.CheckConstraint(
        check=(
          Q(link_url__gt="")
        ),
        name="presentation_submission_google_slides_only",
      ),
    ]

  def clean(self):
    super().clean()
    has_link = bool(self.link_url)

    if not has_link:
      raise ValidationError("Provide a Google Slides link only.")

    if "docs.google.com/presentation" not in self.link_url:
      raise ValidationError("Only Google Slides links are supported.")

  def __str__(self):
    return f"{self.project} - presentation"


class UsefulLink(TimeStampedModel):
  class Audience(models.TextChoices):
    ALL = "all", "Everyone"
    STUDENTS = "team", "Student / Team"
    JUDGES = "judge", "Judges"
    HACKTJ = "hacktj", "HackTJ Team"
    ADMIN = "admin", "Admin"
    VOLUNTEER = "volunteer", "Volunteers"

  title = models.CharField(max_length=255)
  url = models.URLField()
  description = models.CharField(max_length=255, blank=True)
  audience = models.CharField(
    max_length=32,
    choices=Audience.choices,
    default=Audience.ALL,
  )
  is_active = models.BooleanField(default=True)

  def __str__(self):
    return self.title


class SiteContent(TimeStampedModel):
  wifi_name = models.CharField(max_length=128, blank=True)
  wifi_password = models.CharField(max_length=128, blank=True)
  additional_all = models.FileField(
    upload_to="site_content/",
    blank=True,
    null=True,
    help_text="HTML file shown to all roles.",
  )
  additional_team = models.FileField(
    upload_to="site_content/",
    blank=True,
    null=True,
    help_text="HTML file shown to student/team accounts.",
  )
  additional_judge = models.FileField(
    upload_to="site_content/",
    blank=True,
    null=True,
    help_text="HTML file shown to judge accounts.",
  )
  additional_hacktj = models.FileField(
    upload_to="site_content/",
    blank=True,
    null=True,
    help_text="HTML file shown to HackTJ team accounts.",
  )
  additional_admin = models.FileField(
    upload_to="site_content/",
    blank=True,
    null=True,
    help_text="HTML file shown to admin accounts.",
  )
  additional_volunteer = models.FileField(
    upload_to="site_content/",
    blank=True,
    null=True,
    help_text="HTML file shown to volunteer accounts.",
  )

  def __str__(self):
    return "Site content"


class ScheduleItem(TimeStampedModel):
  class Audience(models.TextChoices):
    ALL = "all", "Everyone"
    STUDENTS = "team", "Student / Team"
    JUDGES = "judge", "Judges"
    HACKTJ = "hacktj", "HackTJ Team"
    ADMIN = "admin", "Admin"
    VOLUNTEER = "volunteer", "Volunteers"

  title = models.CharField(max_length=255)
  description = models.TextField(blank=True)
  due_at = models.DateTimeField()
  audience = models.CharField(
    max_length=32,
    choices=Audience.choices,
    default=Audience.ALL,
  )
  is_deadline = models.BooleanField(default=True)

  class Meta:
    ordering = ["due_at"]

  def __str__(self):
    return f"{self.title} ({self.due_at:%Y-%m-%d %H:%M})"


class FormDefinition(TimeStampedModel):
  audience = models.CharField(
    max_length=32,
    choices=ScheduleItem.Audience.choices,
    default=ScheduleItem.Audience.STUDENTS,
  )
  slug = models.SlugField(unique=True)
  title = models.CharField(max_length=255)
  description = models.TextField(blank=True)
  deadline = models.DateTimeField()
  allow_multiple = models.BooleanField(default=False)

  def __str__(self):
    return self.title


class FormSubmission(TimeStampedModel):
  form = models.ForeignKey(
    FormDefinition,
    on_delete=models.CASCADE,
    related_name="submissions",
  )
  team = models.ForeignKey(
    Team,
    on_delete=models.CASCADE,
    related_name="form_submissions",
  )
  data = models.JSONField(default=dict, blank=True)
  submitted_at = models.DateTimeField(default=timezone.now)

  class Meta:
    unique_together = ("form", "team")

  def __str__(self):
    return f"{self.team} - {self.form}"


class JudgingAppointment(TimeStampedModel):
  ROUND_CHOICES = [
    ("prelim", "Preliminary"),
    ("final", "Final"),
  ]

  team = models.ForeignKey(
    Team,
    on_delete=models.CASCADE,
    related_name="appointments",
  )
  project = models.ForeignKey(
    Project,
    on_delete=models.CASCADE,
    related_name="appointments",
  )
  room = models.CharField(max_length=64)
  round_name = models.CharField(max_length=32, choices=ROUND_CHOICES)
  category = models.CharField(max_length=64, blank=True)
  start_time = models.DateTimeField()
  end_time = models.DateTimeField()
  judges = models.ManyToManyField(
    settings.AUTH_USER_MODEL,
    related_name="judging_appointments",
    blank=True,
  )
  rubric_data = models.JSONField(default=dict, blank=True)
  notes = models.TextField(blank=True)
  score_raw = models.DecimalField(
    max_digits=6,
    decimal_places=2,
    blank=True,
    null=True,
  )
  score_scaled = models.DecimalField(
    max_digits=6,
    decimal_places=2,
    blank=True,
    null=True,
  )

  class Meta:
    ordering = ["start_time"]

  def __str__(self):
    return f"{self.project} - {self.room} @ {self.start_time:%Y-%m-%d %H:%M}"


class ScoreRecord(TimeStampedModel):
  appointment = models.ForeignKey(
    JudgingAppointment,
    on_delete=models.CASCADE,
    related_name="score_records",
  )
  judge = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name="score_records",
  )
  project = models.ForeignKey(
    Project,
    on_delete=models.CASCADE,
    related_name="score_records",
  )
  raw_score = models.DecimalField(max_digits=6, decimal_places=2)
  scaled_score = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
  notes = models.TextField(blank=True)

  class Meta:
    unique_together = ("appointment", "judge")

  def __str__(self):
    return f"{self.project} - {self.judge}"


class FoodRegistration(TimeStampedModel):
  team = models.ForeignKey(
    Team,
    on_delete=models.CASCADE,
    related_name="food_registrations",
  )
  person_name = models.CharField(max_length=255)
  badge_id = models.CharField(max_length=64, help_text="Same as barcode on the badge.")
  meal_type = models.CharField(max_length=64)
  notes = models.TextField(blank=True)

  def __str__(self):
    return f"{self.person_name} ({self.meal_type})"


class FoodCheckIn(TimeStampedModel):
  registration = models.ForeignKey(
    FoodRegistration,
    on_delete=models.CASCADE,
    related_name="checkins",
  )
  checked_in_at = models.DateTimeField(auto_now_add=True)
  recorded_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    blank=True,
    null=True,
    related_name="food_checkins",
  )

  def __str__(self):
    return f"{self.registration.person_name} @ {self.checked_in_at}"


class IntegrityReport(TimeStampedModel):
  STATUSES = [
    ("pending", "Pending Review"),
    ("cleared", "Cleared"),
    ("flagged", "Flagged"),
  ]

  project = models.ForeignKey(
    Project,
    on_delete=models.CASCADE,
    related_name="integrity_reports",
  )
  status = models.CharField(max_length=32, choices=STATUSES, default="pending")
  automated_feedback = models.JSONField(default=dict, blank=True)
  reviewer_notes = models.TextField(blank=True)
  last_reviewed_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    blank=True,
    null=True,
    related_name="integrity_reviews",
  )

  def __str__(self):
    return f"{self.project} - {self.status}"


class Announcement(TimeStampedModel):
  title = models.CharField(max_length=255)
  body = models.TextField()
  audience = models.CharField(
    max_length=32,
    choices=ScheduleItem.Audience.choices,
    default=ScheduleItem.Audience.ALL,
  )
  is_active = models.BooleanField(default=True)

  class Meta:
    ordering = ["-created_at"]

  def __str__(self):
    return self.title
