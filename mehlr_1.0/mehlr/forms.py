"""
MEHLR 1.0 — Forms
"""
from django import forms
from mehlr.models import Project, Conversation
from mehlr.prompts.project_prompts import PROJECT_PROMPTS


class ChatMessageForm(forms.Form):
    message = forms.CharField(
        max_length=2000,
        widget=forms.Textarea(attrs={
            "id": "chat-input",
            "rows": 3,
            "placeholder": "Mesajınızı yazın… (Enter: gönder, Shift+Enter: yeni satır)",
            "class": "chat-input",
        }),
        error_messages={"required": "Mesaj boş olamaz.", "max_length": "Maksimum 2000 karakter."},
    )
    project_slug = forms.CharField(
        max_length=100, required=False,
        widget=forms.HiddenInput(),
    )
    conversation_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
    )

    def clean_message(self):
        msg = self.cleaned_data.get("message", "").strip()
        if not msg:
            raise forms.ValidationError("Mesaj boş olamaz.")
        return msg


class ReportCreateForm(forms.Form):
    REPORT_TYPE_CHOICES = [
        ("summary",      "Genel Özet"),
        ("trend_report", "Trend Analizi"),
        ("audit_report", "Denetim Raporu"),
        ("performance",  "Performans Raporu"),
        ("custom",       "Özel Sorgu"),
    ]

    project_slug = forms.ChoiceField(
        label="Proje",
        choices=[],  # __init__'te doldurulacak
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    report_type = forms.ChoiceField(
        label="Rapor Türü",
        choices=REPORT_TYPE_CHOICES,
        initial="summary",
        widget=forms.Select(attrs={
            "class": "form-select",
            "id": "report-type-select",
        }),
    )
    custom_query = forms.CharField(
        label="Özel Sorgu",
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={
            "rows": 3,
            "placeholder": "Özel rapor sorunuzu yazın…",
            "class": "form-textarea",
            "id": "custom-query-input",
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        projects = Project.objects.filter(is_active=True).order_by("name")
        self.fields["project_slug"].choices = [
            (p.slug, PROJECT_PROMPTS.get(p.slug, {}).get("display_name", p.name))
            for p in projects
        ]

    def clean(self):
        cleaned = super().clean()
        report_type = cleaned.get("report_type")
        custom_query = cleaned.get("custom_query", "").strip()
        if report_type == "custom" and not custom_query:
            raise forms.ValidationError("Özel rapor türü için sorgu girilmelidir.")
        return cleaned


class ProjectSearchForm(forms.Form):
    q = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "Proje ara…",
            "class": "form-input",
            "autocomplete": "off",
        }),
    )
    project = forms.ChoiceField(
        required=False,
        choices=[("", "Tüm Projeler")],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        projects = Project.objects.filter(is_active=True).order_by("name")
        self.fields["project"].choices += [
            (p.slug, PROJECT_PROMPTS.get(p.slug, {}).get("display_name", p.name))
            for p in projects
        ]


class ConversationTitleForm(forms.ModelForm):
    class Meta:
        model = Conversation
        fields = ["title"]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Konuşma başlığı…",
                "maxlength": 200,
            })
        }
