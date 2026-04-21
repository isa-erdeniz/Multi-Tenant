"""
MEHLR form sınıfları.
"""
from django import forms
from mehlr.models import Conversation, Message


class NewConversationForm(forms.Form):
    """Yeni sohbet başlatma formu."""
    project = forms.CharField(required=False, max_length=50)


class ChatMessageForm(forms.Form):
    """Chat mesajı gönderme formu."""
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 2,
            'placeholder': 'Sorunuzu yazın...',
            'class': 'mehlr-input',
        }),
        max_length=4000,
    )
    conversation_id = forms.IntegerField(required=False)
    project_slug = forms.CharField(required=False, max_length=50)


class ReportRequestForm(forms.Form):
    """Rapor talebi formu."""
    project = forms.CharField(max_length=50)
    report_type = forms.ChoiceField(
        choices=[
            ('daily', 'Günlük'),
            ('weekly', 'Haftalık'),
            ('monthly', 'Aylık'),
            ('custom', 'Özel'),
        ]
    )
    date_from = forms.DateField(required=False)
    date_to = forms.DateField(required=False)
