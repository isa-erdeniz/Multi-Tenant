"""
mehlr_1.0 — Temel unit testler.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from mehlr.models import Project, Conversation, Message, AnalysisReport
from mehlr.services.context_manager import get_project_context, get_cross_project_context
from mehlr.services.query_processor import classify_query, extract_project, detect_intent
from mehlr.services.report_generator import format_as_markdown, generate, save_report
from mehlr.modules.analytics import AnalyticsModule

User = get_user_model()


class ProjectModelTest(TestCase):
    """Project model testleri."""

    def setUp(self):
        self.project = Project.objects.create(
            name='Test Proje',
            slug='test-proje',
            description='Açıklama',
            project_type='test',
            context_prompt='Bağlam',
            is_active=True,
        )

    def test_project_str(self):
        self.assertEqual(str(self.project), 'Test Proje')

    def test_project_slug_unique(self):
        with self.assertRaises(Exception):
            Project.objects.create(
                name='Diğer',
                slug='test-proje',
                description='x',
                project_type='x',
                context_prompt='x',
            )


class ContextManagerTest(TestCase):
    """Bağlam yönetimi testleri."""

    def test_get_project_context_general(self):
        ctx = get_project_context(None)
        self.assertIn('ErdenizTech', ctx)

    def test_get_project_context_looopone(self):
        ctx = get_project_context('looopone')
        self.assertIn('Looopone', ctx)

    def test_get_cross_project_context(self):
        ctx = get_cross_project_context()
        self.assertIsInstance(ctx, str)


class QueryProcessorTest(TestCase):
    """Sorgu işleme testleri."""

    def test_classify_analysis(self):
        self.assertEqual(classify_query('Looopone analiz et'), 'analysis')

    def test_classify_question(self):
        self.assertEqual(classify_query('Kaç randevu iptal edildi?'), 'question')

    def test_extract_project_looopone(self):
        self.assertEqual(extract_project('Looopone konteyner durumu'), 'looopone')

    def test_detect_intent(self):
        intent = detect_intent('WorkTrackere rapor ver')
        self.assertIn('type', intent)
        self.assertIn('project', intent)


class ReportGeneratorTest(TestCase):
    """Rapor üretici testleri."""

    def setUp(self):
        self.project = Project.objects.create(
            name='Rapor Test',
            slug='rapor-test',
            description='x',
            project_type='test',
            context_prompt='x',
            is_active=True,
        )

    def test_format_as_markdown_dict(self):
        out = format_as_markdown({'a': 1, 'b': 'iki'})
        self.assertIn('**a**', out)
        self.assertIn('**b**', out)

    def test_generate_report(self):
        data = generate(self.project, 'weekly')
        self.assertIsNotNone(data)
        self.assertEqual(data['report_type'], 'weekly')
        self.assertIn('title', data)

    def test_save_report(self):
        data = generate(self.project, 'daily')
        report = save_report(data)
        self.assertIsInstance(report, AnalysisReport)
        self.assertEqual(report.project, self.project)


class AnalyticsModuleTest(TestCase):
    """Analitik modül testleri."""

    def test_analyze_empty_data(self):
        mod = AnalyticsModule()
        result = mod.analyze({}, 'looopone')
        self.assertIn('summary', result)
        self.assertEqual(result['project'], 'looopone')

    def test_is_supported(self):
        mod = AnalyticsModule()
        self.assertTrue(mod.is_supported('looopone'))
        self.assertTrue(mod.is_supported('worktrackere'))


class ViewAccessTest(TestCase):
    """Giriş gerektiren sayfaların testi."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')

    def test_dashboard_requires_login(self):
        res = self.client.get(reverse('mehlr:dashboard'))
        self.assertEqual(res.status_code, 302)
        self.assertIn('login', res.url)

    def test_dashboard_ok_when_logged_in(self):
        self.client.login(username='testuser', password='testpass123')
        res = self.client.get(reverse('mehlr:dashboard'))
        self.assertEqual(res.status_code, 200)

    def test_chat_requires_login(self):
        res = self.client.get(reverse('mehlr:chat'))
        self.assertEqual(res.status_code, 302)

    def test_api_projects_requires_login(self):
        res = self.client.get(reverse('mehlr:api_projects'))
        self.assertEqual(res.status_code, 302)
