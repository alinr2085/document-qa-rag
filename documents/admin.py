from django.contrib import admin, messages
from django.core.exceptions import ImproperlyConfigured

from .models import Chunk, Document, QueryLog
from .services.rag import LLMError, answer_question
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminUserCreationForm
from django.contrib.auth.models import User


class PersianUserCreationForm(AdminUserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields.get("usable_password")
        if field:
            field.label = "احراز هویت با گذرواژه"
            field.help_text = (
                "مشخص می‌کند کاربر بتواند با گذرواژه وارد شود یا نه. "
                "اگر غیرفعال باشد، کاربر همچنان می‌تواند از روش‌های دیگر "
                "مانند ورود یکپارچه (SSO) یا LDAP وارد شود."
            )
            field.choices = [
                (value, "فعال" if value == "true" else "غیرفعال")
                for value, _label in field.choices
            ]


admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    add_form = PersianUserCreationForm


class ChunkInline(admin.TabularInline):
    model = Chunk
    extra = 0
    can_delete = False
    readonly_fields = ["index", "text"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "chunk_total", "created_at", "updated_at"]
    search_fields = ["title", "content"]
    inlines = [ChunkInline]
    actions = ["reindex"]

    @admin.display(description="تعداد بخش‌ها")
    def chunk_total(self, obj):
        return obj.chunks.count()

    @admin.action(description="بازسازی بخش‌های اسناد انتخاب‌شده")
    def reindex(self, request, queryset):
        for doc in queryset:
            doc.rebuild_chunks()
        self.message_user(request, f"{queryset.count()} سند دوباره پردازش شد.")


@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin):
    """Add = ask a question. Editing the question regenerates the answer."""

    list_display = ["short_question", "model_name", "response_time_ms", "created_at"]
    readonly_fields = ["answer", "sources", "model_name", "response_time_ms", "created_at"]
    search_fields = ["question", "answer"]

    def get_fields(self, request, obj=None):
        if obj is None:
            return ["question"]
        return ["question", "answer", "sources", "model_name", "response_time_ms", "created_at"]

    @admin.display(description="پرسش")
    def short_question(self, obj):
        return obj.question[:70]

    def save_model(self, request, obj, form, change):
        # new question, or an existing one whose text was edited -> ask the model again
        if not change or "question" in form.changed_data:
            try:
                for key, value in answer_question(obj.question).items():
                    setattr(obj, key, value)
            except (ImproperlyConfigured, LLMError) as exc:
                obj.answer = f"[خطا] {exc}"
                obj.sources = []
                messages.error(request, str(exc))
        super().save_model(request, obj, form, change)