"""
erdeniz_security/encryption.py — Fernet tabanlı şifreleme.
Hem iş projeleri hem kişisel dosyalar için tek katman. Ayrı modül yok.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import string
import struct
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

STREAM_MAGIC = b"EVLT"
STREAM_VERSION = 1
STREAM_HEADER_SIZE = 32
STREAM_CHUNK_SIZE_DEFAULT = 65536
BIG_FILE_THRESHOLD = 100 * 1024 * 1024  # 100MB


class DecryptionError(Exception):
    """Şifre çözme hatası; detay sızdırmadan güvenli mesaj."""

    pass


def _get_fernet_key(key: str | bytes | None) -> bytes:
    if key is not None:
        if isinstance(key, bytes):
            return key
        k = (key if isinstance(key, str) else key.decode("utf-8")).strip()
        if k:
            return k.encode("ascii")
    env_key = ""
    for env_var in ("ERDENIZ_ENCRYPTION_KEY",):
        try:
            env_key = (os.environ.get(env_var) or "").strip()
            if not env_key:
                try:
                    from decouple import config as _config
                    env_key = (_config(env_var, default="") or "").strip()
                except Exception:
                    pass
        except Exception:
            pass
        if env_key:
            break
    if not env_key:
        raise RuntimeError(
            "ERDENIZ_ENCRYPTION_KEY ortam değişkeni tanımlı olmalı.\n"
            "  Linux/macOS: export ERDENIZ_ENCRYPTION_KEY=<key>\n"
            "  Windows CMD: set ERDENIZ_ENCRYPTION_KEY=<key>\n"
            "  Windows PS:  $env:ERDENIZ_ENCRYPTION_KEY='<key>'\n"
            "  Android:     export ERDENIZ_ENCRYPTION_KEY=<key> (Termux)\n"
            "  .env dosyası: ERDENIZ_ENCRYPTION_KEY=<key>\n"
            "Anahtar üretmek için: python manage.py generate_key --type fernet"
        )
    return env_key.encode("ascii")


class ErdenizEncryptor:
    """
    Fernet ile metin ve dict şifreleme/çözme.
    Key verilmezse ERDENIZ_ENCRYPTION_KEY env'den alınır.
    """

    def __init__(self, key: str | None = None) -> None:
        raw = _get_fernet_key(key)
        if isinstance(raw, str):
            raw = raw.encode()
        self._fernet = Fernet(raw)

    def encrypt(self, plaintext: str) -> str:
        """str → şifreli str (base64). Boş string aynen döner."""
        if plaintext is None:
            raise ValueError("plaintext None olamaz")
        if not isinstance(plaintext, str):
            raise TypeError("plaintext str olmalı")
        if not plaintext.strip():
            return plaintext
        token = self._fernet.encrypt(plaintext.encode("utf-8"))
        return token.decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        """Şifreli str → orijinal str. InvalidToken → DecryptionError."""
        if ciphertext is None:
            raise ValueError("ciphertext None olamaz")
        if not isinstance(ciphertext, str):
            raise TypeError("ciphertext str olmalı")
        if not ciphertext.strip():
            return ciphertext
        try:
            return self._fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
        except InvalidToken:
            raise DecryptionError("Şifre çözülemedi.")

    def encrypt_dict(self, data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
        """Belirtilen alanları şifrele; diğerlerine dokunma."""
        if not isinstance(data, dict):
            raise TypeError("data dict olmalı")
        out = dict(data)
        for f in fields:
            if f in out and out[f] is not None and isinstance(out[f], str) and out[f].strip():
                out[f] = self.encrypt(out[f])
        return out

    def decrypt_dict(self, data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
        """Belirtilen şifreli alanları çöz."""
        if not isinstance(data, dict):
            raise TypeError("data dict olmalı")
        out = dict(data)
        for f in fields:
            if f in out and out[f] is not None and isinstance(out[f], str) and out[f].strip():
                try:
                    out[f] = self.decrypt(out[f])
                except DecryptionError:
                    pass
        return out


class FileEncryptor:
    """Dosya/dizin şifreleme (.evault). Proje ve kişisel dosyalar aynı araç."""

    def __init__(self, key: str | None = None) -> None:
        self._enc = ErdenizEncryptor(key)
        self._max_size_warn = BIG_FILE_THRESHOLD

    def encrypt_file(
        self, input_path: Path | str, output_path: Path | None = None
    ) -> Path:
        """Dosyayı şifrele. >=100MB ise otomatik stream modu kullanılır."""
        inp = Path(input_path).expanduser().resolve()
        if hasattr(os, "path"):
            inp = Path(os.path.normpath(inp))
        if not inp.is_file():
            raise FileNotFoundError(f"Dosya bulunamadı: {inp}")
        file_size = inp.stat().st_size
        if file_size >= BIG_FILE_THRESHOLD:
            return self.encrypt_file_stream(inp, output_path)
        if file_size > self._max_size_warn:
            logger.warning("Büyük dosya şifreleniyor (>100MB): %s", inp)
        payload = self._enc._fernet.encrypt(inp.read_bytes())
        out = Path(output_path).expanduser().resolve() if output_path else inp.with_suffix(inp.suffix + ".evault")
        if hasattr(os, "path"):
            out = Path(os.path.normpath(out))
        out.write_bytes(payload)
        return out

    def encrypt_file_stream(
        self,
        input_path: Path | str,
        output_path: Path | None = None,
        chunk_size: int = STREAM_CHUNK_SIZE_DEFAULT,
    ) -> Path:
        """
        Büyük dosyalar için chunk-based şifreleme.
        Header: magic EVLT + version + chunk_count + original_size (32 byte).
        Chunks: [encrypted_chunk_1][encrypted_chunk_2]...
        Footer: SHA-256 hash (tüm şifreli içeriğin bütünlük kontrolü).
        """
        inp = Path(input_path)
        if not inp.is_file():
            raise FileNotFoundError(f"Dosya bulunamadı: {inp}")
        out = Path(output_path) if output_path else inp.with_suffix(inp.suffix + ".evault")
        size = inp.stat().st_size
        chunk_count = (size + chunk_size - 1) // chunk_size
        header = STREAM_MAGIC + struct.pack("<HIQ", STREAM_VERSION, chunk_count, size)
        header = header.ljust(STREAM_HEADER_SIZE, b"\x00")
        hasher = hashlib.sha256()
        hasher.update(header)
        with open(inp, "rb") as fin, open(out, "wb") as fout:
            fout.write(header)
            for i in range(chunk_count):
                chunk = fin.read(chunk_size)
                enc_chunk = self._enc._fernet.encrypt(chunk)
                hasher.update(enc_chunk)
                fout.write(struct.pack(">I", len(enc_chunk)))
                fout.write(enc_chunk)
        footer = hasher.digest()
        with open(out, "ab") as fout:
            fout.write(footer)
        return out

    def decrypt_file_stream(
        self, input_path: Path | str, output_path: Path | None = None
    ) -> Path:
        """Stream şifreli .evault dosyasını çöz. Chunk'lar length-prefixed."""
        inp = Path(input_path)
        if not inp.is_file():
            raise FileNotFoundError(f"Dosya bulunamadı: {inp}")
        data = inp.read_bytes()
        if len(data) < STREAM_HEADER_SIZE + 32:
            raise DecryptionError("Geçersiz stream evault dosyası.")
        header = data[:STREAM_HEADER_SIZE]
        if header[:4] != STREAM_MAGIC:
            raise DecryptionError("Stream magic eşleşmedi.")
        version, chunk_count, original_size = struct.unpack("<HIQ", header[4:18])
        if version != STREAM_VERSION:
            raise DecryptionError("Desteklenmeyen stream versiyonu.")
        footer = data[-32:]
        body = data[STREAM_HEADER_SIZE:-32]
        hasher = hashlib.sha256(header)
        pos = 0
        dec_parts: list[bytes] = []
        fernet = self._enc._fernet
        for _ in range(chunk_count):
            if pos + 4 > len(body):
                break
            (chunk_len,) = struct.unpack(">I", body[pos : pos + 4])
            pos += 4
            if chunk_len <= 0 or pos + chunk_len > len(body):
                raise DecryptionError("Chunk boyutu geçersiz.")
            chunk_enc = body[pos : pos + chunk_len]
            pos += chunk_len
            hasher.update(chunk_enc)
            try:
                dec_parts.append(fernet.decrypt(chunk_enc))
            except InvalidToken:
                raise DecryptionError("Chunk çözülemedi.")
        if hasher.digest() != footer:
            raise DecryptionError("Bütünlük kontrolü başarısız.")
        dec_data = (b"".join(dec_parts))[:original_size]
        out = Path(output_path) if output_path else inp.with_suffix("") if inp.suffix == ".evault" else inp.with_name(inp.stem + "_decrypted")
        out.write_bytes(dec_data)
        return out

    def _decrypt_stream_simple(self, inp: Path, output_path: Path | None) -> Path:
        """Stream formatı çöz (length-prefixed chunks)."""
        return self.decrypt_file_stream(inp, output_path)

    def get_file_info(self, evault_path: Path | str) -> dict[str, Any]:
        """ .evault dosyasının bilgilerini çözmeden döndürür. """
        inp = Path(evault_path)
        if not inp.is_file():
            raise FileNotFoundError(str(inp))
        data = inp.read_bytes()
        if len(data) < STREAM_HEADER_SIZE:
            return {"original_name": inp.stem.replace(".evault", ""), "original_size": None, "encrypted_date": None, "algorithm": "Fernet", "chunk_count": None, "is_stream": False}
        header = data[:STREAM_HEADER_SIZE]
        if header[:4] != STREAM_MAGIC:
            return {"original_name": inp.stem.replace(".evault", ""), "original_size": None, "encrypted_date": None, "algorithm": "Fernet (standart)", "chunk_count": None, "is_stream": False}
        version, chunk_count, original_size = struct.unpack("<HIQ", header[4:18])
        return {
            "original_name": inp.stem.replace(".evault", ""),
            "original_size": original_size,
            "encrypted_date": None,
            "algorithm": "Fernet (stream)",
            "chunk_count": chunk_count,
            "is_stream": True,
        }

    def decrypt_file(
        self, input_path: Path | str, output_path: Path | None = None
    ) -> Path:
        """.evault dosyasını çöz. Stream ise decrypt_file_stream kullanır."""
        inp = Path(input_path)
        if not inp.is_file():
            raise FileNotFoundError(f"Dosya bulunamadı: {inp}")
        data = inp.read_bytes()
        if len(data) >= STREAM_HEADER_SIZE and data[:4] == STREAM_MAGIC:
            return self._decrypt_stream_simple(inp, output_path)
        try:
            dec = self._enc._fernet.decrypt(data)
        except InvalidToken:
            raise DecryptionError("Dosya şifresi çözülemedi.")
        if output_path is None:
            output_path = inp.with_suffix("") if inp.suffix == ".evault" else inp.with_name(inp.stem + "_decrypted")
        Path(output_path).write_bytes(dec)
        return Path(output_path)

    def encrypt_directory(
        self, dir_path: Path | str, pattern: str = "*", recursive: bool = True
    ) -> list[Path]:
        """Dizindeki eşleşen dosyaları toplu şifrele."""
        base = Path(dir_path)
        if not base.is_dir():
            raise NotADirectoryError(str(base))
        paths = list(base.rglob(pattern) if recursive else base.glob(pattern))
        files = [p for p in paths if p.is_file() and p.suffix != ".evault"]
        result: list[Path] = []
        for f in files:
            try:
                result.append(self.encrypt_file(f))
            except Exception as e:
                logger.warning("Şifreleme atlandı %s: %s", f, e)
        return result


def generate_key() -> str:
    """Yeni Fernet anahtarı üret (base64 string)."""
    return Fernet.generate_key().decode("ascii")


def generate_field_encryption_key() -> str:
    """django-encrypted-model-fields için Fernet uyumlu anahtar."""
    return Fernet.generate_key().decode("ascii")


def hash_data(data: str, algorithm: str = "sha256") -> str:
    """Veri bütünlük kontrolü için hash."""
    if not isinstance(data, str):
        data = str(data)
    raw = data.encode("utf-8")
    alg = algorithm.lower()
    if alg == "sha256":
        return hashlib.sha256(raw).hexdigest()
    if alg == "sha384":
        return hashlib.sha384(raw).hexdigest()
    if alg == "sha512":
        return hashlib.sha512(raw).hexdigest()
    if alg == "sha3_256":
        return hashlib.sha3_256(raw).hexdigest()
    raise ValueError(f"Desteklenmeyen algoritma: {algorithm}")


def secure_compare(a: str, b: str) -> bool:
    """Timing-safe string karşılaştırma."""
    return hmac.compare_digest(
        a.encode("utf-8") if isinstance(a, str) else a,
        b.encode("utf-8") if isinstance(b, str) else b,
    )


def generate_password(length: int = 24, symbols: bool = True) -> str:
    """
    CSPRNG ile güçlü şifre üretir. İş ve kişisel kullanım için tek fonksiyon.
    """
    if length < 8:
        raise ValueError("length en az 8 olmalı")
    alphabet = string.ascii_letters + string.digits
    if symbols:
        alphabet += "!@#$%&*+-=?."
    return "".join(secrets.choice(alphabet) for _ in range(length))
