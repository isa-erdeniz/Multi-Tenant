from django import forms

from .models import Garment


class GarmentForm(forms.ModelForm):
    tags_input = forms.CharField(
        required=False,
        label="Etiketler",
        widget=forms.TextInput(
            attrs={
                "placeholder": "örn. yazlık, rahat, iş",
                "class": "input-field",
            }
        ),
        help_text="Virgülle ayırın: yazlık, rahat, iş",
    )

    class Meta:
        model = Garment
        fields = [
            "name", "category", "subcategory", "color", "color_hex",
            "brand", "size", "material", "pattern", "season",
            "price", "purchase_date", "store_name", "purchase_url",
            "notes", "image",
        ]
        labels = {
            "name": "Kıyafet Adı",
            "category": "Kategori",
            "subcategory": "Alt Kategori",
            "color": "Renk",
            "color_hex": "Renk (Hex)",
            "brand": "Marka",
            "size": "Beden",
            "material": "Kumaş",
            "pattern": "Desen",
            "season": "Mevsim",
            "price": "Fiyat",
            "purchase_date": "Satın Alma Tarihi",
            "store_name": "Mağaza",
            "purchase_url": "Alışveriş Linki",
            "notes": "Notlar",
            "image": "Fotoğraf",
        }
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Kıyafet adı", "class": "input-field"}),
            "category": forms.Select(attrs={"class": "input-field"}),
            "subcategory": forms.Select(attrs={"class": "input-field"}),
            "color": forms.TextInput(attrs={"placeholder": "örn. Lacivert", "class": "input-field"}),
            "color_hex": forms.TextInput(attrs={"placeholder": "#000000", "class": "input-field"}),
            "brand": forms.TextInput(attrs={"placeholder": "Zara, H&M", "class": "input-field"}),
            "size": forms.TextInput(attrs={"placeholder": "M, 38", "class": "input-field"}),
            "material": forms.TextInput(attrs={"placeholder": "Pamuk", "class": "input-field"}),
            "pattern": forms.Select(attrs={"class": "input-field"}),
            "season": forms.Select(attrs={"class": "input-field"}),
            "price": forms.NumberInput(attrs={"placeholder": "0.00", "class": "input-field", "step": "0.01"}),
            "purchase_date": forms.DateInput(attrs={"type": "date", "class": "input-field"}),
            "store_name": forms.TextInput(attrs={"placeholder": "Mağaza adı", "class": "input-field"}),
            "purchase_url": forms.URLInput(attrs={"placeholder": "https://...", "class": "input-field"}),
            "notes": forms.Textarea(attrs={"placeholder": "Notlar", "class": "input-field", "rows": 3}),
            "image": forms.ClearableFileInput(attrs={"class": "hidden", "accept": "image/*", "id": "garment-image-input"}),
        }

    def __init__(self, *args, dark_ui=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].empty_label = "Kategori seçin"
        self.fields["subcategory"].required = False
        self.fields["subcategory"].choices = [
            ("", "Alt kategori seçin"),
        ] + list(Garment.SUBCATEGORY_CHOICES)
        self.fields["pattern"].choices = [
            ("", "Desen seçin"),
        ] + list(Garment.PATTERN_CHOICES)
        self.fields["pattern"].required = False
        if self.instance.pk:
            self.fields["image"].required = False
            if self.instance.tags:
                self.fields["tags_input"].initial = ", ".join(self.instance.tags)

        if dark_ui:
            ctrl = (
                "w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 "
                "text-white placeholder-gray-500 focus:outline-none focus:border-brand-gold"
            )
            ta = ctrl + " resize-y min-h-[5rem]"
            for name, field in self.fields.items():
                w = field.widget
                if name == "image":
                    w.attrs.update(
                        {
                            "class": "sr-only",
                            "accept": "image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp",
                            "id": "id_image",
                        }
                    )
                    continue
                if isinstance(w, (forms.Textarea,)):
                    w.attrs["class"] = ta
                elif isinstance(
                    w,
                    (
                        forms.TextInput,
                        forms.NumberInput,
                        forms.EmailInput,
                        forms.URLInput,
                        forms.DateInput,
                    ),
                ):
                    w.attrs["class"] = ctrl
                elif isinstance(w, forms.Select):
                    w.attrs["class"] = ctrl + " cursor-pointer"

            ch = self.fields.get("color_hex")
            if ch is not None:
                if not self.is_bound:
                    existing = (self.initial.get("color_hex") or "").strip()
                    if not existing and not getattr(self.instance, "pk", None):
                        ch.initial = "#64748b"
                ch.widget = forms.TextInput(
                    attrs={
                        "type": "color",
                        "class": "w-12 h-12 shrink-0 rounded-lg border border-gray-700 cursor-pointer bg-gray-800 p-1",
                        "title": "Renk seçin",
                    }
                )

    def save(self, commit=True):
        instance = super().save(commit=False)
        raw = self.cleaned_data.get("tags_input", "")
        instance.tags = [t.strip() for t in raw.split(",") if t.strip()]
        if commit:
            instance.save()
        return instance
