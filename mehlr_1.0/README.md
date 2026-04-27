# mehlr_1.0 — ErdenizTech AI Engine

Model for Enhanced Heuristic Learning & Reasoning — ErdenizTech bünyesindeki SaaS projelerine akıllı veri analizi, otomasyon ve karar destek hizmetleri sunan Django uygulaması.

## Teknoloji

- Python 3.11+, Django 5.x
- Google Gemini API (google-generativeai)
- Tailwind CSS, HTMX, Markdown
- SQLite (geliştirme) / PostgreSQL (üretim)

## Kurulum

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp env.example .env
# .env içinde GEMINI_API_KEY ve SECRET_KEY düzenleyin
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- **Dashboard:** http://127.0.0.1:8000/mehlr/
- **Sohbet:** http://127.0.0.1:8000/mehlr/chat/
- **Admin:** http://127.0.0.1:8000/admin/

## Ortam Değişkenleri (.env)

| Değişken | Açıklama |
|----------|----------|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | True/False |
| `GEMINI_API_KEY` | Google AI Studio API anahtarı |
| `MEHLR_RATE_LIMIT` | Dakikada max sorgu (varsayılan: 15) |
| `MEHLR_CACHE_TTL` | Yanıt önbellek süresi (saniye, varsayılan: 300) |
| `MEHLR_MAX_CONVERSATION_HISTORY` | Sohbette gönderilen son mesaj sayısı (varsayılan: 20) |

## Proje Bağlamları

Admin panelinden **Projeler** ekleyebilir veya varsayılan bağlamlar kodda tanımlıdır (Looopone, WorkTrackere, Dressifye, Hairinfinitye, EduLingoe, StyleCoree, DriveTrackere). Sohbet sırasında proje seçilerek ilgili bağlam Gemini'ye verilir.

## Test

```bash
python manage.py test mehlr
```

## Yapı

- `mehlr/models.py` — Project, Conversation, Message, AnalysisReport, ModuleRegistry
- `mehlr/services/` — ai_engine (Gemini), context_manager, query_processor, report_generator
- `mehlr/modules/` — base_module, analytics, recommendations, automation
- `mehlr/prompts/` — base_prompt, project_prompts

mehlr_1.0 — ErdenizTech. *"Veriyle düşün, akılla hareket et."*
