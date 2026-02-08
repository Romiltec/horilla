"""
Management command to load Horilla demo data from JSON fixtures.
Can be used from CLI or triggered by LOAD_DEMO_DATA env variable in Docker.
"""

import os

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


# Fixtures that require specific apps to be installed
APP_FIXTURES = [
    ("attendance", "attendance_data.json"),
    ("leave", "leave_data.json"),
    ("asset", "asset_data.json"),
    ("onboarding", "onboarding_data.json"),
    ("offboarding", "offboarding_data.json"),
    ("pms", "pms_data.json"),
    ("payroll", "payroll_data.json"),
    ("project", "project_data.json"),
    ("recruitment", "recruitment_data.json"),
]


class Command(BaseCommand):
    help = "Load Horilla demo data from JSON fixtures in load_data/"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-users",
            action="store_true",
            help="Skip loading user and employee data (use if you already have users)",
        )

    def handle(self, *args, **options):
        load_data_dir = os.path.join(settings.BASE_DIR, "load_data")

        if not os.path.isdir(load_data_dir):
            self.stderr.write(self.style.ERROR(f"Directory not found: {load_data_dir}"))
            return

        # Core fixtures (order matters for foreign key dependencies)
        core_fixtures = []
        if not options["skip_users"]:
            core_fixtures.append("user_data.json")
            core_fixtures.append("employee_info_data.json")
        core_fixtures.append("base_data.json")
        if not options["skip_users"]:
            core_fixtures.append("work_info_data.json")

        # Load core fixtures
        for fixture in core_fixtures:
            fixture_path = os.path.join(load_data_dir, fixture)
            if os.path.exists(fixture_path):
                self.stdout.write(f"Loading {fixture}...")
                try:
                    call_command("loaddata", fixture_path, verbosity=0)
                    self.stdout.write(self.style.SUCCESS(f"  {fixture} loaded"))
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"  Error loading {fixture}: {e}"))
                    return

        # Load app-specific fixtures
        for app_label, fixture_name in APP_FIXTURES:
            if apps.is_installed(app_label):
                fixture_path = os.path.join(load_data_dir, fixture_name)
                if os.path.exists(fixture_path):
                    self.stdout.write(f"Loading {fixture_name}...")
                    try:
                        call_command("loaddata", fixture_path, verbosity=0)
                        self.stdout.write(self.style.SUCCESS(f"  {fixture_name} loaded"))
                    except Exception as e:
                        self.stderr.write(
                            self.style.WARNING(f"  Skipped {fixture_name}: {e}")
                        )

        # Load payroll loan data if payroll is installed
        if apps.is_installed("payroll"):
            loan_fixture = os.path.join(load_data_dir, "payroll_loanaccount_data.json")
            if os.path.exists(loan_fixture):
                self.stdout.write("Loading payroll_loanaccount_data.json...")
                try:
                    call_command("loaddata", loan_fixture, verbosity=0)
                    self.stdout.write(
                        self.style.SUCCESS("  payroll_loanaccount_data.json loaded")
                    )
                except Exception as e:
                    self.stderr.write(
                        self.style.WARNING(
                            f"  Skipped payroll_loanaccount_data.json: {e}"
                        )
                    )

        self.stdout.write(self.style.SUCCESS("\nDemo data loaded successfully!"))
