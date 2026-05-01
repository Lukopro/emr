from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

class Command(BaseCommand):
    def handle(self, *args, **options):
        Group.objects.get_or_create(name="Admin")
        Group.objects.get_or_create(name="Clinician")
        Group.objects.get_or_create(name="Patient")

        self.stdout.write("Roles created")