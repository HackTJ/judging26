from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Project, ProjectList, ProjectListEntry, Team


class ProjectListModelTests(TestCase):
  def setUp(self):
    self.team = Team.objects.create(team_name="Team Phoenix")
    self.project = Project.objects.create(
      team=self.team,
      title="Phoenix AI",
    )

  def test_project_list_str(self):
    project_list = ProjectList.objects.create(
      title="Top Projects",
      slug="top-projects",
    )
    self.assertEqual(str(project_list), "Top Projects")
    self.assertEqual(project_list.filter_config, {})

  def test_project_list_entry_flags_are_mutually_exclusive(self):
    project_list = ProjectList.objects.create(
      title="Finalists",
      slug="finalists",
    )
    entry = ProjectListEntry(
      project_list=project_list,
      project=self.project,
      is_whitelisted=True,
      is_blacklisted=True,
    )

    with self.assertRaises(ValidationError):
      entry.full_clean()

  def test_project_list_entry_unique_per_project(self):
    project_list = ProjectList.objects.create(
      title="Room 101",
      slug="room-101",
    )
    ProjectListEntry.objects.create(
      project_list=project_list,
      project=self.project,
    )

    duplicate = ProjectListEntry(
      project_list=project_list,
      project=self.project,
    )

    with self.assertRaises(ValidationError):
      duplicate.full_clean()
