"""
Dosya/klasör şifreleme ve çözme (.evault). Proje ve kişisel dosyalar aynı komut.
  python manage.py encrypt_files --path ~/belgeler/kimlik.pdf
  python manage.py encrypt_files --path /var/www/media/ --recursive
  python manage.py encrypt_files --path dosya.psd --stream
  python manage.py encrypt_files --info dosya.evault
  python manage.py encrypt_files --path ~/media/ --recursive --parallel
  python manage.py encrypt_files --decrypt --path ~/belge.evault
  python manage.py encrypt_files --path ~/dosya.pdf --shred
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from django.core.management.base import BaseCommand

from erdeniz_security.encryption import FileEncryptor


def _secure_delete(path: Path, passes: int = 3) -> None:
    if not path.is_file():
        return
    import os
    length = path.stat().st_size
    with open(path, "ba") as f:
        for _ in range(passes):
            f.seek(0)
            f.write(os.urandom(length))
    path.unlink()


class Command(BaseCommand):
    help = "Dosya veya klasörü şifrele/çöz (.evault)"

    def add_arguments(self, parser):
        parser.add_argument("--path", "-p", required=False)
        parser.add_argument("--decrypt", "-d", action="store_true")
        parser.add_argument("--recursive", "-r", action="store_true")
        parser.add_argument("--shred", action="store_true")
        parser.add_argument("--key", default=None)
        parser.add_argument("--stream", action="store_true", help="Zorla stream modu (büyük dosyalar)")
        parser.add_argument("--info", action="store_true", help=".evault dosya bilgisi göster")
        parser.add_argument("--parallel", action="store_true", help="Paralel şifreleme (--recursive ile)")

    def handle(self, *args, **options):
        path_arg = options.get("path")
        if options["info"]:
            if not path_arg:
                self.stderr.write(self.style.ERROR("--info için --path ile .evault dosyası verin."))
                return
            path = Path(path_arg).expanduser().resolve()
            if not path.is_file():
                self.stderr.write(self.style.ERROR(f"Bulunamadı: {path}"))
                return
            enc = FileEncryptor(options.get("key"))
            try:
                info = enc.get_file_info(path)
            except FileNotFoundError as e:
                self.stderr.write(self.style.ERROR(str(e)))
                return
            size_str = f"{info['original_size'] / (1024*1024):.1f} MB" if info.get("original_size") else "bilinmiyor"
            self.stdout.write(f"Dosya: {path.name}")
            self.stdout.write(f"Orijinal boyut: {size_str}")
            self.stdout.write(f"Şifreleme: {info.get('algorithm', 'N/A')}")
            self.stdout.write(f"Tarih: {info.get('encrypted_date') or 'N/A'}")
            if info.get("is_stream") and info.get("chunk_count") is not None:
                self.stdout.write(f"Chunk sayısı: {info['chunk_count']}")
            self.stdout.write("Bütünlük: ✓ SHA-256 doğrulandı" if info.get("is_stream") else "Bütünlük: (standart)")
            return

        if not path_arg:
            self.stderr.write(self.style.ERROR("--path gerekli (--info hariç)."))
            return
        path = Path(path_arg).expanduser().resolve()
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"Bulunamadı: {path}"))
            return
        enc = FileEncryptor(options.get("key"))
        if options["decrypt"]:
            if not path.is_file():
                self.stderr.write(self.style.ERROR("Çözme için dosya verin."))
                return
            out = enc.decrypt_file(path)
            self.stdout.write(self.style.SUCCESS(f"Çözüldü: {out}"))
            return
        if path.is_file():
            if options["stream"]:
                out = enc.encrypt_file_stream(path)
            else:
                out = enc.encrypt_file(path)
            if options["shred"]:
                _secure_delete(path)
                self.stdout.write("Orijinal güvenli silindi.")
            self.stdout.write(self.style.SUCCESS(f"Şifrelendi: {out}"))
            return
        if path.is_dir():
            if not options["recursive"]:
                self.stderr.write("Klasör için --recursive kullanın.")
                return
            if options["parallel"]:
                files = [p for p in path.rglob("*") if p.is_file() and p.suffix != ".evault"]
                results = []
                with ThreadPoolExecutor(max_workers=4) as ex:
                    futures = {ex.submit(enc.encrypt_file, f): f for f in files}
                    for fut in as_completed(futures):
                        try:
                            results.append(fut.result())
                        except Exception as e:
                            self.stderr.write(self.style.WARNING(f"Atlandı {futures[fut]}: {e}"))
                self.stdout.write(self.style.SUCCESS(f"{len(results)} dosya şifrelendi."))
            else:
                results = enc.encrypt_directory(path, recursive=True)
                self.stdout.write(self.style.SUCCESS(f"{len(results)} dosya şifrelendi."))
            return
