"""python manage.py encrypt_existing --app X --model Y --fields a,b,c [--all-models] [--dry-run] [--all-projects]"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.apps import apps

PROJECT_MODEL_FIELDS = {
    "looopone": [("core", "Reporter", ["tc_kimlik", "phone", "email", "address"]), ("core", "WasteReport", ["location_detail", "reporter_notes"]), ("core", "MunicipalityContact", ["officer_phone", "officer_email"])],
    "worktrackere": [("core", "Customer", ["phone", "email", "address", "notes"]), ("core", "Appointment", ["customer_notes", "internal_notes"])],
    "dressifye_saas": [("core", "UserProfile", ["body_measurements", "phone", "email"]), ("fitting", "TryOnSession", ["user_photo_path"]), ("core", "OrderInfo", ["shipping_address", "phone"])],
    "hairinfinitye": [("core", "Customer", ["phone", "email", "allergy_info", "hair_analysis"]), ("core", "Order", ["shipping_address", "phone", "payment_ref"])],
    "edulingoe": [("core", "Student", ["tc_kimlik", "parent_phone", "parent_email"]), ("core", "Progress", ["voice_recording_path"])],
    "stylecoree": [("core", "Client", ["phone", "email", "company_info"]), ("core", "Project", ["brief_content", "pricing_details"])],
    "drivetrackere": [("core", "Vehicle", ["plate_number", "chassis_number", "registration_info"]), ("core", "Driver", ["tc_kimlik", "license_number", "phone", "email"]), ("core", "Insurance", ["policy_number", "claim_details"])],
    "dressifye": [("core", "UserProfile", ["body_measurements", "phone", "email", "style_preferences"]), ("core", "Order", ["shipping_address", "phone", "payment_ref"])],
    "mehlr": [("mehlr", "APICredential", ["api_key", "api_secret"]), ("mehlr", "QueryLog", ["user_query", "ai_response"]), ("mehlr", "ProjectConfig", ["connection_strings", "auth_tokens"])],
}


class Command(BaseCommand):
    help = "Mevcut düz metin verileri şifreli alanlara dönüştürür"

    def add_arguments(self, parser):
        parser.add_argument("--app", type=str, default=None)
        parser.add_argument("--model", type=str, default=None)
        parser.add_argument("--fields", type=str, default=None)
        parser.add_argument("--all-models", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--all-projects", action="store_true")
        parser.add_argument("--batch-size", type=int, default=500)

    def handle(self, *args, **options):
        if options["all_projects"]:
            self.stdout.write("Her proje dizininde bu komutu --app/--model/--fields veya --all-models ile çalıştırın.")
            return
        app_label = options["app"]
        model_name = options["model"]
        fields_str = options["fields"]
        all_models = options["all_models"]
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN"))
        if all_models and app_label:
            project_id = getattr(__import__("django.conf", fromlist=["settings"]).settings, "ERDENIZ_PROJECT_ID", "current")
            config = [c for c in PROJECT_MODEL_FIELDS.get(project_id, []) if c[0] == app_label]
            total = 0
            for app, model, fields in config:
                n = self._encrypt_model(app, model, fields, batch_size, dry_run)
                total += n
            self.stdout.write(self.style.SUCCESS(f"Toplam {total} kayıt."))
            return
        if not app_label or not model_name:
            self.stderr.write(self.style.ERROR("--app ve --model gerekli (veya --app ile --all-models)"))
            return
        fields = [f.strip() for f in (fields_str or "").split(",") if f.strip()]
        if not fields:
            self.stderr.write(self.style.ERROR("--fields gerekli"))
            return
        count = self._encrypt_model(app_label, model_name, fields, batch_size, dry_run)
        self.stdout.write(self.style.SUCCESS(f"{count} kayıt şifrelendi."))

    def _encrypt_model(self, app_label: str, model_name: str, fields: list[str], batch_size: int, dry_run: bool) -> int:
        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            self.stdout.write(self.style.WARNING(f"Model yok: {app_label}.{model_name}"))
            return 0
        for f in fields:
            if not hasattr(model, f):
                return 0
        qs = model.objects.all()
        total = qs.count()
        if total == 0:
            return 0
        if dry_run:
            self.stdout.write(f"  [DRY RUN] {model_name}: {total} kayıt, alanlar: {fields}")
            return total
        updated = 0
        batch = []
        with transaction.atomic():
            for obj in qs.iterator(chunk_size=batch_size):
                changed = False
                for fn in fields:
                    val = getattr(obj, fn, None)
                    if val is None or (isinstance(val, str) and not val.strip()):
                        continue
                    setattr(obj, fn, val)
                    changed = True
                if changed:
                    batch.append(obj)
                    if len(batch) >= batch_size:
                        model.objects.bulk_update(batch, fields)
                        updated += len(batch)
                        batch = []
            if batch:
                model.objects.bulk_update(batch, fields)
                updated += len(batch)
        return updated
