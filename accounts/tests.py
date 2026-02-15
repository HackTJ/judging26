from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from core.models import (
  IntegrityReport,
  JudgingAppointment,
  Project,
  ProjectList,
  ProjectListEntry,
  ScoreRecord,
  Team,
)


class ProjectDetailViewTests(TestCase):
  def setUp(self):
    self.team_user = User.objects.create_user(
      username="team-alpha",
      password="password123",
      role=User.Role.TEAM,
    )
    self.team = Team.objects.create(
      team_name="Team Alpha",
      account=self.team_user,
      members=["Ada", "Grace"],
    )
    self.project = Project.objects.create(
      team=self.team,
      title="Portal Beacon",
      description="Enables AR wayfinding.",
    )
    self.url = reverse("project_detail", args=[self.project.id])

  def test_team_can_view_own_project(self):
    self.client.login(username="team-alpha", password="password123")
    response = self.client.get(self.url)
    self.assertEqual(response.status_code, 200)
    self.assertTrue(response.context["is_team_view"])
    self.assertFalse(response.context["show_scores"])

  def test_team_cannot_view_other_projects(self):
    other_user = User.objects.create_user(
      username="team-beta",
      password="password123",
      role=User.Role.TEAM,
    )
    other_team = Team.objects.create(team_name="Team Beta", account=other_user)
    other_project = Project.objects.create(team=other_team, title="Beta App")

    self.client.login(username="team-alpha", password="password123")
    response = self.client.get(reverse("project_detail", args=[other_project.id]))
    self.assertEqual(response.status_code, 403)

  def test_judge_can_view_scores_and_integrity(self):
    judge = User.objects.create_user(
      username="judge-john",
      password="password123",
      role=User.Role.JUDGE,
    )
    appointment = JudgingAppointment.objects.create(
      team=self.team,
      project=self.project,
      room="Room 101",
      round_name="prelim",
      category="AI/ML",
      start_time=timezone.now(),
      end_time=timezone.now() + timezone.timedelta(minutes=10),
    )
    appointment.judges.add(judge)
    ScoreRecord.objects.create(
      appointment=appointment,
      judge=judge,
      project=self.project,
      raw_score=Decimal("85"),
      scaled_score=Decimal("92.5"),
    )
    IntegrityReport.objects.create(
      project=self.project,
      status="pending",
      reviewer_notes="Auto-generated check queued.",
    )

    self.client.login(username="judge-john", password="password123")
    response = self.client.get(self.url)
    self.assertEqual(response.status_code, 200)
    self.assertTrue(response.context["show_scores"])
    self.assertTrue(response.context["score_records"])
    self.assertTrue(response.context["show_integrity"])
    self.assertTrue(response.context["integrity_reports"])

  def test_hacktj_view_hides_scores(self):
    hacktj = User.objects.create_user(
      username="ops-user",
      password="password123",
      role=User.Role.HACKTJ,
    )
    self.client.login(username="ops-user", password="password123")
    response = self.client.get(self.url)
    self.assertEqual(response.status_code, 200)
    self.assertFalse(response.context["show_scores"])
    self.assertFalse(response.context["show_integrity"])

  def test_team_can_submit_category_form(self):
    self.client.login(username="team-alpha", password="password123")
    response = self.client.post(
      self.url,
      {
        "form_type": "category",
        "team_name": "Team Alpha Deluxe",
        "main_category": Project.Category.CYBER,
        "side_beginner": "on",
        "side_social_impact": "on",
        "side_mobile_web": "mobile",
        "side_ai_ml": "on",
        "side_coder": "on",
      },
    )
    self.assertEqual(response.status_code, 302)
    self.team.refresh_from_db()
    self.project.refresh_from_db()
    self.assertEqual(self.team.team_name, "Team Alpha Deluxe")
    self.assertEqual(self.project.main_category, Project.Category.CYBER)
    self.assertTrue(self.project.is_mobile)
    self.assertFalse(self.project.is_web)
    self.assertTrue(self.project.is_beginner)
    self.assertTrue(self.project.uses_ai_ml)
    self.assertIn("social_impact", self.project.eligible_categories)
    self.assertIn("coder", self.project.eligible_categories)
    self.assertIsNotNone(self.project.category_submitted_at)

  def test_team_can_submit_full_form(self):
    self.client.login(username="team-alpha", password="password123")
    response = self.client.post(
      self.url,
      {
        "form_type": "full",
        "preliminary_title": "Beacon Draft",
        "title": "Portal Beacon V2",
        "inspiration": "Students getting lost.",
        "description": "Wayfinding guidance.",
        "ai_usage": "LLM for summaries.",
        "build_summary": "Built with Django + React.",
        "challenges": "Time crunch.",
        "accomplishments": "Working prototype.",
        "repo_url": "https://github.com/example/repo",
        "notes": "Ready for judging.",
      },
    )
    self.assertEqual(response.status_code, 302)
    self.project.refresh_from_db()
    self.assertEqual(self.project.title, "Portal Beacon V2")
    self.assertEqual(self.project.repo_url, "https://github.com/example/repo")
    self.assertIsNotNone(self.project.full_submitted_at)


class ProjectListViewTests(TestCase):
  def setUp(self):
    self.admin = User.objects.create_user(
      username="admin-user",
      password="password123",
      role=User.Role.ADMIN,
    )
    self.judge = User.objects.create_user(
      username="judge-one",
      password="password123",
      role=User.Role.JUDGE,
    )
    self.team_account = User.objects.create_user(
      username="team-viewer",
      password="password123",
      role=User.Role.TEAM,
    )

    self.team1 = Team.objects.create(
      team_name="Eco Warriors",
      account=self.team_account,
      members=["Sky", "Reed"],
    )
    self.project1 = Project.objects.create(
      team=self.team1,
      title="Eco Scanner",
      main_category=Project.Category.SUSTAINABILITY,
      is_beginner=True,
    )

    self.team2 = Team.objects.create(team_name="Cyber Owls")
    self.project2 = Project.objects.create(
      team=self.team2,
      title="Guardian",
      main_category=Project.Category.CYBER,
      uses_ai_ml=True,
    )

    self.team3 = Team.objects.create(team_name="Quantum Ninjas")
    self.project3 = Project.objects.create(
      team=self.team3,
      title="Quantum Sync",
      main_category=Project.Category.SUSTAINABILITY,
    )

    now = timezone.now()
    appointment = JudgingAppointment.objects.create(
      team=self.team1,
      project=self.project1,
      room="A101",
      round_name="prelim",
      category="Sustainability",
      start_time=now,
      end_time=now + timezone.timedelta(minutes=10),
    )
    appointment.judges.add(self.judge)
    ScoreRecord.objects.create(
      appointment=appointment,
      judge=self.judge,
      project=self.project1,
      raw_score=Decimal("82"),
      scaled_score=Decimal("88.5"),
    )

  def test_team_cannot_access_master_list(self):
    self.client.login(username="team-viewer", password="password123")
    response = self.client.get(reverse("project_list"))
    self.assertEqual(response.status_code, 403)

  def test_admin_sees_all_projects_without_config(self):
    self.client.login(username="admin-user", password="password123")
    response = self.client.get(reverse("project_list"))
    self.assertEqual(response.status_code, 200)
    rows = response.context["project_rows"]
    self.assertEqual(len(rows), 3)
    self.assertTrue(response.context["show_scores"])

  def test_project_list_filters_respect_whitelist_and_blacklist(self):
    config = {
      "main_categories": [Project.Category.SUSTAINABILITY],
      "require_flags": ["is_beginner"],
    }
    project_list = ProjectList.objects.create(
      title="Sustainability Focus",
      slug="sustainability-focus",
      audience="admin",
      sort_field=ProjectList.SortField.ALPHABETICAL,
      limit=2,
      filter_config=config,
    )
    ProjectListEntry.objects.create(
      project_list=project_list,
      project=self.project2,
      is_whitelisted=True,
      manual_rank=1,
    )
    ProjectListEntry.objects.create(
      project_list=project_list,
      project=self.project3,
      is_blacklisted=True,
    )

    self.client.login(username="admin-user", password="password123")
    response = self.client.get(reverse("project_list"), {"list": project_list.slug})
    self.assertEqual(response.status_code, 200)
    rows = response.context["project_rows"]
    self.assertEqual(len(rows), 2)
    included_ids = [row["project"].id for row in rows]
    self.assertIn(self.project1.id, included_ids)  # Matches category + beginner
    self.assertIn(self.project2.id, included_ids)  # Forced via whitelist
    self.assertNotIn(self.project3.id, included_ids)  # Blacklisted
    self.assertEqual(rows[0]["project"].id, self.project2.id)  # Manual rank pinned first

  def test_hacktj_view_hides_scores(self):
    hacktj = User.objects.create_user(
      username="ops-view",
      password="password123",
      role=User.Role.HACKTJ,
    )
    self.client.login(username="ops-view", password="password123")
    response = self.client.get(reverse("project_list"))
    self.assertEqual(response.status_code, 200)
    self.assertFalse(response.context["show_scores"])

  def test_default_list_selected_when_available(self):
    ProjectList.objects.create(
      title="Admin Picks",
      slug="admin-picks",
      audience="admin",
      is_default=True,
    )
    ProjectList.objects.create(
      title="General",
      slug="general",
      audience="all",
    )

    self.client.login(username="admin-user", password="password123")
    response = self.client.get(reverse("project_list"))
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.context["selected_list"].slug, "admin-picks")
    self.assertEqual(response.context["list_slug"], "admin-picks")


class MyProjectEntryViewTests(TestCase):
  def setUp(self):
    self.user = User.objects.create_user(
      username="team-entry",
      password="password123",
      role=User.Role.TEAM,
    )
    self.team = Team.objects.create(
      team_name="Entry Team",
      account=self.user,
    )

  def test_team_without_project_gets_created(self):
    self.client.login(username="team-entry", password="password123")
    response = self.client.get(reverse("team_project_entry"))
    self.assertEqual(response.status_code, 302)
    self.team.refresh_from_db()
    project = getattr(self.team, "project", None)
    self.assertIsNotNone(project)
    self.assertEqual(project.title, "Entry Team Project")

  def test_non_team_redirected(self):
    judge = User.objects.create_user(
      username="judge-entry",
      password="password123",
      role=User.Role.JUDGE,
    )
    self.client.login(username="judge-entry", password="password123")
    response = self.client.get(reverse("team_project_entry"))
    self.assertRedirects(response, reverse("dashboard"))
