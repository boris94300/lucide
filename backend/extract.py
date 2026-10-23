"""Extraction du texte et des QR codes depuis PDF, images ou texte."""
import io
import os

import cv2
import fitz
import numpy as np
from PIL import Image

from . import llm

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}


def _qr_from_image_bytes(data: bytes) -> list[str]:
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return []
    det = cv2.QRCodeDetector()
    out = []
    try:
        ok, decoded, _, _ = det.detectAndDecodeMulti(img)
        if ok:
            out = [d for d in decoded if d]
    except Exception:
        pass
    if not out:
        try:
            d, _, _ = det.detectAndDecode(img)
            if d:
                out = [d]
        except Exception:
            pass
    return out


def _tesseract(data: bytes) -> str:
    try:
        import pytesseract
        img = Image.open(io.BytesIO(data)).convert("RGB")
        if img.width < 1200:
            f = 1200 / img.width
            img = img.resize((int(img.width * f), int(img.height * f)))
        return pytesseract.image_to_string(img, lang="fra+eng")
    except Exception:
        return ""


def extract(filename: str, data: bytes) -> dict:
    """Retourne {text, qr, source, pages}."""
    ext = os.path.splitext(filename.lower())[1]
    qr: list[str] = []

    if ext == ".pdf":
        doc = fitz.open(stream=data, filetype="pdf")
        text = "\n".join(p.get_text() for p in doc)
        for p in doc:
            qr += _qr_from_image_bytes(p.get_pixmap(dpi=150).tobytes("png"))
        source = "pdf-texte"
        if len(text.strip()) < 80:
            ocr = llm.ocr(data, "application/pdf") if llm.enabled() else ""
            if ocr:
                text, source = ocr, "pdf-ocr-mistral"
            else:
                text = "\n".join(_tesseract(p.get_pixmap(dpi=200).tobytes("png")) for p in doc)
                source = "pdf-ocr-local"
        return {"text": text, "qr": qr, "source": source, "pages": len(doc)}

    if ext in IMAGE_EXT:
        qr = _qr_from_image_bytes(data)
        mime = "image/png" if ext == ".png" else "image/jpeg"
        text = llm.ocr(data, mime) if llm.enabled() else ""
        source = "image-ocr-mistral"
        if not text:
            text, source = _tesseract(data), "image-ocr-local"
        return {"text": text, "qr": qr, "source": source, "pages": 1}

    return {"text": data.decode("utf-8", errors="ignore"), "qr": [], "source": "texte", "pages": 1}
