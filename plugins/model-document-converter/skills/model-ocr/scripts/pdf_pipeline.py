#!/usr/bin/env python3
"""Mechanical PDF preparation, invisible-text editing and evidence-producing QA.

Recognition is deliberately absent: MODEL supplies the approved layer plan.
PDF input is always edited as PDF. PNG renders are never a PDF replacement.
Coordinates in the layer plan are unrotated MuPDF page points (top-left origin).
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import io
import json
import math
import os
import re
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Any

import pymupdf as fitz
from PIL import Image, ImageOps
from pypdf import PdfReader


PLAN_VERSION = "model-ocr-layer-plan-1"
INVENTORY_VERSION = "model-ocr-inventory-1"
REPORT_VERSION = "model-ocr-pdf-qa-1"
DEFAULT_MAX_RENDER_PIXELS = 40_000_000
DEFAULT_MAX_INPUT_PIXELS = 120_000_000
OUTSIDE_TOLERANCE_PT = 2.0
RETAINED_GLYPH_TOLERANCE_PT = 0.05
DEFAULT_FONT = Path(__file__).resolve().parents[1] / "assets" / "DejaVuSans.ttf"


class PipelineError(RuntimeError):
    """A required invariant failed; the candidate must not be published."""


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_text(text: str) -> str:
    """Comparison only: NFC and whitespace; never change signs/case/punctuation."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def _load_plan(plan: dict | str | Path) -> dict:
    try:
        if isinstance(plan, dict):
            # Detach from the caller and reject non-JSON/NaN values.
            return json.loads(json.dumps(plan, ensure_ascii=False, allow_nan=False))
        return json.loads(Path(plan).read_text(encoding="utf-8"),
                          parse_constant=lambda value: (_ for _ in ()).throw(
                              PipelineError(f"Non-finite JSON value: {value}")))
    except (OSError, ValueError, TypeError) as exc:
        raise PipelineError(f"Cannot read layer plan: {exc}") from exc


def _write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                      encoding="utf-8")


def _rect(values: Any, label: str) -> fitz.Rect:
    if (not isinstance(values, (list, tuple)) or len(values) != 4
            or any(isinstance(v, bool) or not isinstance(v, (float, int))
                   or not math.isfinite(v) for v in values)):
        raise PipelineError(f"{label}: expected four finite numeric coordinates")
    r = fitz.Rect(values)
    if r.is_empty or r.is_infinite or r.width <= 0 or r.height <= 0:
        raise PipelineError(f"{label}: bbox must have positive width and height")
    return r


def _numbers(values) -> list[float]:
    return [round(float(v), 7) for v in values]


def _expand(r: fitz.Rect, amount: float) -> fitz.Rect:
    return fitz.Rect(r.x0 - amount, r.y0 - amount, r.x1 + amount, r.y1 + amount)


def _bounds(page: fitz.Page) -> fitz.Rect:
    return fitz.Rect(page.rect) * page.derotation_matrix


def _inside(box: fitz.Rect, bounds: fitz.Rect, tolerance: float = 0.0) -> bool:
    return (box.x0 >= bounds.x0 - tolerance and box.y0 >= bounds.y0 - tolerance
            and box.x1 <= bounds.x1 + tolerance and box.y1 <= bounds.y1 + tolerance)


def dynamic_dpi(width_pt: float, height_pt: float) -> float:
    short = min(width_pt, height_pt)
    if not math.isfinite(short) or short <= 0:
        raise PipelineError("Invalid page size for dynamic DPI")
    return max((1024.0 / short) * 72.0, 192.0)


def _render(page: fitz.Page, *, max_render_pixels: int) -> tuple[fitz.Pixmap, float]:
    dpi = dynamic_dpi(page.rect.width, page.rect.height)
    width = math.ceil(page.rect.width * dpi / 72.0)
    height = math.ceil(page.rect.height * dpi / 72.0)
    if width * height > max_render_pixels:
        raise PipelineError(
            f"Page {page.number + 1}: baseline render requires {width * height} pixels, "
            f"limit is {max_render_pixels}; use reviewed tiles or raise the explicit limit")
    return page.get_pixmap(matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0),
                           colorspace=fitz.csRGB, alpha=False, annots=True), dpi


def _open_pdf(path: str | Path) -> fitz.Document:
    try:
        document = fitz.open(path)
    except Exception as exc:
        raise PipelineError(f"Cannot open PDF: {exc}") from exc
    if not document.is_pdf:
        document.close()
        raise PipelineError("build/qa require the PDF base returned by prepare")
    if document.needs_pass:
        document.close()
        raise PipelineError("Password-protected PDF requires an authorized unlocked input")
    if not document.page_count:
        document.close()
        raise PipelineError("Zero-page PDF is not a complete document")
    return document


def detect_signatures(path: str | Path) -> dict:
    """Structural detection, including malformed *filled* signature candidates.

    Missing/invalid ByteRange is evidence to investigate, never evidence that a
    filled signature does not exist. No cryptographic conclusion is made here.
    """
    candidates = []
    result = {"status": "not_present", "count": 0, "signatures": candidates,
              "candidates": candidates, "issues": [], "empty_fields": 0,
              "cryptographic_validity": "not_checked"}
    try:
        file_size = Path(path).stat().st_size
        reader = PdfReader(str(path), strict=False)
        if reader.is_encrypted:
            return {**result, "status": "unknown", "reason": "encrypted_pdf"}
        root = reader.trailer["/Root"]
        todo = []
        form = root.get("/AcroForm")
        if form:
            todo.extend((ref, "", False) for ref in form.get_object().get("/Fields", []))
        for page in reader.pages:
            todo.extend((ref, "", False) for ref in page.get("/Annots", []))
        perms = root.get("/Perms")
        if perms:
            todo.extend((ref, "", True) for ref in perms.get_object().values())
        seen = set()
        while todo:
            ref, inherited_name, signature_value = todo.pop()
            key = (getattr(ref, "idnum", None), getattr(ref, "generation", None))
            obj = ref.get_object() if hasattr(ref, "get_object") else ref
            identity = key if key[0] is not None else ("direct", id(obj))
            if identity in seen or not hasattr(obj, "get"):
                continue
            seen.add(identity)
            field_name = str(obj.get("/T", inherited_name))
            todo.extend((child, field_name, False) for child in obj.get("/Kids", []))
            value = obj.get("/V")
            if str(obj.get("/FT", "")) == "/Sig":
                resolved = value.get_object() if hasattr(value, "get_object") else value
                if not resolved or type(resolved).__name__ == "NullObject":
                    result["empty_fields"] += 1
                elif hasattr(resolved, "get"):
                    todo.append((value, field_name, True))
                else:
                    candidates.append({"field_name": field_name, "type": "/Sig",
                                       "subfilter": "", "byte_range": None,
                                       "contents_sha256": None, "contents_bytes": 0,
                                       "issues": ["invalid_signature_value"]})
            elif value:
                todo.append((value, field_name, False))
            candidate = (signature_value or str(obj.get("/Type", "")) in ("/Sig", "/DocTimeStamp")
                         or ("/ByteRange" in obj and "/Contents" in obj))
            if not candidate:
                continue
            issues = []
            contents = obj.get("/Contents")
            if isinstance(contents, bytes):
                contents_bytes = bytes(contents)
            elif hasattr(contents, "original_bytes"):
                contents_bytes = contents.original_bytes
            else:
                contents_bytes = b""
                if contents is not None:
                    issues.append("invalid_contents_type")
            if not contents_bytes:
                issues.append("missing_contents")
            elif not any(contents_bytes):
                issues.append("empty_contents_placeholder")
            raw_range = obj.get("/ByteRange")
            byte_range = None
            if raw_range is None:
                issues.append("missing_byte_range")
            elif not isinstance(raw_range, (list, tuple)):
                issues.append("invalid_byte_range_type")
            elif (len(raw_range) < 4 or len(raw_range) % 2):
                issues.append("invalid_byte_range_length")
                if all(isinstance(v, int) and not isinstance(v, bool) for v in raw_range):
                    byte_range = [int(v) for v in raw_range]
            elif not all(isinstance(v, int) and not isinstance(v, bool) for v in raw_range):
                issues.append("invalid_byte_range_values")
            else:
                byte_range = [int(v) for v in raw_range]
                last_end = 0
                for start, length in zip(byte_range[::2], byte_range[1::2]):
                    if start < last_end or start < 0 or length < 0 or start + length > file_size:
                        issues.append("invalid_byte_range_bounds")
                        break
                    last_end = start + length
                if byte_range[0] != 0:
                    issues.append("byte_range_does_not_start_at_zero")
            candidates.append({"field_name": field_name, "type": str(obj.get("/Type", "/Sig")),
                               "subfilter": str(obj.get("/SubFilter", "")),
                               "byte_range": byte_range,
                               "contents_sha256": _sha(contents_bytes) if contents_bytes else None,
                               "contents_bytes": len(contents_bytes), "issues": sorted(set(issues))})
        candidates.sort(key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False))
        result["count"] = len(candidates)
        result["issues"] = sorted({issue for item in candidates for issue in item["issues"]})
        result["status"] = ("malformed" if result["issues"] else
                            "present" if result["count"] else "not_present")
    except Exception as exc:
        result.update(status="unknown", reason=f"presence_detection_failed: {type(exc).__name__}")
        result["count"] = len(candidates)
        result["issues"] = sorted({issue for item in candidates for issue in item["issues"]}
                                  | {"presence_detection_incomplete"})
    return result


def _trace_text(trace: dict) -> str:
    try:
        return "".join(chr(char[0]) for char in trace["chars"])
    except (ValueError, TypeError) as exc:
        raise PipelineError("Text trace has invalid Unicode; manual inspection required") from exc


def _trace_inventory(page: fitz.Page) -> list[dict]:
    rows = []
    for i, trace in enumerate(page.get_texttrace()):
        rows.append({
            "trace_index": i, "text": _trace_text(trace), "type": trace["type"],
            "hidden": trace["type"] == 3, "seqno": trace["seqno"],
            "bbox": _numbers(trace["bbox"]), "direction": _numbers(trace["dir"]),
            "font": trace["font"], "size": trace["size"], "opacity": trace["opacity"],
            "chars": [{"index": j, "text": chr(c[0]), "origin": _numbers(c[2]),
                       "bbox": _numbers(c[3])} for j, c in enumerate(trace["chars"])],
        })
    return rows


def _page_geometry(page: fitz.Page) -> dict:
    return {
        "mediabox": _numbers(page.mediabox), "cropbox": _numbers(page.cropbox),
        "cropbox_position": _numbers(page.cropbox_position), "rotation": page.rotation,
        "display_rect": _numbers(page.rect), "unrotated_rect": _numbers(_bounds(page)),
        "rotation_matrix": _numbers(page.rotation_matrix),
        "derotation_matrix": _numbers(page.derotation_matrix),
        "pdf_transformation_matrix": _numbers(page.transformation_matrix),
    }


def _xref_stream_descriptor(doc: fitz.Document, xref: int) -> dict:
    """No xref in the descriptor: garbage collection may renumber objects."""
    descriptor = {"raw_sha256": _sha(doc.xref_stream_raw(xref) or b""),
                  "decoded_sha256": _sha(doc.xref_stream(xref) or b"")}
    for key in ("Width", "Height", "BitsPerComponent", "Filter", "Decode", "Interpolate",
                "ImageMask", "SMaskInData"):
        kind, value = doc.xref_get_key(xref, key)
        descriptor[key] = value if kind != "null" else None
    # DecodeParms can contain indirect objects; resolve without exposing xref identity.
    for key in ("DecodeParms", "ColorSpace"):
        descriptor[key] = _canonical_pdf_value(doc, doc.xref_get_key(xref, key))
    for key in ("SMask", "Mask"):
        kind, value = doc.xref_get_key(xref, key)
        if kind == "xref":
            target = int(value.split()[0])
            descriptor[key] = _xref_stream_descriptor(doc, target) if doc.xref_is_stream(target) else _canonical_pdf_value(doc, (kind, value))
        else:
            descriptor[key] = value if kind != "null" else None
    return descriptor


def _canonical_pdf_value(doc: fitz.Document, item: tuple[str, str], depth: int = 0):
    kind, value = item
    if kind == "null":
        return None
    if depth > 8:
        raise PipelineError("Image descriptor has unsupported recursive PDF references")
    if kind == "xref":
        xref = int(value.split()[0])
        content = doc.xref_object(xref, compressed=True)
        if doc.xref_is_stream(xref):
            # ICC profiles may be losslessly compressed by the required optimized
            # save. Their decoded content/properties are the colorspace identity;
            # image and mask encoded bytes are checked separately and exactly.
            return {"decoded_stream_sha256": _sha(doc.xref_stream(xref) or b""),
                    "properties": {key: _canonical_pdf_value(doc, doc.xref_get_key(xref, key), depth + 1)
                                   for key in sorted(doc.xref_get_keys(xref))
                                   if key not in ("Length", "Filter", "DecodeParms")}}
        return _canonical_pdf_value(doc, ("resolved", content), depth + 1)
    # Canonicalize references in colorspace arrays/dictionaries recursively.
    def resolve(match):
        return json.dumps(_canonical_pdf_value(doc, ("xref", match.group(0)), depth + 1),
                          sort_keys=True, ensure_ascii=False)
    return re.sub(r"\b\d+\s+\d+\s+R\b", resolve, value)


def image_inventory(doc: fitz.Document) -> list[dict]:
    """Each displayed occurrence, original encoded stream, masks and dimensions."""
    pages = []
    for page in doc:
        resources = []
        decoded_identities = {}
        for item in page.get_images(full=True):
            stream = _xref_stream_descriptor(doc, item[0])
            identity = (item[2], item[3], item[4], stream["decoded_sha256"])
            encoded_identity = json.dumps(stream, sort_keys=True)
            if identity in decoded_identities and decoded_identities[identity] != encoded_identity:
                raise PipelineError("Pixel-identical images have different encodings/masks; per-occurrence stream identity is ambiguous")
            decoded_identities[identity] = encoded_identity
            resources.append({"width": item[2], "height": item[3],
                              "bits_per_component": item[4], "stream": stream})
        resources.sort(key=lambda row: json.dumps(row, sort_keys=True))
        occurrences = []
        for info in page.get_image_info(hashes=True, xrefs=True):
            xref = info.get("xref", 0)
            if not xref:
                raise PipelineError(
                    f"Page {page.number + 1}: inline/unresolvable image stream; "
                    "exact encoded-stream preservation cannot be proved by this helper")
            occurrences.append({
                "bbox": _numbers(info["bbox"]), "transform": _numbers(info["transform"]),
                "width": info["width"], "height": info["height"],
                "bits_per_component": info["bpc"], "colorspace": info["colorspace"],
                "pixel_digest": info["digest"].hex(),
                "stream": _xref_stream_descriptor(doc, xref),
            })
        pages.append({"page": page.number + 1, "resources": resources, "occurrences": occurrences})
    return pages


def _stable(value):
    if isinstance(value, float):
        return round(value, 5)
    if isinstance(value, (fitz.Rect, fitz.Point, fitz.Quad, fitz.Matrix)):
        return [_stable(x) for x in value]
    if isinstance(value, bytes):
        return {"sha256": _sha(value)}
    if isinstance(value, (list, tuple)):
        return [_stable(x) for x in value]
    if isinstance(value, dict):
        return {str(k): _stable(v) for k, v in value.items() if k != "xref"}
    return value


def _annotation_inventory(doc: fitz.Document) -> list[dict]:
    rows = []
    for page in doc:
        annots = []
        for annot in page.annots() or []:
            annots.append(_stable({"type": annot.type, "rect": annot.rect, "info": annot.info,
                                   "flags": annot.flags, "colors": annot.colors,
                                   "opacity": annot.opacity, "border": annot.border,
                                   "vertices": annot.vertices}))
        widgets = [_stable({"name": widget.field_name, "type": widget.field_type,
                            "value": widget.field_value, "rect": widget.rect,
                            "flags": widget.field_flags}) for widget in page.widgets() or []]
        rows.append({"page": page.number + 1, "annotations": annots,
                     "widgets": widgets, "links": _stable(page.get_links())})
    return rows


def _visible_text_inventory(doc: fitz.Document) -> list[list]:
    return [[_stable({"text": _trace_text(t), "type": t["type"], "opacity": t["opacity"],
                       "bbox": t["bbox"], "direction": t["dir"],
                       "origins": [c[2] for c in t["chars"]]})
             for t in page.get_texttrace() if t["type"] != 3] for page in doc]


def _actual_source_kind(path: Path) -> str:
    """Inspect bytes; filename suffix and caller-supplied kind are not evidence."""
    try:
        with fitz.open(stream=path.read_bytes()) as probe:
            if probe.is_pdf:
                return "pdf"
    except Exception:
        pass
    try:
        with Image.open(path) as image:
            if image.format:
                return "image"
    except Exception as exc:
        raise PipelineError(f"Input is neither a readable PDF nor a supported image: {exc}") from exc
    raise PipelineError("Input type cannot be established from its actual bytes")


def _image_source_frames(input_path: Path, *, max_input_pixels: int) -> list[dict]:
    """Decode only explicitly supported sample representations, before writing.

    In particular Pillow's RGB conversion is NOT a safe 16-bit/float conversion.
    Source-container bit depth is inspected as well as Pillow mode because a
    16-bit RGB PNG may already be presented by Pillow as 8-bit RGB.
    """
    original_bytes = input_path.read_bytes()
    try:
        image = Image.open(input_path)
    except Exception as exc:
        raise PipelineError(f"Unsupported or damaged image input: {exc}") from exc
    output = []
    try:
        source_format = image.format
        if source_format not in {"PNG", "JPEG", "MPO", "TIFF", "BMP", "GIF", "WEBP", "PPM", "TGA", "PCX"}:
            raise PipelineError(f"Unsupported image format {source_format}; lossless sample preservation is not established")
        frames = getattr(image, "n_frames", 1)
        if frames > 4096:
            raise PipelineError("Image has too many frames; no silent frame truncation is permitted")
        if frames > 1 and source_format not in ("TIFF", "MPO"):
            raise PipelineError("Animated/multiframe image is ambiguous; provide ordered still pages")
        if source_format == "PNG" and len(original_bytes) > 24 and original_bytes[24] > 8:
            raise PipelineError("Unsupported high-bit image (PNG >8 bits per sample); no clipping or conversion was performed")
        if source_format == "PPM":
            # P6 RGB can be 16-bit despite Pillow exposing it as mode RGB.
            # Parse only the header tokens, leaving binary sample bytes alone.
            tokens, position = [], 0
            while len(tokens) < 4 and position < min(len(original_bytes), 65536):
                if original_bytes[position:position + 1].isspace():
                    position += 1
                elif original_bytes[position:position + 1] == b"#":
                    end = original_bytes.find(b"\n", position)
                    if end < 0:
                        break
                    position = end + 1
                else:
                    match = re.match(rb"[^\s#]+", original_bytes[position:])
                    if not match:
                        break
                    tokens.append(match.group())
                    position += len(match.group())
                    if len(tokens) == 3 and tokens[0] in (b"P1", b"P4"):
                        break
            if (not tokens or tokens[0] not in (b"P1", b"P2", b"P3", b"P4", b"P5", b"P6")
                    or (tokens[0] not in (b"P1", b"P4") and
                        (len(tokens) != 4 or not tokens[3].isdigit()))):
                raise PipelineError("Unsupported portable image header; sample depth cannot be established")
            if len(tokens) == 4 and int(tokens[3]) > 255:
                raise PipelineError("Unsupported high-bit portable image; no sample scaling or clipping was performed")
        for number in range(frames):
            image.seek(number)
            if image.width * image.height > max_input_pixels:
                raise PipelineError(f"Image frame {number + 1} exceeds the explicit input pixel limit")
            bits = image.tag_v2.get(258, ()) if source_format == "TIFF" else ()
            bits = (bits,) if isinstance(bits, int) else tuple(bits)
            jpeg_bits = getattr(image, "bits", 8) if source_format in ("JPEG", "MPO") else 8
            if image.mode.startswith("I") or image.mode == "F" or any(bit > 8 for bit in bits) or jpeg_bits > 8:
                raise PipelineError(f"Unsupported high-bit/float image frame {number + 1} ({image.mode}); "
                                    "no clipping or conversion was performed")
            if image.mode not in ("1", "L", "LA", "P", "PA", "RGB", "RGBA", "CMYK"):
                raise PipelineError(f"Unsupported image sample mode {image.mode}; original samples were not converted")
            orientation = image.getexif().get(274, 1)
            if type(orientation) is not int or orientation not in range(1, 9):
                raise PipelineError("Unsupported EXIF orientation; explicit source interpretation is required")
            original_size, original_mode = list(image.size), image.mode
            frame = ImageOps.exif_transpose(image.copy())
            width, height = frame.size
            if frames == 1 and source_format in ("JPEG", "PNG") and orientation == 1:
                stream, embedding = original_bytes, "original_encoded_image"
            else:
                if frame.mode == "CMYK":
                    raise PipelineError("CMYK orientation/multiframe conversion is unsupported; no RGB conversion was performed")
                if frame.mode in ("P", "PA"):
                    frame = frame.convert("RGBA" if frame.mode == "PA" or "transparency" in frame.info else "RGB")
                elif frame.mode == "1":
                    frame = frame.convert("L")
                buffer = io.BytesIO()
                frame.save(buffer, format="PNG")
                stream, embedding = buffer.getvalue(), "lossless_original_resolution_pixels"
            output.append({"stream": stream, "page": number + 1,
                           "source_format": source_format, "source_mode": original_mode,
                           "source_bits_per_sample": list(bits), "original_pixels": original_size,
                           "oriented_pixels": [width, height], "exif_orientation": orientation,
                           "embedding": embedding})
    except PipelineError:
        raise
    except Exception as exc:
        raise PipelineError(f"Cannot decode all original image frames safely: {type(exc).__name__}: {exc}") from exc
    finally:
        image.close()
    return output


def _decoded_image_identity(doc: fitz.Document, xref: int) -> dict:
    """Decoded samples, colorspace, mask and interpretation, excluding encoding."""
    descriptor = _xref_stream_descriptor(doc, xref)
    def without_compression(value):
        if isinstance(value, dict):
            return {key: without_compression(item) for key, item in value.items()
                    if key not in ("raw_sha256", "Filter", "DecodeParms")}
        if isinstance(value, list):
            return [without_compression(item) for item in value]
        return value
    return without_compression(descriptor)


def verify_source_base(original_path: str | Path, base_pdf: str | Path,
                       expected_kind: str | None = None, inventory: dict | str | Path | None = None,
                       *, max_input_pixels: int = DEFAULT_MAX_INPUT_PIXELS,
                       max_render_pixels: int = DEFAULT_MAX_RENDER_PIXELS) -> dict:
    """Re-establish original -> base binding from actual bytes and image pixels.

    A self-authored inventory is only an extra consistency check. It cannot prove
    this relationship. Call this on original/raw bytes at BOTH stage and seal.
    """
    original, base = Path(original_path).resolve(), Path(base_pdf).resolve()
    if not original.is_file() or not base.is_file():
        raise PipelineError("Original and PDF base must both be existing files")
    actual_kind = _actual_source_kind(original)
    if expected_kind is not None and expected_kind != actual_kind:
        raise PipelineError(f"Claimed source kind {expected_kind!r} disagrees with actual {actual_kind} bytes")
    original_hash, base_hash = sha256_file(original), sha256_file(base)
    if actual_kind == "pdf" and original_hash != base_hash:
        raise PipelineError("PDF base must be byte-identical to the actual original PDF")
    frames = (_image_source_frames(original, max_input_pixels=max_input_pixels)
              if actual_kind == "image" else [])
    frame_checks, geometry = [], []
    with _open_pdf(base) as document:
        if actual_kind == "image" and document.page_count != len(frames):
            raise PipelineError("Image frame count does not match the actual PDF base page count")
        assumed_dpi = None
        for page in document:
            geometry.append({"page": page.number + 1, **_page_geometry(page)})
            if actual_kind == "pdf":
                continue
            frame = frames[page.number]
            width, height = frame["oriented_pixels"]
            if (page.rotation != 0 or any(abs(v) > 0.01 for v in (page.mediabox.x0, page.mediabox.y0,
                                                               page.cropbox.x0, page.cropbox.y0))
                    or any(abs(a - b) > 0.01 for a, b in zip(page.mediabox, page.cropbox))):
                raise PipelineError("Image base has unexpected crop, rotation or page origin")
            dpi_x, dpi_y = width * 72.0 / page.rect.width, height * 72.0 / page.rect.height
            if abs(dpi_x - dpi_y) > 0.01 or (assumed_dpi is not None and abs(dpi_x - assumed_dpi) > 0.01):
                raise PipelineError("Image base changes source aspect ratio or uses inconsistent frame scaling")
            assumed_dpi = dpi_x
            if (page.get_texttrace() or page.get_drawings() or list(page.annots() or [])
                    or list(page.widgets() or []) or page.get_links()):
                raise PipelineError("Prepared image base contains foreign text, graphics, annotations or widgets")
            resources = page.get_images(full=True)
            occurrences = page.get_image_info(hashes=True, xrefs=True)
            if len(resources) != 1 or len(occurrences) != 1 or not occurrences[0].get("xref"):
                raise PipelineError("Each image frame must correspond to exactly one actual base image occurrence")
            actual_image = occurrences[0]
            if [actual_image["width"], actual_image["height"]] != [width, height]:
                raise PipelineError("Image base resampled or substituted original pixel dimensions")
            with fitz.open() as reference:
                reference_page = reference.new_page(width=page.rect.width, height=page.rect.height)
                reference_page.insert_image(reference_page.rect, stream=frame["stream"])
                # Reopen both sides as PDF images. An in-memory source PNG may
                # retain premultiplied-alpha caches whose rounding differs by one
                # channel value from the same serialized, decoded PDF mask.
                reference_bytes = reference.tobytes(garbage=4, deflate=True)
            with fitz.open(stream=reference_bytes) as reference:
                reference_page = reference[0]
                reference_image = reference_page.get_image_info(hashes=True, xrefs=True)[0]
                reference_xref = reference_image["xref"]
                if (_decoded_image_identity(document, actual_image["xref"])
                        != _decoded_image_identity(reference, reference_xref)):
                    raise PipelineError("Image base pixels, mask or color interpretation do not match the actual original frame")
                for key in ("bbox", "transform"):
                    if any(abs(a - b) > 0.01 for a, b in zip(actual_image[key], reference_image[key])):
                        raise PipelineError("Image base placement does not match the original full frame")
                if (frame["source_format"] == "JPEG" and frame["exif_orientation"] == 1
                        and document.xref_stream_raw(actual_image["xref"]) != frame["stream"]):
                    raise PipelineError("Original JPEG compressed bytes were changed in the image base")
                actual_pixels, _ = _render(page, max_render_pixels=max_render_pixels)
                reference_pixels, _ = _render(reference_page, max_render_pixels=max_render_pixels)
                if (actual_pixels.width, actual_pixels.height, actual_pixels.samples) != (
                        reference_pixels.width, reference_pixels.height, reference_pixels.samples):
                    raise PipelineError("Image base rendering differs from the actual original frame on a white background")
                frame_checks.append({"page": page.number + 1,
                                     **{key: value for key, value in frame.items() if key != "stream"},
                                     "assumed_image_dpi": dpi_x, "pixels_and_mask_equal": True,
                                     "full_frame_placement_equal": True,
                                     "rendered_rgb_sha256": _sha(actual_pixels.samples)})
    if inventory is not None:
        observed = _load_plan(inventory)
        if (observed.get("schema_version") != INVENTORY_VERSION
                or observed.get("source_kind") != actual_kind
                or observed.get("input_sha256") != original_hash
                or observed.get("original_input_sha256") != original_hash
                or observed.get("source_sha256") != base_hash
                or observed.get("page_count") != len(geometry)):
            raise PipelineError("Preparation inventory disagrees with actual original/base type, hashes or page count")
        recorded_pages = observed.get("pages")
        if not isinstance(recorded_pages, list) or len(recorded_pages) != len(geometry):
            raise PipelineError("Preparation inventory does not contain every actual page")
        for recorded, actual in zip(recorded_pages, geometry):
            if any(recorded.get(key) != value for key, value in actual.items()):
                raise PipelineError("Preparation inventory page geometry disagrees with actual PDF base")
        if actual_kind == "image":
            for recorded, actual in zip(recorded_pages, frame_checks):
                for key in ("original_pixels", "oriented_pixels", "exif_orientation"):
                    if recorded.get(key) != actual[key]:
                        raise PipelineError("Preparation inventory disagrees with actual original image frames")
    if sha256_file(original) != original_hash or sha256_file(base) != base_hash:
        raise PipelineError("Original or base bytes changed during binding verification")
    return {"ok": True, "actual_kind": actual_kind, "source_kind": actual_kind,
            "original_filename": original.name, "input_sha256": original_hash,
            "original_input_sha256": original_hash, "source_sha256": base_hash,
            "binding": "byte_identical_pdf" if actual_kind == "pdf" else "verified_image_pixels",
            "page_count": len(geometry), "pages": geometry, "frames": frame_checks,
            "inventory_checked": inventory is not None}


def _image_base(input_path: Path, work_dir: Path, *, image_dpi: float,
                max_input_pixels: int, max_render_pixels: int) -> tuple[Path, list[dict]]:
    if not math.isfinite(image_dpi) or image_dpi <= 0:
        raise PipelineError("image_dpi must be positive")
    base = work_dir / "image-base.pdf"
    if base.exists():
        raise PipelineError(f"Refusing to overwrite prepared PDF: {base}")
    frames = _image_source_frames(input_path, max_input_pixels=max_input_pixels)
    metadata = []
    # Preflight every frame, including high-bit/float rejection, before any PDF or
    # render is written. A later bad frame cannot leave a misleading partial base.
    with fitz.open() as document:
        for frame in frames:
            width, height = frame["oriented_pixels"]
            scale = max(1.0, 1536.0 / min(width, height))
            render_size = (math.ceil(width * scale), math.ceil(height * scale))
            if render_size[0] * render_size[1] > max_render_pixels:
                raise PipelineError("Working image upscale exceeds pixel limit; use reviewed tiles")
            page = document.new_page(width=width * 72.0 / image_dpi,
                                     height=height * 72.0 / image_dpi)
            page.insert_image(page.rect, stream=frame["stream"])
            metadata.append({key: value for key, value in frame.items() if key != "stream"})
            metadata[-1].update(assumed_image_dpi=image_dpi, working_upscale_only=scale)
        document.save(base, garbage=4, deflate=True)
    try:
        verify_source_base(input_path, base, "image", max_input_pixels=max_input_pixels,
                           max_render_pixels=max_render_pixels)
        with _open_pdf(base) as document:
            for page, info in zip(document, metadata):
                scale = image_dpi * info["working_upscale_only"] / 72.0
                pixels = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB,
                                         alpha=False, annots=True)
                if pixels.width * pixels.height > max_render_pixels:
                    raise PipelineError("Actual working render exceeds the explicit pixel limit")
                render_path = work_dir / "renders" / f"page-{page.number + 1:05d}.png"
                pixels.save(render_path)
                info.update(render=str(render_path.resolve()), render_pixels=[pixels.width, pixels.height],
                            render_dpi=image_dpi * info["working_upscale_only"],
                            preview_source="prepared_pdf_rgb_white_background")
    except Exception:
        base.unlink(missing_ok=True)
        for info in metadata:
            if "render" in info:
                Path(info["render"]).unlink(missing_ok=True)
        raise
    return base, metadata


def prepare(input_path: str | Path, work_dir: str | Path, *,
            max_render_pixels: int = DEFAULT_MAX_RENDER_PIXELS,
            max_input_pixels: int = DEFAULT_MAX_INPUT_PIXELS,
            image_dpi: float = 300.0) -> dict:
    source = Path(input_path).resolve()
    work = Path(work_dir).resolve()
    if not source.is_file():
        raise PipelineError(f"Input file does not exist: {source}")
    if (work / "inventory.json").exists():
        raise PipelineError("Preparation directory already has an inventory; use a new directory")
    if (work / "renders").is_dir() and any((work / "renders").iterdir()):
        raise PipelineError("Render directory is not empty; refusing to overwrite existing/source files")
    work.mkdir(parents=True, exist_ok=True)
    (work / "renders").mkdir(exist_ok=True)
    original_hash = sha256_file(source)
    is_pdf = _actual_source_kind(source) == "pdf"
    if is_pdf:
        base, input_images = source, []
        signature_detection = detect_signatures(source)
    else:
        base, input_images = _image_base(source, work, image_dpi=image_dpi,
                                         max_input_pixels=max_input_pixels,
                                         max_render_pixels=max_render_pixels)
        signature_detection = {"status": "not_applicable", "count": 0,
                               "signatures": [], "candidates": [], "issues": [],
                               "empty_fields": 0, "cryptographic_validity": "not_checked"}
    with _open_pdf(base) as doc:
        images = image_inventory(doc)
        pages = []
        text_flags = fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES
        for page in doc:
            if is_pdf:
                pixmap, dpi = _render(page, max_render_pixels=max_render_pixels)
                render_path = work / "renders" / f"page-{page.number + 1:05d}.png"
                pixmap.save(render_path)
                render_info = {"render": str(render_path), "render_dpi": dpi,
                               "render_pixels": [pixmap.width, pixmap.height]}
            else:
                render_info = input_images[page.number]
            pages.append({"page": page.number + 1, **_page_geometry(page), **render_info,
                          "text": page.get_text("text", sort=True),
                          "native_dict": page.get_text("dict", flags=text_flags),
                          "native_words": page.get_text("words"),
                          "texttrace": _trace_inventory(page),
                          "images": images[page.number]})
        inventory = {"schema_version": INVENTORY_VERSION,
                     "source_kind": "pdf" if is_pdf else "image",
                     "original_filename": source.name, "original_input": str(source),
                     "input_sha256": original_hash, "original_input_sha256": original_hash,
                     "base_pdf": str(base.resolve()), "source_sha256": sha256_file(base),
                     "page_count": doc.page_count, "coordinate_system": "unrotated_mupdf_points",
                     "signature_detection": signature_detection, "pages": pages}
    if sha256_file(source) != original_hash:
        raise PipelineError("Original input changed during preparation")
    inventory["source_base_binding"] = verify_source_base(
        source, base, inventory["source_kind"], inventory,
        max_input_pixels=max_input_pixels, max_render_pixels=max_render_pixels)
    _write_json(work / "inventory.json", inventory)
    return inventory


def _check_plan(doc: fitz.Document, source_path: Path, plan: dict) -> None:
    if not isinstance(plan, dict) or plan.get("schema_version") != PLAN_VERSION:
        raise PipelineError(f"Layer plan must use schema_version={PLAN_VERSION}")
    if plan.get("source_sha256") != sha256_file(source_path):
        raise PipelineError("Plan source_sha256 does not match the actual PDF base")
    if plan.get("review_complete") is not True or plan.get("unresolved") != []:
        raise PipelineError("MODEL/user review is incomplete; unresolved readings block finalization")
    pages = plan.get("pages")
    if not isinstance(pages, list) or [p.get("page") for p in pages if isinstance(p, dict)] != list(range(1, doc.page_count + 1)):
        raise PipelineError("Plan must contain every source page exactly once, in order")
    for page, spec in zip(doc, pages):
        if type(spec.get("page")) is not int:
            raise PipelineError("Page numbers must be integers, not booleans")
        if spec.get("mode") not in ("keep", "add", "patch", "rebuild_hidden"):
            raise PipelineError(f"Page {page.number + 1}: unknown layer mode")
        if not isinstance(spec.get("expected_text"), str):
            raise PipelineError("Every page requires its complete approved expected_text")
        lines = spec.get("lines", [])
        if not isinstance(lines, list):
            raise PipelineError("lines must be an array")
        if spec["mode"] == "keep" and lines:
            raise PipelineError("keep pages cannot contain layer edits")
        if spec["mode"] != "keep" and not lines:
            raise PipelineError("A modifying mode requires at least one approved line/word")
        if spec["mode"] == "rebuild_hidden" and (
                spec.get("geometry_override_reviewed") is not True
                or not isinstance(spec.get("rebuild_reason"), str)
                or not spec["rebuild_reason"].strip()):
            raise PipelineError("Full hidden-layer rebuild requires explicit geometry review and reason")
        for line in lines:
            if not isinstance(line, dict) or not isinstance(line.get("text"), str) or not line["text"].strip():
                raise PipelineError("Each line needs non-empty approved text")
            if any(c in line["text"] for c in "\r\n\t\x00\x0b\x0c"):
                raise PipelineError("Place individual lines/words; multiline paragraph insertions are forbidden")
            if line.get("geometry_verified") is not True:
                raise PipelineError("Each insertion needs MODEL-verified line/word geometry")
            if spec["mode"] == "patch" and not isinstance(line.get("source"), dict):
                raise PipelineError("patch requires an exact original hidden-text selector")
            if spec["mode"] == "patch" and any(char.isspace() for char in line["text"]):
                raise PipelineError("Patch replacement must be one complete word/token; split a multiword repair into original word geometries")
            if spec["mode"] != "patch":
                r = _rect(line.get("bbox"), "new line bbox")
                if not _inside(r, _bounds(page), 0.01):
                    raise PipelineError("New line bbox lies outside the actual cropped page")
        checks = spec.get("search_checks", [])
        if not isinstance(checks, list):
            raise PipelineError("search_checks must be an array")
        for check in checks:
            if not isinstance(check.get("text"), str) or not check["text"].strip():
                raise PipelineError("A search check requires non-empty text")
            _rect(check.get("bbox"), "search check bbox")


def _source_selection(traces: list[dict], ref: dict) -> tuple[list[tuple], fitz.Rect, int]:
    for name in ("trace_index", "char_start", "char_end"):
        if type(ref.get(name)) is not int:
            raise PipelineError(f"Hidden source selector needs integer {name}")
    ti, start, end = ref["trace_index"], ref["char_start"], ref["char_end"]
    if ti < 0 or ti >= len(traces):
        raise PipelineError("Stale trace_index in hidden source selector")
    trace = traces[ti]
    if trace["type"] != 3:
        raise PipelineError("Refusing to remove visible/source text: selector is not render-mode-3 text")
    if trace.get("wmode", 0) != 0 or any(abs(a - b) > 0.001 for a, b in zip(trace["dir"], (1, 0))):
        raise PipelineError("Angled/vertical hidden text requires a reviewed specialized editor")
    if not 0 <= start < end <= len(trace["chars"]):
        raise PipelineError("Invalid hidden source character range")
    # An interior glyph repaired in a separate text run can look correct to sorted
    # extraction yet fail normal PDF search for the whole token. Replace the full
    # source token so ordinary viewers retain searchable words.
    if ((start > 0 and not chr(trace["chars"][start - 1][0]).isspace())
            or (end < len(trace["chars"]) and not chr(trace["chars"][end][0]).isspace())):
        raise PipelineError("Partial-word patch is unsafe for PDF search; select the complete original word/token")
    chars = list(trace["chars"][start:end])
    original = "".join(chr(c[0]) for c in chars)
    if ref.get("original_text") != original:
        raise PipelineError("original_text does not exactly match the selected original PDF characters")
    if any(char.isspace() for char in original):
        raise PipelineError("Multiword line patch would reflow original word geometry; select each complete changed original word/token separately")
    if max(c[2][1] for c in chars) - min(c[2][1] for c in chars) > 0.25:
        raise PipelineError("A replacement selector crosses text lines; split into original lines/words")
    bbox = fitz.Rect(chars[0][3])
    for char in chars[1:]:
        bbox |= fitz.Rect(char[3])
    if bbox.is_empty or bbox.is_infinite:
        raise PipelineError("Source geometry is unusable; explicit reviewed rebuild is required")
    return chars, bbox, ti


def _planned_edits(page: fitz.Page, spec: dict) -> tuple[list[dict], set[tuple[int, int]], list[fitz.Rect]]:
    traces = page.get_texttrace()
    mode = spec["mode"]
    selected: set[tuple[int, int]] = set()
    selection_groups: list[set[tuple[int, int]]] = []
    edits = []
    if mode == "keep":
        return edits, selected, []
    if mode == "rebuild_hidden":
        for ti, trace in enumerate(traces):
            if trace["type"] == 3:
                selected.update((ti, ci) for ci in range(len(trace["chars"])))
        if not selected:
            raise PipelineError("rebuild_hidden found no confirmed hidden layer")
    for line in spec.get("lines", []):
        if mode == "patch":
            ref = line["source"]
            _, bbox, ti = _source_selection(traces, ref)
            indices = {(ti, i) for i in range(ref["char_start"], ref["char_end"])}
            if selected & indices:
                raise PipelineError("Two replacements select the same original character")
            selected |= indices
            selection_groups.append(indices)
            if "bbox" in line and any(abs(a - b) > 0.05 for a, b in zip(_rect(line["bbox"], "patch bbox"), bbox)):
                raise PipelineError("patch cannot relocate text: bbox must equal original selected geometry")
        else:
            bbox = _rect(line["bbox"], "line bbox")
        if not _inside(bbox, _bounds(page), 0.01):
            raise PipelineError("Insertion geometry is outside page; use reviewed replacement geometry")
        edit = {"text": line["text"], "bbox": _numbers(bbox)}
        if mode == "patch":
            edit["source_font_size"] = float(traces[line["source"]["trace_index"]]["size"])
        edits.append(edit)
    if mode == "patch":
        # A PDF word can span several source text runs. A selector ending at a
        # trace boundary is not automatically a complete word in that case.
        for word in page.get_text("words", clip=fitz.INFINITE_RECT()):
            word_box = fitz.Rect(word[:4])
            members = set()
            for ti, trace in enumerate(traces):
                if trace["type"] != 3:
                    continue
                for ci, char in enumerate(trace["chars"]):
                    r = fitz.Rect(char[3])
                    center = fitz.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)
                    if not chr(char[0]).isspace() and center in word_box:
                        members.add((ti, ci))
            if selected & members and not any(members <= group for group in selection_groups):
                raise PipelineError("Source word crosses selected text-run boundaries; use a reviewed whole-word/line operation")
    # A mixed page may have good native text and an image-only region. Add only in
    # verified empty regions; neither native text nor existing OCR may be doubled.
    if mode in ("add", "rebuild_hidden"):
        retained = [fitz.Rect(c[3]) for ti, trace in enumerate(traces)
                    for ci, c in enumerate(trace["chars"]) if (ti, ci) not in selected]
        for i, edit in enumerate(edits):
            box = fitz.Rect(edit["bbox"])
            if any(box.intersects(old) for old in retained):
                raise PipelineError("New OCR geometry overlaps retained source text")
            if any(box.intersects(fitz.Rect(other["bbox"])) for other in edits[:i]):
                raise PipelineError("New OCR line/word geometries overlap each other")
    # Individual glyph interiors avoid sweeping away adjacent words or line content.
    redactions = []
    for ti, ci in sorted(selected):
        box = fitz.Rect(traces[ti]["chars"][ci][3])
        if box.is_empty or box.is_infinite:
            raise PipelineError("Selected hidden glyph has invalid geometry")
        epsilon = min(0.05, box.width / 10, box.height / 10)
        redactions.append(fitz.Rect(box.x0 + epsilon, box.y0 + epsilon,
                                    box.x1 - epsilon, box.y1 - epsilon))
    # Any overlap with unselected text is unsafe, even if it is also hidden.
    for ti, trace in enumerate(traces):
        for ci, char in enumerate(trace["chars"]):
            if (ti, ci) in selected:
                continue
            box = fitz.Rect(char[3])
            if any(box.intersects(redaction) for redaction in redactions):
                raise PipelineError("Hidden patch would overlap unselected source text")
    for annot in page.annots() or []:
        if annot.type[0] == fitz.PDF_ANNOT_REDACT:
            continue  # preserved by temporary detachment, not applied
        if any(annot.rect.intersects(r) for r in redactions):
            raise PipelineError("Hidden patch overlaps an original annotation")
    for widget in page.widgets() or []:
        if any(widget.rect.intersects(r) for r in redactions):
            raise PipelineError("Hidden patch overlaps an original form widget")
    for link in page.get_links():
        if any(fitz.Rect(link["from"]).intersects(r) for r in redactions):
            raise PipelineError("Hidden patch overlaps a source link; redaction would remove it")
    return edits, selected, redactions


def _remove_selected_hidden(page: fitz.Page, rectangles: list[fitz.Rect]) -> None:
    if not rectangles:
        return
    doc = page.parent
    original_annots = doc.xref_get_key(page.xref, "Annots")
    redact_xrefs = {a.xref for a in page.annots() or [] if a.type[0] == fitz.PDF_ANNOT_REDACT}
    suspended = False
    if redact_xrefs:
        kind, value = original_annots
        array = doc.xref_object(int(value.split()[0]), compressed=True) if kind == "xref" else value
        if not re.fullmatch(r"\s*\[\s*(?:\d+\s+\d+\s+R\s*)*\]\s*", array):
            raise PipelineError("Unsupported annotation array: cannot safely preserve existing redactions")
        references = re.findall(r"\d+\s+\d+\s+R", array)
        keep = [ref for ref in references if int(ref.split()[0]) not in redact_xrefs]
        doc.xref_set_key(page.xref, "Annots", "[" + " ".join(keep) + "]")
        page = doc.reload_page(page)
        suspended = True
    try:
        for rectangle in rectangles:
            page.add_redact_annot(rectangle, fill=False, cross_out=False)
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                              graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                              text=fitz.PDF_REDACT_TEXT_REMOVE)
    finally:
        if suspended:
            # Original objects never left the document; restore before any save/GC.
            doc.xref_set_key(page.xref, "Annots", original_annots[1])


def _insert_line(page: fitz.Page, line: dict, font: fitz.Font, font_path: Path, font_name: str) -> dict:
    text = line["text"]
    box = fitz.Rect(line["bbox"])
    missing = sorted({ch for ch in text if not ch.isspace() and not font.has_glyph(ord(ch))})
    if missing:
        raise PipelineError(f"Bundled font lacks required glyphs: {''.join(missing)!r}; supply a suitable font")
    height = font.ascender - font.descender
    if height <= 0:
        raise PipelineError("Font metrics are invalid")
    fontsize = box.height / height
    if not 2.0 <= fontsize <= 72.0:
        raise PipelineError("Line requires an implausible font size; verify/split source geometry or supply a suitable font")
    if "source_font_size" in line:
        source_size = line["source_font_size"]
        if source_size <= 0 or not 0.6 <= fontsize / source_size <= 1.6:
            raise PipelineError("Replacement font size differs excessively from source line/word geometry")
    # Horizontal fitting is per single visually verified line/word, never a paragraph.
    text_width = font.text_length(text, fontsize=fontsize)
    if text_width <= 0:
        raise PipelineError("Cannot position a zero-width line")
    scale_x = box.width / text_width
    if not 0.5 <= scale_x <= 2.0:
        raise PipelineError("Line geometry is implausible; verify/split the line or word before placement")
    origin = fitz.Point(box.x0, box.y0 + fontsize * font.ascender)
    result = page.insert_text(origin, text, fontsize=fontsize, fontname=font_name,
                              fontfile=str(font_path), render_mode=3, overlay=True,
                              morph=(origin, fitz.Matrix(scale_x, 1.0)))
    if result != 1:
        raise PipelineError(f"Single-line insertion failed or clipped (result={result!r})")
    return {"text": text, "bbox": _numbers(box), "font_size": fontsize,
            "horizontal_scale": scale_x, "render_mode": 3}


def _image_stream_pairs(source: fitz.Document, candidate: fitz.Document):
    pairs = []
    if source.page_count != candidate.page_count:
        raise PipelineError("Cannot restore image streams after page-count change")
    for sp, cp in zip(source, candidate):
        original, current = sp.get_images(full=True), cp.get_images(full=True)
        if len(original) != len(current):
            raise PipelineError("PDF operation changed image resources")
        available = list(current)
        for before in original:
            decoded = source.xref_stream(before[0])
            matches = [item for item in available if before[2:7] == item[2:7]
                       and candidate.xref_stream(item[0]) == decoded]
            same_encoded = [item for item in matches
                            if candidate.xref_stream_raw(item[0]) == source.xref_stream_raw(before[0])]
            if same_encoded:
                after = same_encoded[0]
            elif len(matches) == 1:
                after = matches[0]
            else:
                raise PipelineError("Image resources cannot be matched unambiguously by dimensions and content")
            available.remove(after)
            pairs.append((before[0], after[0]))
            if bool(before[1]) != bool(after[1]):
                raise PipelineError("Image soft mask was lost or added")
            if before[1]:
                pairs.append((before[1], after[1]))
    return pairs


def _restore_original_image_streams(source_path: Path, candidate_path: Path) -> dict:
    """deflate=True compresses unfiltered images even with deflate_images=False.

    Restore only byte-changed, decoded-identical streams and their original filter
    properties, then save without recompressing them. No image pixels are regenerated.
    """
    restored, seen = [], {}
    with _open_pdf(source_path) as source, _open_pdf(candidate_path) as candidate:
        for original_xref, target_xref in _image_stream_pairs(source, candidate):
            original_raw = source.xref_stream_raw(original_xref) or b""
            key = _sha(original_raw)
            if target_xref in seen and seen[target_xref] != key:
                raise PipelineError("Optimizer merged distinct original image encodings; cannot restore unambiguously")
            seen[target_xref] = key
            if candidate.xref_stream_raw(target_xref) == original_raw:
                continue
            if source.xref_stream(original_xref) != candidate.xref_stream(target_xref):
                raise PipelineError("Image decoded stream changed; refusing to recreate source pixels")
            properties = {name: source.xref_get_key(original_xref, name)
                          for name in ("Filter", "DecodeParms")}
            if any(kind == "xref" or re.search(r"\b\d+\s+\d+\s+R\b", value)
                   for kind, value in properties.values()):
                raise PipelineError("Changed image filter has indirect parameters; safe restoration unavailable")
            candidate.update_stream(target_xref, original_raw, compress=False)
            for name, (kind, value) in properties.items():
                candidate.xref_set_key(target_xref, name, "null" if kind == "null" else value)
            restored.append({"raw_sha256": key, "bytes": len(original_raw)})
        if restored:
            restored_path = candidate_path.with_suffix(".restored.pdf")
            try:
                candidate.save(restored_path, garbage=4, deflate=False,
                               deflate_images=False, deflate_fonts=False)
            except Exception:
                restored_path.unlink(missing_ok=True)
                raise
    if restored:
        os.replace(restored_path, candidate_path)
    return {"restored_streams": len(restored), "streams": restored,
            "final_save_deflate": not bool(restored)}


def _outside_characters(page: fitz.Page, tolerance: float = OUTSIDE_TOLERANCE_PT) -> dict:
    raw = page.get_text("rawdict", clip=fitz.INFINITE_RECT(),
                        flags=fitz.TEXTFLAGS_RAWDICT & ~fitz.TEXT_PRESERVE_IMAGES)
    outside, count = [], 0
    for block in raw.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                for char in span.get("chars", []):
                    count += 1
                    displayed = fitz.Rect(char["bbox"]) * page.rotation_matrix
                    if not _inside(displayed, page.rect, tolerance):
                        outside.append({"text": char["c"], "display_bbox": _numbers(displayed)})
    return {"total": count, "outside": len(outside), "tolerance_pt": tolerance,
            "examples": outside[:20]}


def _font_stream_bytes(doc: fitz.Document) -> int:
    used = set()
    total = 0
    # Count encoded stream bytes actually stored in the PDF, not extract_font's
    # decompressed program size (which cannot explain a file-size delta).
    for descriptor in range(1, doc.xref_length()):
        try:
            keys = set(doc.xref_get_keys(descriptor)) & {"FontFile", "FontFile2", "FontFile3"}
            for key in keys:
                kind, value = doc.xref_get_key(descriptor, key)
                if kind != "xref":
                    continue
                xref = int(value.split()[0])
                if xref not in used and doc.xref_is_stream(xref):
                    used.add(xref)
                    total += len(doc.xref_stream_raw(xref) or b"")
        except RuntimeError:
            continue
    return total


def _spatial_match(page: fitz.Page, text: str, box: fitz.Rect) -> bool:
    area = _expand(box, 2.0)
    local = normalized_text(page.get_text("text", clip=area, sort=True))
    if normalized_text(text) not in local:
        return False
    hits = page.search_for(text, clip=area)
    return bool(hits) and any(_inside(fitz.Rect(hit), area, 0.1) for hit in hits)


def _retained_hidden_geometry(before: fitz.Page, after: fitz.Page,
                              selected: set[tuple[int, int]]) -> dict:
    """Match each retained invisible glyph by content AND original geometry.

    Trace splitting, resource renaming and font subsetting may be harmless, so
    matching is per glyph and does not assume the same text-run segmentation.
    This gate is mandatory, even with no user-authored search checks.
    """
    tolerance = RETAINED_GLYPH_TOLERANCE_PT
    buckets = collections.defaultdict(list)
    output_count = 0
    for trace in after.get_texttrace():
        if trace["type"] != 3:
            continue
        for char in trace["chars"]:
            origin = char[2]
            key = (char[0], math.floor(origin[0] / tolerance), math.floor(origin[1] / tolerance))
            buckets[key].append((output_count, char, trace))
            output_count += 1
    consumed, failures = set(), []
    expected = 0
    for ti, trace in enumerate(before.get_texttrace()):
        if trace["type"] != 3:
            continue
        for ci, char in enumerate(trace["chars"]):
            if (ti, ci) in selected:
                continue
            expected += 1
            bx, by = math.floor(char[2][0] / tolerance), math.floor(char[2][1] / tolerance)
            match = None
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for identifier, candidate, candidate_trace in buckets.get((char[0], bx + dx, by + dy), []):
                        if identifier in consumed:
                            continue
                        geometry_equal = all(abs(a - b) <= tolerance for a, b in
                                             zip((*char[2], *char[3]), (*candidate[2], *candidate[3])))
                        direction_equal = all(abs(a - b) <= 1e-6 for a, b in
                                              zip(trace["dir"], candidate_trace["dir"]))
                        if (geometry_equal and direction_equal
                                and trace.get("wmode", 0) == candidate_trace.get("wmode", 0)
                                and abs(trace["opacity"] - candidate_trace["opacity"]) <= 1e-6):
                            match = identifier
                            break
                    if match is not None:
                        break
                if match is not None:
                    break
            if match is None:
                if len(failures) < 10:
                    failures.append({"source_trace": ti, "source_character": ci,
                                     "codepoint": char[0], "origin": _numbers(char[2]),
                                     "bbox": _numbers(char[3])})
            else:
                consumed.add(match)
    return {"equal": len(consumed) == expected, "tolerance_pt": tolerance,
            "expected_retained_characters": expected, "matched_retained_characters": len(consumed),
            "output_hidden_characters": output_count,
            "unmatched_retained_characters": expected - len(consumed), "examples": failures}


def qa(source_pdf_path: str | Path, output_path: str | Path,
       plan: dict | str | Path, *, max_render_pixels: int = DEFAULT_MAX_RENDER_PIXELS) -> dict:
    source_path, result_path = Path(source_pdf_path).resolve(), Path(output_path).resolve()
    spec = _load_plan(plan)
    report = {"schema_version": REPORT_VERSION, "ok": False, "errors": [], "pages": [],
              "source_sha256": sha256_file(source_path), "output_sha256": sha256_file(result_path)}
    errors = report["errors"]
    with _open_pdf(source_path) as source, _open_pdf(result_path) as output:
        _check_plan(source, source_path, spec)
        if output.page_count != source.page_count:
            errors.append("page_count_changed")
            return report
        try:
            source_images, output_images = image_inventory(source), image_inventory(output)
            report["image_preservation"] = {"exact": source_images == output_images,
                                             "source": source_images, "output": output_images}
            if source_images != output_images:
                errors.append("image_streams_dimensions_masks_or_placements_changed")
        except PipelineError as exc:
            errors.append(str(exc))
        if _annotation_inventory(source) != _annotation_inventory(output):
            errors.append("annotations_widgets_or_links_changed")
        if _visible_text_inventory(source) != _visible_text_inventory(output):
            errors.append("visible_native_text_or_geometry_changed")
        for before, after, page_spec in zip(source, output, spec["pages"]):
            page_errors = []
            if _page_geometry(before) != _page_geometry(after):
                page_errors.append("page_geometry_changed")
            try:
                a, dpi_a = _render(before, max_render_pixels=max_render_pixels)
                b, dpi_b = _render(after, max_render_pixels=max_render_pixels)
                visual_equal = (a.width, a.height, a.n, a.samples) == (b.width, b.height, b.n, b.samples)
                visual = {"equal": visual_equal, "dpi": dpi_a, "pixels": [a.width, a.height],
                          "source_sha256": _sha(a.samples), "output_sha256": _sha(b.samples)}
                if not visual_equal or dpi_a != dpi_b:
                    page_errors.append("visible_render_changed")
            except PipelineError as exc:
                visual = {"equal": False, "error": str(exc)}
                page_errors.append("visual_comparison_unavailable")
            chars = _outside_characters(after)
            if chars["outside"] != 0:
                page_errors.append("characters_outside_page")
            expected = normalized_text(page_spec["expected_text"])
            # Ordinary bounded extraction is the required path; infinite extraction
            # is only a diagnostic and must not conceal clipped/missing content.
            ordinary = after.get_text("text")
            actual = after.get_text("text", sort=True)
            bounded = after.get_text("text", clip=_bounds(after), sort=True)
            infinite = after.get_text("text", clip=fitz.INFINITE_RECT(), sort=True)
            if normalized_text(actual) != expected:
                page_errors.append("approved_text_mismatch_in_normal_sorted_extraction")
            if normalized_text(bounded) != expected:
                page_errors.append("approved_text_missing_from_page_bounded_extraction")
            if normalized_text(infinite) != expected:
                page_errors.append("unexpected_or_outside_text_in_infinite_extraction")
            # Secondary count check for default unsorted extraction. This is never
            # used alone: exact ordered comparison above and location checks below apply.
            if collections.Counter(normalized_text(ordinary).replace(" ", "")) != collections.Counter(expected.replace(" ", "")):
                page_errors.append("default_extraction_character_coverage_mismatch")
            edits, selected, _ = _planned_edits(before, page_spec)
            retained_geometry = _retained_hidden_geometry(before, after, selected)
            if not retained_geometry["equal"]:
                page_errors.append("retained_hidden_text_or_geometry_changed")
            checks = [{"text": line["text"], "bbox": line["bbox"]} for line in edits]
            checks += page_spec.get("search_checks", [])
            check_results = []
            for check in checks:
                matched = _spatial_match(after, check["text"], fitz.Rect(check["bbox"]))
                check_results.append({"text_sha256": _sha(check["text"].encode()),
                                      "bbox": check["bbox"], "found_at_expected_location": matched})
                if not matched:
                    page_errors.append("text_not_searchable_at_approved_location")
            report["pages"].append({"page": after.number + 1, "ok": not page_errors,
                                     "errors": page_errors, "visual_parity": visual,
                                     "characters": chars, "search_checks": check_results,
                                     "retained_hidden_geometry": retained_geometry,
                                     "expected_text_sha256": _sha(expected.encode()),
                                     "extracted_text_sha256": _sha(normalized_text(actual).encode())})
            errors.extend(f"page {after.number + 1}: {e}" for e in page_errors)
        source_size, output_size = source_path.stat().st_size, result_path.stat().st_size
        source_fonts, output_fonts = _font_stream_bytes(source), _font_stream_bytes(output)
        report["size_diagnostics"] = {"source_bytes": source_size, "output_bytes": output_size,
                                      "delta_bytes": output_size - source_size,
                                      "source_font_bytes": source_fonts, "output_font_bytes": output_fonts,
                                      "font_delta_bytes": output_fonts - source_fonts,
                                      "other_delta_bytes": (output_size - source_size) - (output_fonts - source_fonts),
                                      "images_resampled": False if report.get("image_preservation", {}).get("exact") else None,
                                      "note": "File deltas also include object tables, text streams and compression; no claim of image recompression savings."}
    report["ok"] = not errors
    return report


def build(source_pdf_path: str | Path, plan: dict | str | Path, output_path: str | Path, *,
          font_path: str | Path | None = None, qa_report_path: str | Path | None = None,
          max_render_pixels: int = DEFAULT_MAX_RENDER_PIXELS) -> dict:
    source_path, target = Path(source_pdf_path).resolve(), Path(output_path).resolve()
    if source_path == target or target.exists():
        raise PipelineError("Refusing to overwrite original/existing output; use a new output path")
    if qa_report_path and Path(qa_report_path).resolve() in (source_path, target):
        raise PipelineError("QA report cannot overwrite the original or candidate PDF")
    selected_font = Path(font_path) if font_path else DEFAULT_FONT
    if not selected_font.is_file():
        raise PipelineError("A suitable Unicode font file is required")
    spec = _load_plan(plan)
    original_hash = sha256_file(source_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=".model-ocr-candidate-", suffix=".pdf", dir=target.parent)
    os.close(descriptor)
    candidate = Path(temp_name)
    candidate.unlink()
    placements = []
    try:
        with _open_pdf(source_path) as doc:
            _check_plan(doc, source_path, spec)
            # Preflight proves image inventory and edit safety before mutation.
            image_inventory(doc)
            prepared = [_planned_edits(page, page_spec) for page, page_spec in zip(doc, spec["pages"])]
            font = fitz.Font(fontfile=str(selected_font))
            for number, (edits, selected, rectangles) in enumerate(prepared):
                page = doc[number]
                _remove_selected_hidden(page, rectangles)
                page = doc[number]
                # Resource name is unique relative to existing page fonts.
                used_names = {r[4] for r in page.get_fonts(full=True)}
                font_name = "ModelOCRUnicode"
                while font_name in used_names:
                    font_name += "X"
                insertions = [_insert_line(page, edit, font, selected_font, font_name) for edit in edits]
                placements.append({"page": number + 1, "removed_hidden_characters": len(selected),
                                   "insertions": insertions})
            doc.subset_fonts()
            doc.save(candidate, garbage=4, deflate=True, deflate_images=False, deflate_fonts=True)
        restoration = _restore_original_image_streams(source_path, candidate)
        report = qa(source_path, candidate, spec, max_render_pixels=max_render_pixels)
        report["save_strategy"] = {"subset_fonts": True, "optimized_save": {"garbage": 4, "deflate": True},
                                   "image_stream_restoration": restoration}
        report["placements"] = placements
        if sha256_file(source_path) != original_hash:
            report["ok"] = False
            report["errors"].append("original_pdf_bytes_changed")
        if qa_report_path:
            _write_json(qa_report_path, report)
        if not report["ok"]:
            raise PipelineError("Candidate failed mandatory QA: " + "; ".join(report["errors"][:12]))
        # Atomic same-filesystem publication after successful QA only.
        os.link(candidate, target)
        candidate.unlink()
        report["output_path"] = str(target)
        if qa_report_path:
            _write_json(qa_report_path, report)
        return report
    except PipelineError:
        raise
    except Exception as exc:
        raise PipelineError(f"PDF pipeline failed: {type(exc).__name__}: {exc}") from exc
    finally:
        candidate.unlink(missing_ok=True)
        candidate.with_suffix(".restored.pdf").unlink(missing_ok=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prep = subparsers.add_parser("prepare", help="Inventory and render original PDF/image without OCR")
    prep.add_argument("input")
    prep.add_argument("work_dir")
    prep.add_argument("--max-render-pixels", type=int, default=DEFAULT_MAX_RENDER_PIXELS)
    prep.add_argument("--image-dpi", type=float, default=300.0)
    make = subparsers.add_parser("build", help="Apply MODEL-approved line/word plan and run mandatory QA")
    make.add_argument("source_pdf")
    make.add_argument("plan")
    make.add_argument("output")
    make.add_argument("--font")
    make.add_argument("--qa-report")
    make.add_argument("--max-render-pixels", type=int, default=DEFAULT_MAX_RENDER_PIXELS)
    check = subparsers.add_parser("qa", help="Recheck actual source, output and approved plan")
    check.add_argument("source_pdf")
    check.add_argument("output")
    check.add_argument("plan")
    check.add_argument("--report")
    check.add_argument("--max-render-pixels", type=int, default=DEFAULT_MAX_RENDER_PIXELS)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            value = prepare(args.input, args.work_dir, max_render_pixels=args.max_render_pixels,
                            image_dpi=args.image_dpi)
            print(json.dumps({key: value[key] for key in ("schema_version", "base_pdf", "source_sha256",
                                                         "original_input_sha256", "page_count", "signature_detection")},
                             ensure_ascii=False))
            return 0
        if args.command == "build":
            value = build(args.source_pdf, args.plan, args.output, font_path=args.font,
                          qa_report_path=args.qa_report, max_render_pixels=args.max_render_pixels)
        else:
            value = qa(args.source_pdf, args.output, args.plan, max_render_pixels=args.max_render_pixels)
            if args.report:
                if Path(args.report).resolve() in (Path(args.source_pdf).resolve(), Path(args.output).resolve()):
                    raise PipelineError("QA report cannot overwrite a source/output PDF")
                _write_json(args.report, value)
        print(json.dumps({"ok": value["ok"], "errors": value["errors"],
                          "source_sha256": value["source_sha256"], "output_sha256": value["output_sha256"],
                          "pages": len(value["pages"])}, ensure_ascii=False))
        return 0 if value["ok"] else 2
    except (PipelineError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
