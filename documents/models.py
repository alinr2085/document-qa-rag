from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models, transaction

from .services.ingest import extract_docx_text, split_text


class Document(models.Model):
    title = models.CharField("عنوان", max_length=255)
    file = models.FileField(
        "فایل docx",
        upload_to="documents/",
        blank=True,
        validators=[FileExtensionValidator(["docx"])],
        help_text="در صورت آپلود، متن از فایل استخراج و جایگزین «متن کامل» می‌شود.",
    )
    content = models.TextField("متن کامل", blank=True)
    created_at = models.DateTimeField("تاریخ ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین ویرایش", auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "سند"
        verbose_name_plural = "اسناد"

    def __str__(self):
        return self.title

    def clean(self):
        if not self.file and not (self.content or "").strip():
            raise ValidationError("یا یک فایل docx آپلود کنید یا متن سند را وارد کنید.")

    def save(self, *args, **kwargs):
        # A freshly uploaded (not yet committed) file overrides the text
        if self.file and not self.file._committed:
            self.content = extract_docx_text(self.file.file)
        with transaction.atomic():
            super().save(*args, **kwargs)
            self.rebuild_chunks()

    def rebuild_chunks(self):
        self.chunks.all().delete()
        Chunk.objects.bulk_create(
            Chunk(document=self, index=i, text=t)
            for i, t in enumerate(split_text(self.content))
        )


class Chunk(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
    index = models.PositiveIntegerField("شماره بخش")
    text = models.TextField("متن بخش")

    class Meta:
        ordering = ["document_id", "index"]
        verbose_name = "بخش"
        verbose_name_plural = "بخش‌ها"

    def __str__(self):
        return f"{self.document_id}#{self.index}"


class QueryLog(models.Model):
    question = models.TextField("پرسش")
    answer = models.TextField("پاسخ", blank=True)
    sources = models.JSONField("منابع", default=list, blank=True)
    model_name = models.CharField("مدل", max_length=200, blank=True)
    response_time_ms = models.PositiveIntegerField("زمان پاسخ (ms)", default=0)
    created_at = models.DateTimeField("تاریخ", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "تاریخچه پرسش"
        verbose_name_plural = "تاریخچه پرسش‌ها"

    def __str__(self):
        return self.question[:60]