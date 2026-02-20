# NOTE i generated this command with gpt for testing might not be complete

from __future__ import annotations

import random
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from core.models import (
    Team,
    Project,
    PresentationSubmission,
    FormDefinition,
    FormSubmission,
    JudgingAppointment,
    ScoreRecord,
)

MOCK_PREFIX = "mock_"
MOCK_EMAIL_DOMAIN = "example.com"


def mock_username(kind: str, idx: int) -> str:
    return f"{MOCK_PREFIX}{kind}{idx}"


def mock_email(username: str) -> str:
    return f"{username}@{MOCK_EMAIL_DOMAIN}"


class Command(BaseCommand):
    help = "Seed realistic mock hackathon judging data"

    def add_arguments(self, parser):
        parser.add_argument("--teams", type=int, default=6)
        parser.add_argument("--judges", type=int, default=4)
        parser.add_argument("--volunteers", type=int, default=2)
        parser.add_argument("--hacktj", type=int, default=1)

        parser.add_argument(
            "--appointments-per-team-per-round",
            dest="appointments_per_team_per_round",
            type=int,
            default=1,
        )

        parser.add_argument("--rounds", type=int, default=2)
        parser.add_argument("--seed", type=int, default=26)

        parser.add_argument("--force", action="store_true")

    @transaction.atomic
    def handle(self, *args, **opts):

        if not settings.DEBUG and not opts["force"]:
            self.stderr.write(
                self.style.ERROR(
                    "Refusing to seed mock data with DEBUG=False.\n"
                    "Use --force if intentional."
                )
            )
            return

        random.seed(opts["seed"])

        now = timezone.now()

        teams_count = opts["teams"]
        judges_count = opts["judges"]
        volunteers_count = opts["volunteers"]
        hacktj_count = opts["hacktj"]
        rounds_count = opts["rounds"]
        appts_per_team_per_round = opts["appointments_per_team_per_round"]

        categories = [c[0] for c in Project.Category.choices]
        rooms = ["A101", "A102", "B201", "B202"]

        # -------------------------
        # CREATE ADMIN
        # -------------------------

        admin_user = self.create_user(
            username=f"{MOCK_PREFIX}admin",
            role=User.Role.ADMIN,
            password="password",
            is_staff=True,
            is_superuser=True,
        )

        self.stdout.write(
            self.style.SUCCESS(f"Admin: {admin_user.username} / password")
        )

        # -------------------------
        # CREATE OTHER USERS
        # -------------------------

        hacktj_users = [
            self.create_user(
                mock_username("hacktj", i),
                User.Role.HACKTJ,
                password="password",
            )
            for i in range(1, hacktj_count + 1)
        ]

        volunteer_users = [
            self.create_user(
                mock_username("vol", i),
                User.Role.VOLUNTEER,
                password="password",
            )
            for i in range(1, volunteers_count + 1)
        ]

        judge_users = [
            self.create_user(
                mock_username("judge", i),
                User.Role.JUDGE,
                password="password",
            )
            for i in range(1, judges_count + 1)
        ]

        team_users = [
            self.create_user(
                mock_username("team", i),
                User.Role.TEAM,
                password="password",
            )
            for i in range(1, teams_count + 1)
        ]

        # -------------------------
        # TEAMS + PROJECTS
        # -------------------------

        teams = []
        projects = []

        for i, user in enumerate(team_users, start=1):

            team, _ = Team.objects.get_or_create(
                team_name=f"Mock Team {i}",
                defaults={
                    "account": user,
                    "contact_email": mock_email(user.username),
                    "members": [f"Member {i}A", f"Member {i}B"],
                    "barcode_prefix": f"MOCK{i:03}",
                    "team_name_locked": True,
                },
            )

            project, _ = Project.objects.get_or_create(
                team=team,
                defaults={
                    "title": f"Mock Project {i}",
                    "preliminary_title": f"Mock Prelim {i}",
                    "description": "Test project for judging",
                    "build_summary": "Built during hackathon",
                    "repo_url": "https://github.com/example/repo",
                    "main_category": random.choice(categories),
                },
            )

            PresentationSubmission.objects.get_or_create(
                project=project,
                defaults={
                    "link_url": f"https://docs.google.com/presentation/d/mock{i}/edit",
                    "is_public_link_valid": True,
                },
            )

            teams.append(team)
            projects.append(project)

        # -------------------------
        # FORM DEF + SUBMISSIONS
        # -------------------------

        form_def, _ = FormDefinition.objects.get_or_create(
            slug="mock-preread",
            defaults={
                "title": "Mock preread",
                "audience": "team",
                "deadline": now + timedelta(days=1),
            },
        )

        for team in teams:
            FormSubmission.objects.get_or_create(
                form=form_def,
                team=team,
                defaults={
                    "data": {
                        "pitch": "This is a mock project pitch"
                    }
                },
            )

        # -------------------------
        # APPOINTMENTS
        # -------------------------

        appointment_count = 0

        round_names = ["prelim", "final"][:rounds_count]

        for round_name in round_names:

            time_cursor = now + timedelta(minutes=30)

            for team, project in zip(teams, projects):

                for _ in range(appts_per_team_per_round):

                    appt = JudgingAppointment.objects.create(
                        team=team,
                        project=project,
                        room=random.choice(rooms),
                        round_name=round_name,
                        category=project.main_category,
                        start_time=time_cursor,
                        end_time=time_cursor + timedelta(minutes=10),
                    )

                    judges = random.sample(
                        judge_users,
                        min(len(judge_users), 2),
                    )

                    appt.judges.add(*judges)

                    for judge in judges:

                        ScoreRecord.objects.get_or_create(
                            appointment=appt,
                            judge=judge,
                            defaults={
                                "project": project,
                                "raw_score": 0,
                            },
                        )

                    appointment_count += 1

                    time_cursor += timedelta(minutes=15)

        # -------------------------
        # DONE
        # -------------------------

        self.stdout.write(
            self.style.SUCCESS(
                f"""
Seed complete.

Teams: {len(teams)}
Projects: {len(projects)}
Judges: {len(judge_users)}
Appointments: {appointment_count}

Login password for all users: password
"""
            )
        )

    # -------------------------
    # USER CREATION HELPER
    # -------------------------

    def create_user(
        self,
        username,
        role,
        password="password",
        is_staff=False,
        is_superuser=False,
    ):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": mock_email(username),
                "role": role,
                "is_staff": is_staff,
                "is_superuser": is_superuser,
            },
        )

        user.set_password(password)
        user.save()

        return user