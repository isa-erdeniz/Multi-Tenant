"""
mehlr_1.0 — Unit testler.
"""
from unittest.mock import patch
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from mehlr.models import Project, Conversation, Message, AnalysisReport
from mehlr.prompts.base_prompt import (
    build_system_prompt,
    build_analysis_prompt,
    build_fallback_response,
    MEHLR_MASTER_PROMPT,
    COT_INSTRUCTION,
    CONFIDENCE_INSTRUCTION,
)
from mehlr.prompts.project_prompts import PROJECT_PROMPTS, PROJECT_CONTEXTS
from mehlr.services.context_manager import get_project_context, get_enriched_context
from mehlr.services.query_processor import preprocess_query, rewrite_query, validate_response

User = get_user_model()


def _project_kwargs(**overrides):
    base = {
        "name": "Test Projesi",
        "slug": "test-projesi",
        "description": "Test açıklama",
        "project_type": "test",
        "context_prompt": "Test bağlam",
        "is_active": True,
    }
    base.update(overrides)
    return base


class BasePromptTests(TestCase):
    def test_master_prompt_not_empty(self):
        self.assertGreater(len(MEHLR_MASTER_PROMPT), 100)

    def test_build_system_prompt_contains_master(self):
        sp = build_system_prompt("Test proje promptu.")
        self.assertIn("MEHLR", sp)
        self.assertIn("Test proje promptu.", sp)

    def test_build_system_prompt_with_cot(self):
        sp = build_system_prompt("Test.", include_cot=True)
        self.assertIn(COT_INSTRUCTION[:30], sp)

    def test_build_system_prompt_without_cot(self):
        sp = build_system_prompt("Test.", include_cot=False)
        self.assertNotIn(COT_INSTRUCTION[:30], sp)

    def test_build_analysis_prompt_has_confidence(self):
        sp = build_analysis_prompt("Test.")
        self.assertIn("Güven skoru", sp)

    def test_build_fallback_response(self):
        msg = build_fallback_response(
            project_name="Looopone",
            available_context="IoT veri",
            assumption="Sensör analizi",
            missing_info="Doluluk yüzdesi",
        )
        self.assertIn("Looopone", msg)


class ProjectPromptsTests(TestCase):
    ALL_PROJECTS = [
        "looopone",
        "worktrackere",
        "garment-core",
        "hairinfinitye",
        "edulingoe",
        "stylecoree",
        "drivetrackere",
        "dressifye",
        "evidenceandtransparency",
    ]

    def test_all_9_projects_in_prompts(self):
        for key in self.ALL_PROJECTS:
            with self.subTest(project=key):
                self.assertIn(key, PROJECT_PROMPTS)

    def test_each_project_has_required_fields(self):
        required = ["name", "domain", "system_prompt", "capabilities", "analytics_config"]
        for key in self.ALL_PROJECTS:
            with self.subTest(project=key):
                for field in required:
                    self.assertIn(field, PROJECT_PROMPTS[key])

    def test_capabilities_not_empty(self):
        for key in self.ALL_PROJECTS:
            with self.subTest(project=key):
                self.assertGreater(len(PROJECT_PROMPTS[key].get("capabilities", [])), 0)

    def test_garment_core_slug_variants(self):
        ctx_tire = get_project_context("garment-core")
        ctx_alt = get_project_context("garment_core")
        self.assertTrue(bool(ctx_tire) or bool(ctx_alt))

    def test_contexts_has_general(self):
        self.assertIn("general", PROJECT_CONTEXTS)


class ContextManagerTests(TestCase):
    def test_get_project_context_returns_string(self):
        self.assertIsInstance(get_project_context("looopone"), str)

    def test_get_project_context_unknown_falls_back(self):
        self.assertIsInstance(get_project_context("bilinmeyen"), str)

    def test_get_enriched_context_basic(self):
        ctx = get_enriched_context("dressifye", [], "stil önerisi")
        self.assertIsInstance(ctx, str)
        self.assertGreater(len(ctx), 0)

    def test_get_enriched_context_with_history(self):
        history = [
            {"role": "user", "content": "mavi renk yakışır mı?"},
            {"role": "assistant", "content": "Evet, yakışır."},
        ]
        ctx = get_enriched_context("dressifye", history, "peki kırmızı?")
        self.assertIsInstance(ctx, str)


class QueryProcessorTests(TestCase):
    def test_preprocess_analysis_detected(self):
        result = preprocess_query("Araç bakım raporu oluştur")
        self.assertTrue(result["is_analysis"])

    def test_preprocess_empty(self):
        result = preprocess_query("")
        self.assertTrue(len(result["warnings"]) > 0)

    def test_preprocess_truncates_long(self):
        result = preprocess_query("a" * 3000)
        self.assertLessEqual(len(result["query"]), 2000)

    def test_preprocess_turkish_detected(self):
        result = preprocess_query("Merhaba nasılsın")
        self.assertEqual(result["language"], "tr")

    def test_rewrite_short_query(self):
        self.assertIn("Looopone", rewrite_query("nasıl?", "looopone"))

    def test_rewrite_long_query_unchanged(self):
        q = "Bu sensörlerin doluluk verisi neden hatalı görünüyor?"
        self.assertEqual(rewrite_query(q, "looopone"), q)

    def test_validate_good_response(self):
        result = validate_response("Bu Looopone platformu hakkında bilgi " * 5)
        self.assertTrue(result["valid"])

    def test_validate_empty_response(self):
        result = validate_response("")
        self.assertFalse(result["valid"])


class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", password="pass1234")
        self.project = Project.objects.create(**_project_kwargs())

    def test_project_str(self):
        self.assertIn("Test Projesi", str(self.project))

    def test_conversation_create(self):
        conv = Conversation.objects.create(
            user=self.user, project=self.project, title="Test Konuşma"
        )
        self.assertEqual(conv.project, self.project)

    def test_message_create(self):
        conv = Conversation.objects.create(
            user=self.user, project=self.project, title="C"
        )
        msg = Message.objects.create(
            conversation=conv, role=Message.Role.USER, content="Test"
        )
        self.assertEqual(msg.role, "user")

    def test_analysis_report_data_snapshot(self):
        report = AnalysisReport.objects.create(
            project=self.project,
            title="Test Rapor",
            report_type=AnalysisReport.ReportType.CUSTOM,
            content="İçerik",
            data_snapshot={
                "confidence_score": "YÜKSEK",
                "tokens_used": 1024,
                "generation_time": 2.5,
                "has_error": False,
                "error_message": "",
                "response": "Test rapor içeriği.",
            },
        )
        self.assertEqual(report.data_snapshot["confidence_score"], "YÜKSEK")
        self.assertEqual(report.data_snapshot["tokens_used"], 1024)


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user("viewuser", password="pass1234")
        self.project = Project.objects.create(
            **_project_kwargs(name="Looopone", slug="looopone")
        )
        self.client.login(username="viewuser", password="pass1234")

    def test_dashboard_view(self):
        response = self.client.get(reverse("mehlr:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("projects_with_meta", response.context)

    def test_chat_view_no_project(self):
        self.assertEqual(self.client.get(reverse("mehlr:chat")).status_code, 200)

    def test_chat_view_with_project(self):
        response = self.client.get(
            reverse("mehlr:chat_project", kwargs={"project_slug": "looopone"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_project"], self.project)

    def test_report_list_view(self):
        self.assertEqual(
            self.client.get(reverse("mehlr:reports")).status_code, 200
        )

    def test_project_context_api(self):
        response = self.client.get(
            reverse(
                "mehlr:project_context_api",
                kwargs={"project_slug": "looopone"},
            )
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("capabilities", data)
        self.assertIn("display_name", data)

    @patch("mehlr.views.generate_response")
    def test_send_message_htmx(self, mock_gen):
        mock_gen.return_value = ("Test AI yanıtı.", 100, 1.2, None)
        conv = Conversation.objects.create(
            user=self.user, project=self.project, title="T"
        )
        response = self.client.post(
            reverse("mehlr:send_message"),
            {
                "project_slug": "looopone",
                "message": "Sensör verisi analiz et",
                "conversation_id": str(conv.id),
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)

    def test_send_message_empty(self):
        response = self.client.post(
            reverse("mehlr:send_message"),
            {"message": "", "project_slug": "looopone"},
        )
        self.assertEqual(response.status_code, 400)

    def test_login_required(self):
        self.client.logout()
        for name in ["mehlr:dashboard", "mehlr:chat", "mehlr:reports"]:
            with self.subTest(view=name):
                self.assertIn(
                    self.client.get(reverse(name)).status_code, [301, 302]
                )


class TemplateTagTests(TestCase):
    def test_project_display_name(self):
        from mehlr.templatetags.mehlr_tags import project_display_name

        self.assertEqual(project_display_name("dressifye"), "Dressifye")

    def test_project_capabilities(self):
        from mehlr.templatetags.mehlr_tags import project_capabilities

        self.assertGreater(len(project_capabilities("looopone")), 0)

    def test_capability_label(self):
        from mehlr.templatetags.mehlr_tags import capability_label

        self.assertEqual(
            capability_label("outfit_recommendation"), "Outfit Recommendation"
        )

    def test_confidence_color(self):
        from mehlr.templatetags.mehlr_tags import confidence_color

        self.assertEqual(confidence_color("YÜKSEK"), "text-green-600")
        self.assertEqual(confidence_color("ORTA"), "text-yellow-500")
        self.assertEqual(confidence_color("DÜŞÜK"), "text-red-500")

    def test_quality_badge(self):
        from mehlr.templatetags.mehlr_tags import quality_badge

        self.assertIn("green", quality_badge(90))
        self.assertIn("yellow", quality_badge(70))
        self.assertIn("red", quality_badge(40))
