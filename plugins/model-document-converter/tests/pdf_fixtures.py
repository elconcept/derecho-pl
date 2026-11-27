"""Synthetic, temporary PDF fixtures. No real person's document or data is used."""
from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont


FONT_PATH = (Path(__file__).resolve().parents[1] / 'skills' / 'model-ocr' /
             'assets' / 'DejaVuSans.ttf')
POLISH = 'Zażółć gęślą jaźń — ŁÓDŹ, żółć, źdźbło, ćma, ń, ą, ę.'
LONG_LAB_LINE = (
    'KREATYNINA 112 µmol/l  zakres referencyjny 62–106  '
    'materiał: surowica  metoda enzymatyczna  wynik zweryfikowany'
)


@dataclass
class ScanFixture:
    path: Path
    image_bytes: bytes
    expected_words: dict[str, tuple[float, float, float, float]]
    bad_words: dict[str, tuple[float, float, float, float]]
    page_width: float
    page_height: float


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def image_stream_inventory(doc: fitz.Document) -> list[dict]:
    """Independent raw image-byte inventory, not a call into implementation QA."""
    result = []
    for page_number, page in enumerate(doc, start=1):
        for item in page.get_images(full=True):
            xref, mask, width, height, bpc, colorspace = item[:6]
            result.append({
                'page': page_number,
                'xref': xref,
                'mask': mask,
                'width': width,
                'height': height,
                'bpc': bpc,
                'colorspace': colorspace,
                'raw_sha256': sha(doc.xref_stream_raw(xref)),
                'decoded_sha256': sha(doc.xref_stream(xref)),
            })
    return result


def annotation_inventory(doc: fitz.Document) -> list[dict]:
    result = []
    for n, page in enumerate(doc, start=1):
        for annot in page.annots() or []:
            result.append({
                'page': n,
                'type': tuple(annot.type),
                'rect': tuple(annot.rect),
                'content': annot.info.get('content'),
                'name': annot.info.get('name'),
                'flags': annot.flags,
                'colors': annot.colors,
            })
    return result


def rendered_pixels(doc: fitz.Document, page_number: int = 0, dpi: int = 144) -> tuple:
    pix = doc[page_number].get_pixmap(dpi=dpi, alpha=False, annots=True)
    return pix.width, pix.height, pix.n, sha(pix.samples)


def make_scan_pdf(path: Path, *, hidden: bool = True,
                  rotation: int = 0, cropped: bool = False,
                  blank_page: bool = False, redaction_annot: bool = False,
                  native_heading: bool = True) -> ScanFixture:
    """A synthetic scan with independently known visible and hidden values.

    Its JPEG image shows PLT 304 and KREATYNINA 112. Optional hidden OCR instead
    says 30A and 1I2. Other hidden words are already correct and must survive.
    A native PDF heading, vector border and note annotation must also survive.
    """
    if not FONT_PATH.exists():
        raise RuntimeError('Synthetic Unicode fixture requires DejaVuSans.ttf')
    width, height = 612, 792
    scale = 2
    raster = Image.new('RGB', (width * scale, height * scale), 'white')
    draw = ImageDraw.Draw(raster)
    pilfont = ImageFont.truetype(str(FONT_PATH), 12 * scale)
    pilsmall = ImageFont.truetype(str(FONT_PATH), 8 * scale)
    words = [
        ('PLT', 52, 140), ('304', 180, 140),
        ('KREATYNINA', 52, 185), ('112', 220, 185),
        ('SYNTHETIC', 52, 220), ('FIXTURE', 150, 220),
    ]
    for text, x, baseline in words:
        draw.text((x * scale, baseline * scale), text, font=pilfont,
                  fill='black', anchor='ls')
    draw.text((52 * scale, 260 * scale), POLISH, font=pilfont,
              fill='black', anchor='ls')
    draw.text((52 * scale, 300 * scale), LONG_LAB_LINE, font=pilsmall,
              fill='black', anchor='ls')
    draw.line([(52 * scale, 350 * scale), (540 * scale, 350 * scale)],
              fill=(10, 30, 80), width=3)
    output = io.BytesIO()
    raster.save(output, format='JPEG', quality=95, subsampling=0)
    image_bytes = output.getvalue()
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    page.insert_image(page.rect, stream=image_bytes)
    if native_heading:
        page.insert_text((52, 72), 'SYNTHETIC TEST DOCUMENT', fontsize=14)
    page.draw_rect(fitz.Rect(40, 95, 570, 385), color=(0.2, 0.3, 0.6), width=0.5)
    note = page.add_text_annot((565, 405), 'Synthetic note must survive OCR repair')
    note.update()
    if redaction_annot:
        redaction = page.add_redact_annot(fitz.Rect(440, 650, 520, 675),
                                         cross_out=False)
        redaction.set_info(content='Existing redaction annotation: do not apply')
        redaction.update()
    if hidden:
        for text, x, baseline in words:
            mistaken = {'304': '30A', '112': '1I2'}.get(text, text)
            page.insert_text((x, baseline), mistaken, fontsize=12,
                             fontname='fixturefont', fontfile=str(FONT_PATH),
                             render_mode=3)
        page.insert_text((52, 260), POLISH, fontsize=12,
                         fontname='fixturefont', fontfile=str(FONT_PATH),
                         render_mode=3)
        page.insert_text((52, 300), LONG_LAB_LINE, fontsize=8,
                         fontname='fixturefont', fontfile=str(FONT_PATH),
                         render_mode=3)
    if cropped:
        page.set_cropbox(fitz.Rect(20, 30, 592, 762))
    if rotation:
        page.set_rotation(rotation)
    if blank_page:
        doc.new_page(width=width, height=height)
    doc.save(path, garbage=0, deflate=False)
    doc.close()
    expected, wrong = {}, {}
    with fitz.open(path) as reopened:
        p = reopened[0]
        for item in p.get_text('words'):
            token = item[4]
            bbox = tuple(item[:4])
            if token in {'30A', '1I2'}:
                wrong[token] = bbox
                expected[{'30A': '304', '1I2': '112'}[token]] = bbox
            elif token in {'PLT', 'KREATYNINA', 'SYNTHETIC', 'FIXTURE'}:
                expected[token] = bbox
    return ScanFixture(path, image_bytes, expected, wrong, width, height)


def make_image(path: Path, *, fmt: str = 'PNG', size: tuple[int, int] = (900, 1200)) -> Path:
    """Small synthetic image input with no private information."""
    image = Image.new('RGB', size, 'white')
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(FONT_PATH), 32)
    draw.text((70, 100), 'SYNTHETIC IMAGE 123', font=font, fill='black')
    draw.rectangle((55, 70, size[0] - 55, 190), outline='navy', width=3)
    image.save(path, format=fmt, dpi=(300, 300))
    return path


def make_signature_pdf(path: Path, *, populated: bool, real_cms: bool = True) -> Path:
    """Empty field or real self-signed CMS, solely for structural detection.

    A generated certificate is NOT trusted and the fixture is NOT evidence of
    qualified-signature validation. Keys exist only in memory during this call.
    """
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 70), 'SYNTHETIC SIGNATURE DETECTION FIXTURE')
    widget = fitz.Widget()
    widget.field_name = 'SyntheticSignature'
    widget.field_type = fitz.PDF_WIDGET_TYPE_SIGNATURE
    widget.rect = fitz.Rect(50, 100, 250, 145)
    added = page.add_widget(widget)
    if not populated:
        doc.save(path)
        doc.close()
        return path

    reserved_hex_chars = 32768
    sig_xref = doc.get_new_xref()
    doc.update_object(sig_xref,
        '<< /Type /Sig /Filter /Adobe.PPKLite /SubFilter /adbe.pkcs7.detached '
        '/ByteRange [0 9999999999 9999999999 9999999999] '
        '/Contents <' + '0' * reserved_hex_chars + '> '
        '/Reason (Synthetic local test only) >>')
    doc.xref_set_key(added.xref, 'V', f'{sig_xref} 0 R')
    data = doc.tobytes(garbage=0, deflate=False)
    doc.close()
    contents_match = re.search(rb'/Contents\s*<([0-9A-Fa-f]{32768})>', data)
    byte_range_match = re.search(rb'/ByteRange\s*\[\s*0\s+9999999999\s+9999999999\s+9999999999\s*\]', data)
    if not contents_match or not byte_range_match:
        raise AssertionError('Synthetic signature placeholders were not found')
    skip_start = contents_match.start(1) - 1
    skip_end = contents_match.end(1) + 1
    replacement = f'/ByteRange [0 {skip_start} {skip_end} {len(data) - skip_end}]'.encode()
    old_length = byte_range_match.end() - byte_range_match.start()
    if len(replacement) > old_length:
        raise AssertionError('Synthetic ByteRange placeholder too short')
    data = (data[:byte_range_match.start()] + replacement.ljust(old_length) +
            data[byte_range_match.end():])
    if real_cms:
        from datetime import datetime, timedelta, timezone
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives.serialization import pkcs7
        from cryptography.x509.oid import NameOID

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,
                                            'Synthetic Test Signer')])
        now = datetime.now(timezone.utc)
        cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
                .public_key(key.public_key()).serial_number(123456789)
                .not_valid_before(now - timedelta(days=1))
                .not_valid_after(now + timedelta(days=1))
                .sign(key, hashes.SHA256()))
        signed_content = data[:skip_start] + data[skip_end:]
        cms = (pkcs7.PKCS7SignatureBuilder().set_data(signed_content)
               .add_signer(cert, key, hashes.SHA256())
               .sign(serialization.Encoding.DER,
                     [pkcs7.PKCS7Options.DetachedSignature, pkcs7.PKCS7Options.Binary]))
        cms_hex = cms.hex().upper().encode()
    else:
        cms_hex = b'30000000'
    if len(cms_hex) > reserved_hex_chars:
        raise AssertionError('Synthetic signature exceeds reserved buffer')
    data = (data[:contents_match.start(1)] + cms_hex.ljust(reserved_hex_chars, b'0') +
            data[contents_match.end(1):])
    path.write_bytes(data)
    return path
