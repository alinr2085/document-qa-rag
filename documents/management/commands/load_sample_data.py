from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from documents.models import Document

TITLES = {
    "leave_policy.docx": "سیاست مرخصی شرکت",
    "remote_work.docx": "آیین‌نامه دورکاری",
    "it_security.docx": "راهنمای امنیت اطلاعات",
}


class Command(BaseCommand):
    help = "Load the sample .docx documents from sample_data/ (skips ones that already exist)."

    def handle(self, *args, **options):
        folder = Path(settings.BASE_DIR) / "sample_data"
        for filename, title in TITLES.items():
            if Document.objects.filter(title=title).exists():
                self.stdout.write(f"skip: {title}")
                continue
            with open(folder / filename, "rb") as f:
                Document(title=title, file=File(f, name=filename)).save()
            self.stdout.write(self.style.SUCCESS(f"loaded: {title}"))
