from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from .models import Document, QueryLog
from .services.ingest import extract_docx_text

SAMPLE = Path(settings.BASE_DIR) / "sample_data"


def fake_llm(*args, **kwargs):
    return FakeListChatModel(responses=["۲۶ روز مرخصی استحقاقی [1]"])


@override_settings(OPENROUTER_API_KEY="test", MEDIA_ROOT="/tmp/docqa_test_media")
class DocumentQATests(TestCase):
    def setUp(self):
        call_command("load_sample_data", stdout=StringIO())

    def test_docx_extraction_and_chunks(self):
        with open(SAMPLE / "leave_policy.docx", "rb") as f:
            text = extract_docx_text(f)
        self.assertIn("۲۶ روز", text)
        doc = Document.objects.get(title="سیاست مرخصی شرکت")
        self.assertIn("۲۶ روز", doc.content)
        self.assertGreaterEqual(doc.chunks.count(), 1)

    def test_crud_via_api(self):
        r = self.client.post("/api/documents/", {"title": "t", "content": "سلام دنیا"}, content_type="application/json")
        self.assertEqual(r.status_code, 201)
        pk = r.json()["id"]
        r = self.client.patch(f"/api/documents/{pk}/", {"content": "متن جدید"}, content_type="application/json")
        self.assertEqual(r.json()["content"], "متن جدید")
        self.assertEqual(self.client.delete(f"/api/documents/{pk}/").status_code, 204)

    def test_upload_docx_via_api(self):
        data = (SAMPLE / "remote_work.docx").read_bytes()
        f = SimpleUploadedFile("x.docx", data)
        r = self.client.post("/api/documents/", {"title": "up", "file": f})
        self.assertEqual(r.status_code, 201, r.content)
        self.assertIn("دورکاری", r.json()["content"])

    def test_create_requires_file_or_content(self):
        r = self.client.post("/api/documents/", {"title": "empty"}, content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_search_finds_relevant_document(self):
        r = self.client.post("/api/search/", {"query": "مرخصی استحقاقی چند روز است؟"}, content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()[0]["title"], "سیاست مرخصی شرکت")
        r = self.client.post("/api/search/", {"query": "رمز عبور باید چند کاراکتر باشد"}, content_type="application/json")
        self.assertEqual(r.json()[0]["title"], "راهنمای امنیت اطلاعات")

    def test_index_refreshes_after_delete(self):
        Document.objects.filter(title="سیاست مرخصی شرکت").delete()
        r = self.client.post("/api/search/", {"query": "مرخصی استحقاقی"}, content_type="application/json")
        self.assertTrue(all(x["title"] != "سیاست مرخصی شرکت" for x in r.json()))

    @patch("documents.services.rag.get_llm", fake_llm)
    def test_ask_saves_history(self):
        r = self.client.post("/api/ask/", {"question": "مرخصی استحقاقی چند روز است؟"}, content_type="application/json")
        self.assertEqual(r.status_code, 201, r.content)
        body = r.json()
        self.assertIn("۲۶", body["answer"])
        self.assertEqual(body["sources"][0]["title"], "سیاست مرخصی شرکت")
        self.assertEqual(QueryLog.objects.count(), 1)
        self.assertEqual(self.client.get("/api/history/").json()["count"], 1)
        self.assertEqual(self.client.delete(f"/api/history/{body['id']}/").status_code, 204)

    @patch("documents.services.rag.get_llm", fake_llm)
    def test_ask_without_relevant_docs_skips_llm(self):
        r = self.client.post("/api/ask/", {"question": "qqqq zzzz"}, content_type="application/json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["sources"], [])

    @override_settings(OPENROUTER_API_KEY="")
    def test_ask_without_api_key_returns_503(self):
        r = self.client.post("/api/ask/", {"question": "مرخصی استحقاقی"}, content_type="application/json")
        self.assertEqual(r.status_code, 503)

    @patch("documents.services.rag.get_llm", fake_llm)
    def test_admin_question_form_generates_answer(self):
        get_user_model().objects.create_superuser("admin", "a@a.com", "pass12345")
        self.client.login(username="admin", password="pass12345")
        r = self.client.post("/admin/documents/querylog/add/", {"question": "مرخصی استحقاقی چند روز است؟"})
        self.assertEqual(r.status_code, 302, r.content[:500])
        self.assertIn("۲۶", QueryLog.objects.get().answer)

    def test_swagger_schema(self):
        self.assertEqual(self.client.get("/api/schema/").status_code, 200)
        self.assertEqual(self.client.get("/api/docs/").status_code, 200)


@override_settings(MEDIA_ROOT="/tmp/docqa_test_media")
class AdminThemeTests(TestCase):
    """The admin panel is only restyled (no logic changes) - make sure it still works."""

    def setUp(self):
        call_command("load_sample_data", stdout=StringIO())
        get_user_model().objects.create_superuser("admin", "a@a.com", "pass12345")
        self.client.login(username="admin", password="pass12345")

    def test_admin_pages_render_with_theme(self):
        for url in [
            "/admin/",
            "/admin/documents/document/",
            "/admin/documents/document/add/",
            "/admin/documents/querylog/add/",
        ]:
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 200, url)
                self.assertContains(r, "admin/css/admin-theme.css")

    def test_theme_stylesheet_is_discoverable(self):
        found = finders.find("admin/css/admin-theme.css")
        self.assertIsNotNone(found, "admin-theme.css not found by the staticfiles finder")
        with open(found, encoding="utf-8") as f:
            self.assertIn("--t-primary", f.read())

    def test_login_page_renders_split_layout(self):
        self.client.logout()
        r = self.client.get("/admin/login/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "login-shell")
        # the login form itself must stay untouched
        self.assertContains(r, 'id="login-form"')
        self.assertContains(r, 'name="next"')
        self.assertContains(r, 'name="username"')
        self.assertContains(r, 'name="password"')

    @patch("documents.services.rag.get_llm", fake_llm)
    def test_admin_ask_form_still_generates_answer(self):
        """The restyled admin must keep its 'ask a question' behaviour."""
        r = self.client.post("/admin/documents/querylog/add/", {"question": "مرخصی استحقاقی چند روز است؟"})
        self.assertEqual(r.status_code, 302)
        self.assertIn("۲۶", QueryLog.objects.get().answer)
