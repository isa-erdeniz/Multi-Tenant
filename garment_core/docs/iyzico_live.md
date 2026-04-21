# iyzico canlı ortam geçiş rehberi

Bu doküman, Garment Core’un **sandbox → production** iyzico entegrasyonu için kontrol listesidir. Ekibin ortak referansı olarak kullanılabilir.

## Ön koşullar

- [ ] iyzico **Merchant panel** erişimi (canlı hesap onayı tamamlandı)
- [ ] Uygulama **HTTPS** ile yayında (webhook ve callback için zorunlu)
- [ ] Ortam değişkenleri / secret’lar güvenli şekilde (ör. Railway, Vault) saklanıyor

## API ve kimlik bilgileri

- [ ] **Canlı API Key** ve **Secret Key** panelden alındı (`IYZICO_API_KEY`, `IYZICO_SECRET_KEY`)
- [ ] **Merchant ID** kaydedildi (`IYZICO_MERCHANT_ID`) — özellikle abonelik webhook imzası (Subscription formatı) için gerekli
- [ ] **Base URL** canlı API host’una ayarlandı  
  Örnek: `api.iyzipay.com` (ortam değişkeni tam URL veya host olabilir; projede SDK için host’a normalize edilir)

## Webhook

- [ ] Panelde **Webhook URL** tanımlandı:  
  `https://<domaininiz>/odemeler/webhook/iyzico/`  
  (Merchant Notifications / Subscription Notifications menüleri iyzico arayüzüne göre doldurulur)
- [ ] **X-Iyz-Signature-V3** özelliği ihtiyaç halinde iyzico ile etkinleştirildi ([dokümantasyon](https://docs.iyzico.com/en/advanced/webhook))
- [ ] Ortamda: `IYZICO_WEBHOOK_VERIFY_SIGNATURE=True`
- [ ] Canlıda: `IYZICO_WEBHOOK_ALLOW_UNSIGNED=False` (imza olmadan kabul etme)
- [ ] Test ödemesi / abonelik bildirimi sonrası sunucu loglarında webhook alındı ve **2xx** döndü
- [ ] Aynı bildirimin tekrarında **idempotent** yanıt (`idempotent: true`) veya tek kayıt — `WebhookEvent` modeli ile çift işlem engellenir

## Uygulama içi davranış

- [ ] Ödeme callback (`/odemeler/callback/`) canlı iyzico yanıtı ile doğrulandı
- [ ] Başarılı ödeme sonrası abonelik (`UserSubscription`) ve plan ataması beklenen şekilde güncelleniyor
- [ ] Para birimi (`IYZICO_CURRENCY`) plan fiyatları ile uyumlu (örn. USD / TRY)

## Güvenlik ve uyumluluk

- [ ] Secret key’ler repoda yok; sadece ortam değişkeninde
- [ ] Yasal sayfalar ve ödeme bilgilendirmeleri canlı sitede erişilebilir (`/legal/...`, footer linkleri)

## Son kontroller

- [ ] Staging veya canlıda **gerçek küçük tutarlı** test işlemi
- [ ] Hata izleme (ör. Sentry) canlıda aktif ve ödeme hataları görünüyor
- [ ] Yedekleme ve veritabanı geri dönüş planı gözden geçirildi

## Sorun giderme

| Belirti | Olası neden |
|--------|----------------|
| 403 webhook | İmza doğrulama başarısız — secret, Merchant ID veya imza sırası |
| 200 ama iş yok | Handler erken çıkıyor; token / `Payment` eşleşmesi loglardan kontrol edilmeli |
| Tekrarlayan webhook | `iyziReferenceCode` ile idempotency kaydı — ikinci istek işlenmez, 200 + `idempotent` |

## İlgili kod

- `apps/payments/webhooks.py` — webhook girişi
- `apps/payments/webhook_signature.py` — `X-Iyz-Signature-V3`
- `apps/payments/models.py` — `WebhookEvent`, `webhook_idempotency_key`
- `config/settings/base.py` — `IYZICO_*` ayarları
