"""
Run via: python manage.py setup_groups

Creates the "Moderators" group with the can_verify_opportunity permission
attached, if it doesn't already exist. Safe to re-run (get_or_create
throughout) — meant to be part of setting up any new environment
(dev, staging, a fresh prod deploy) rather than a one-time manual step in
/admin/ that's easy to forget to repeat.
"""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the Moderators group with the can_verify_opportunity permission"

    def handle(self, *args, **options):
        group, created = Group.objects.get_or_create(name="Moderators")
        permission = Permission.objects.get(codename="can_verify_opportunity")
        group.permissions.add(permission)

        if created:
            self.stdout.write(self.style.SUCCESS("Created 'Moderators' group with can_verify_opportunity."))
        else:
            self.stdout.write("'Moderators' group already existed — permission confirmed attached.")
