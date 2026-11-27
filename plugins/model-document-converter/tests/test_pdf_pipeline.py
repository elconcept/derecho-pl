"""Regression tests for observable preservation and OCR-layer behaviour.

All PDFs and images are generated synthetic fixtures in TemporaryDirectory.
Tests do not run OCR, process medical records, or claim MODEL reading accuracy.
Run with: python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import copy
import importlib.util
import io
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont

from pdf_fixtures import (
    FONT_PATH, LONG_LAB_LINE, POLISH, annotation_inventory,
    image_stream_inventory, make_image, make_scan_pdf, make_signature_pdf,
    rendered_pixels, sha,
)


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PLUGIN_ROOT / 'skills' / 'model-ocr' / 'scripts' / 'pdf_pipeline.py'
SPEC = importlib.util.spec_from_file_location('tested_pdf_pipeline', SCRIPT)
PIPELINE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PIPELINE
SPEC.loader.exec_module(PIPELINE)


def normalized(text: str) -> str:
    return ' '.join(unicodedata.normalize('NFC', text).split())


def trace_text(trace: dict) -> str:
    return ''.join(chr(char[0]) for char in trace['chars'])


def trace_box(trace: dict, start: int = 0, end: int | None = None) -> list[float]:
    chars = trace['chars'][start:end]
    return [min(c[3][0] for c in chars), min(c[3][1] for c in chars),
            max(c[3][2] for c in chars), max(c[3][3] for c in chars)]


def images_without_object_ids(doc: fitz.Document) -> list[dict]:
    return [{key: value for key, value in row.items() if key not in {'xref', 'mask'}}
            for row in image_stream_inventory(doc)]


def plan_for_patch(source: Path, replacements: dict[str, str], *,
                   search_checks: bool = True) -> dict:
    pages = []
    with fitz.open(source) as doc:
        for number, page in enumerate(doc, 1):
            lines = []
            checks = []
            expected = page.get_text('text', sort=True)
            for trace_index, trace in enumerate(page.get_texttrace()):
                old = trace_text(trace)
                if old not in replacements:
                    continue
                new = replacements[old]
                lines.append({
                    'text': new,
                    'geometry_verified': True,
                    'source': {'trace_index': trace_index, 'char_start': 0,
                               'char_end': len(trace['chars']),
                               'original_text': old},
                })
                expected = expected.replace(old, new)
                if search_checks:
                    box = trace_box(trace)
                    checks.append({'text': new, 'bbox': box})
            pages.append({
                'page': number,
                'mode': 'patch' if lines else 'keep',
                'expected_text': expected,
                'lines': lines,
                'search_checks': checks,
            })
    return {
        'schema_version': 'model-ocr-layer-plan-1',
        'source_sha256': sha(source.read_bytes()),
        'review_complete': True,
        'unresolved': [],
        'pages': pages,
    }


def plan_for_new_layer(source: Path, lines: list[dict]) -> dict:
    return {
        'schema_version': 'model-ocr-layer-plan-1',
        'source_sha256': sha(source.read_bytes()),
        'review_complete': True,
        'unresolved': [],
        'pages': [{
            'page': 1,
            'mode': 'add',
            'expected_text': '\n'.join(line['text'] for line in lines),
            'lines': [dict(line, geometry_verified=True) for line in lines],
            'search_checks': [{'text': line['text'], 'bbox': line['bbox']}
                              for line in lines],
        }],
    }


def scan_layer_lines() -> list[dict]:
    return [
        {'text': 'PLT', 'bbox': [52, 128, 76, 143]},
        {'text': '304', 'bbox': [180, 128, 204, 143]},
        {'text': 'KREATYNINA', 'bbox': [52, 173, 130, 188]},
        {'text': '112', 'bbox': [220, 173, 244, 188]},
        {'text': 'SYNTHETIC', 'bbox': [52, 208, 123, 223]},
        {'text': 'FIXTURE', 'bbox': [150, 208, 203, 223]},
        {'text': POLISH, 'bbox': [52, 248, 550, 264]},
        {'text': LONG_LAB_LINE, 'bbox': [52, 290, 560, 304]},
    ]


class PdfPipelineRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='model-ocr-synthetic-test-')
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def build(self, source: Path, plan: dict, name: str = 'searchable.pdf'):
        target = self.root / name
        report = PIPELINE.build(source, plan, target, font_path=FONT_PATH)
        self.assertTrue(report['ok'], report)
        self.assertTrue(target.is_file())
        return target, report

    def assert_same_page_appearance(self, source: Path, target: Path):
        with fitz.open(source) as before, fitz.open(target) as after:
            self.assertEqual(len(before), len(after))
            for number in range(len(before)):
                self.assertEqual(rendered_pixels(before, number),
                                 rendered_pixels(after, number),
                                 f'Page {number + 1} rendered appearance changed')
                self.assertEqual(tuple(before[number].mediabox), tuple(after[number].mediabox))
                self.assertEqual(tuple(before[number].cropbox), tuple(after[number].cropbox))
                self.assertEqual(before[number].rotation, after[number].rotation)

    def assert_chars_within_page(self, page):
        # MuPDF text geometry is unrotated even when the displayed page rotates.
        bounds = fitz.Rect(0, 0, page.cropbox.width, page.cropbox.height)
        for block in page.get_text('rawdict', clip=fitz.INFINITE_RECT())['blocks']:
            for line in block.get('lines', []):
                for span in line.get('spans', []):
                    for char in span.get('chars', []):
                        rect = fitz.Rect(char['bbox'])
                        self.assertGreaterEqual(rect.x0, bounds.x0 - 0.1, char)
                        self.assertGreaterEqual(rect.y0, bounds.y0 - 0.1, char)
                        self.assertLessEqual(rect.x1, bounds.x1 + 0.1, char)
                        self.assertLessEqual(rect.y1, bounds.y1 + 0.1, char)

    def test_patch_keeps_scan_streams_pixels_good_text_and_annotations(self):
        fixture = make_scan_pdf(self.root / 'synthetic.pdf')
        source_hash = sha(fixture.path.read_bytes())
        plan = plan_for_patch(fixture.path, {'30A': '304', '1I2': '112'})
        target, _ = self.build(fixture.path, plan)
        self.assertEqual(source_hash, sha(fixture.path.read_bytes()), 'Original bytes changed')
        with fitz.open(fixture.path) as before, fitz.open(target) as after:
            self.assertEqual(images_without_object_ids(before), images_without_object_ids(after))
            self.assertEqual(annotation_inventory(before), annotation_inventory(after))
            self.assertEqual(len(before[0].get_drawings()), len(after[0].get_drawings()))
            text = after[0].get_text()
            self.assertIn('304', text)
            self.assertIn('112', text)
            self.assertNotIn('30A', text)
            self.assertNotIn('1I2', text)
            self.assertIn(POLISH, text)
            for token in ('PLT', 'KREATYNINA', 'FIXTURE'):
                before_boxes = [tuple(box) for box in before[0].search_for(token)]
                after_boxes = [tuple(box) for box in after[0].search_for(token)]
                self.assertEqual(before_boxes, after_boxes, f'Good token {token} moved')
        self.assert_same_page_appearance(fixture.path, target)

    def test_corrected_numbers_are_searchable_at_the_original_locations(self):
        fixture = make_scan_pdf(self.root / 'synthetic.pdf')
        plan = plan_for_patch(fixture.path, {'30A': '304', '1I2': '112'})
        target, _ = self.build(fixture.path, plan)
        with fitz.open(target) as doc:
            for old, new in [('30A', '304'), ('1I2', '112')]:
                expected = fitz.Rect(fixture.bad_words[old])
                hits = doc[0].search_for(new)
                self.assertTrue(hits, f'{new} is not searchable')
                self.assertTrue(any(abs(hit.x0 - expected.x0) < 1.0 and
                                    abs(hit.x1 - expected.x1) < 1.0 and
                                    abs(hit.y0 - expected.y0) < 3.0
                                    for hit in hits), (new, expected, hits))
            self.assert_chars_within_page(doc[0])

    def test_visible_native_text_cannot_be_selected_for_ocr_repair(self):
        fixture = make_scan_pdf(self.root / 'synthetic.pdf')
        plan = plan_for_patch(fixture.path, {'SYNTHETIC TEST DOCUMENT': 'ALTERED'})
        target = self.root / 'must-not-publish.pdf'
        with self.assertRaises(PIPELINE.PipelineError):
            PIPELINE.build(fixture.path, plan, target, font_path=FONT_PATH)
        self.assertFalse(target.exists())

    def test_output_path_cannot_overwrite_the_original(self):
        fixture = make_scan_pdf(self.root / 'synthetic.pdf')
        original_bytes = fixture.path.read_bytes()
        plan = plan_for_patch(fixture.path, {'30A': '304', '1I2': '112'})
        with self.assertRaises(PIPELINE.PipelineError):
            PIPELINE.build(fixture.path, plan, fixture.path, font_path=FONT_PATH)
        self.assertEqual(fixture.path.read_bytes(), original_bytes)

    def test_partial_character_patch_is_rejected_instead_of_publishing_split_search_token(self):
        fixture = make_scan_pdf(self.root / 'synthetic.pdf')
        plan = plan_for_patch(fixture.path, {'30A': '304'})
        correction = plan['pages'][0]['lines'][0]
        correction['text'] = '4'
        correction['source'].update(char_start=2, char_end=3, original_text='A')
        plan['pages'][0]['search_checks'] = []
        target = self.root / 'must-not-publish.pdf'
        original_bytes = fixture.path.read_bytes()
        with self.assertRaises(PIPELINE.PipelineError):
            PIPELINE.build(fixture.path, plan, target, font_path=FONT_PATH)
        self.assertFalse(target.exists())
        self.assertEqual(fixture.path.read_bytes(), original_bytes)

    def test_original_redaction_annotation_is_not_applied_or_deleted(self):
        fixture = make_scan_pdf(self.root / 'redaction-annot.pdf', redaction_annot=True)
        plan = plan_for_patch(fixture.path, {'30A': '304', '1I2': '112'})
        target, _ = self.build(fixture.path, plan)
        with fitz.open(fixture.path) as before, fitz.open(target) as after:
            self.assertEqual(annotation_inventory(before), annotation_inventory(after))
        self.assert_same_page_appearance(fixture.path, target)

    def test_cropbox_and_rotations_preserve_geometry_and_scan(self):
        for rotation in (0, 90, 180, 270):
            with self.subTest(rotation=rotation):
                fixture = make_scan_pdf(self.root / f'rotated-{rotation}.pdf',
                                        rotation=rotation, cropped=True)
                plan = plan_for_patch(fixture.path, {'30A': '304', '1I2': '112'})
                target, _ = self.build(fixture.path, plan, f'output-{rotation}.pdf')
                self.assert_same_page_appearance(fixture.path, target)
                with fitz.open(target) as doc:
                    self.assertIn('304', doc[0].get_text())
                    self.assertIn('112', doc[0].get_text())
                    self.assert_chars_within_page(doc[0])

    def test_blank_pages_are_retained_exactly_once(self):
        fixture = make_scan_pdf(self.root / 'blank-page.pdf', blank_page=True)
        plan = plan_for_patch(fixture.path, {'30A': '304', '1I2': '112'})
        target, _ = self.build(fixture.path, plan)
        with fitz.open(target) as doc:
            self.assertEqual(len(doc), 2)
            self.assertEqual(doc[1].get_text(), '')
        self.assert_same_page_appearance(fixture.path, target)

    def test_png_prepare_retains_original_bytes_and_native_image_dimensions(self):
        source = make_image(self.root / 'synthetic.png')
        original = source.read_bytes()
        info = PIPELINE.prepare(source, self.root / 'png-work')
        self.assertEqual(source.read_bytes(), original)
        base = Path(info['base_pdf'])
        with fitz.open(base) as doc:
            self.assertEqual(len(doc), 1)
            images = doc[0].get_images(full=True)
            self.assertEqual(len(images), 1)
            self.assertEqual(tuple(images[0][2:4]), (900, 1200))
            pix = fitz.Pixmap(doc, images[0][0])
            image = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
            self.assertEqual(image.tobytes(), Image.open(source).convert('RGB').tobytes())

    def test_jpeg_prepare_preserves_compressed_image_bytes(self):
        source = make_image(self.root / 'synthetic.jpg', fmt='JPEG')
        original = source.read_bytes()
        info = PIPELINE.prepare(source, self.root / 'jpeg-work')
        self.assertEqual(source.read_bytes(), original)
        with fitz.open(info['base_pdf']) as doc:
            images = doc[0].get_images(full=True)
            self.assertEqual(tuple(images[0][2:4]), (900, 1200))
            self.assertEqual(doc.xref_stream_raw(images[0][0]), original)

    def test_unfiltered_image_and_soft_mask_bytes_survive_ocr_repair(self):
        source = self.root / 'unfiltered-rgba.pdf'
        raster = Image.new('RGBA', (600, 800), (255, 255, 255, 255))
        draw = ImageDraw.Draw(raster)
        draw.rectangle((40, 40, 560, 200), fill=(10, 70, 130, 100))
        draw.text((104, 280), '304', fill=(0, 0, 0, 255), anchor='ls',
                  font=ImageFont.truetype(str(FONT_PATH), 24))
        image_bytes = io.BytesIO()
        raster.save(image_bytes, format='PNG')
        with fitz.open() as doc:
            page = doc.new_page(width=300, height=400)
            xref = page.insert_image(page.rect, stream=image_bytes.getvalue())
            soft_mask = page.get_images(full=True)[0][1]
            self.assertGreater(soft_mask, 0, 'Fixture must exercise an image mask')
            for object_number in (xref, soft_mask):
                doc.update_stream(object_number, doc.xref_stream(object_number), compress=False)
            page.insert_text((52, 140), '30A', fontname='fixturefont',
                             fontfile=str(FONT_PATH), fontsize=12, render_mode=3)
            doc.save(source, garbage=0, deflate=False)
        plan = plan_for_patch(source, {'30A': '304'})
        target, _ = self.build(source, plan)
        with fitz.open(source) as before, fitz.open(target) as after:
            old = before[0].get_images(full=True)[0]
            new = after[0].get_images(full=True)[0]
            self.assertEqual(old[2:4], new[2:4])
            for old_xref, new_xref in [(old[0], new[0]), (old[1], new[1])]:
                self.assertEqual(before.xref_stream_raw(old_xref), before.xref_stream(old_xref),
                                 'Fixture must exercise initially unfiltered bytes')
                self.assertEqual(before.xref_stream_raw(old_xref), after.xref_stream_raw(new_xref))
        self.assert_same_page_appearance(source, target)

    def test_unicode_long_lines_are_complete_in_default_extraction_and_within_page(self):
        fixture = make_scan_pdf(self.root / 'no-ocr.pdf', hidden=False,
                                native_heading=False)
        base = fixture.path
        lines = scan_layer_lines()
        plan = plan_for_new_layer(base, lines)
        target, _ = self.build(base, plan)
        self.assert_same_page_appearance(base, target)
        with fitz.open(target) as doc:
            normal = doc[0].get_text('text', sort=True)
            unlimited = doc[0].get_text('text', sort=True, clip=fitz.INFINITE_RECT())
            self.assertEqual(normalized(normal), normalized(unlimited))
            self.assertEqual(normalized(normal), normalized(plan['pages'][0]['expected_text']))
            self.assertIn(POLISH, normal)
            self.assertIn(normalized(LONG_LAB_LINE), normalized(normal))
            self.assertTrue(doc[0].search_for('PLT'))
            self.assertTrue(doc[0].search_for('304'))
            self.assertTrue(doc[0].search_for('KREATYNINA'))
            self.assertTrue(doc[0].search_for('112'))
            self.assert_chars_within_page(doc[0])

    def test_add_ocr_to_scanned_body_keeps_native_header(self):
        fixture = make_scan_pdf(self.root / 'mixed.pdf', hidden=False)
        plan = plan_for_new_layer(fixture.path, scan_layer_lines())
        with fitz.open(fixture.path) as before:
            native_text = before[0].get_text('text', sort=True)
            native_boxes = [tuple(box) for box in before[0].search_for('SYNTHETIC TEST DOCUMENT')]
        plan['pages'][0]['expected_text'] = native_text + '\n' + plan['pages'][0]['expected_text']
        target, _ = self.build(fixture.path, plan)
        with fitz.open(target) as after:
            self.assertEqual(native_boxes,
                [tuple(box) for box in after[0].search_for('SYNTHETIC TEST DOCUMENT')])
            self.assertIn(POLISH, after[0].get_text())
            self.assertTrue(after[0].search_for('304'))
        self.assert_same_page_appearance(fixture.path, target)

    def test_add_ocr_rejects_overlap_with_existing_native_glyphs(self):
        fixture = make_scan_pdf(self.root / 'mixed.pdf', hidden=False)
        with fitz.open(fixture.path) as before:
            native_trace = before[0].get_texttrace()[0]
            box = trace_box(native_trace)
            original_text = before[0].get_text()
        plan = plan_for_new_layer(fixture.path, [{'text': 'OVERLAPPING', 'bbox': box}])
        plan['pages'][0]['expected_text'] = original_text + 'OVERLAPPING'
        target = self.root / 'must-not-publish.pdf'
        with self.assertRaises(PIPELINE.PipelineError):
            PIPELINE.build(fixture.path, plan, target, font_path=FONT_PATH)
        self.assertFalse(target.exists())

    def test_rebuild_removes_outside_page_hidden_garbage_without_rasterization(self):
        source = make_image(self.root / 'synthetic.png')
        info = PIPELINE.prepare(source, self.root / 'image-work')
        clean = Path(info['base_pdf'])
        damaged = self.root / 'bad-hidden-geometry.pdf'
        with fitz.open(clean) as doc:
            page = doc[0]
            page.insert_text((page.rect.width + 50, 70), 'OFFPAGE_BAD_OCR',
                             render_mode=3)
            doc.save(damaged)
        lines = [{'text': 'SYNTHETIC IMAGE 123', 'bbox': [15, 22, 190, 38]}]
        plan = plan_for_new_layer(damaged, lines)
        plan['pages'][0].update(mode='rebuild_hidden',
                                geometry_override_reviewed=True,
                                rebuild_reason='Synthetic source OCR is outside page')
        target, _ = self.build(damaged, plan)
        self.assert_same_page_appearance(damaged, target)
        with fitz.open(damaged) as before, fitz.open(target) as after:
            self.assertEqual(images_without_object_ids(before), images_without_object_ids(after))
            self.assertNotIn('OFFPAGE_BAD_OCR', after[0].get_text(clip=fitz.INFINITE_RECT()))
            self.assertIn('SYNTHETIC IMAGE 123', after[0].get_text())
            self.assert_chars_within_page(after[0])

    def test_qa_rejects_changed_visible_pixels(self):
        fixture = make_scan_pdf(self.root / 'synthetic.pdf')
        plan = plan_for_patch(fixture.path, {'30A': '304', '1I2': '112'})
        target, _ = self.build(fixture.path, plan)
        corrupted = self.root / 'visually-corrupted.pdf'
        with fitz.open(target) as doc:
            doc[0].draw_rect(fitz.Rect(50, 130, 240, 145), fill=(1, 1, 1), color=None)
            doc.save(corrupted)
        report = PIPELINE.qa(fixture.path, corrupted, plan)
        self.assertFalse(report['ok'], report)
        self.assertTrue(report['errors'])

    def test_qa_rejects_missing_or_wrong_searchable_text(self):
        fixture = make_scan_pdf(self.root / 'synthetic.pdf')
        plan = plan_for_patch(fixture.path, {'30A': '304', '1I2': '112'})
        # The untouched source has identical visible pixels but wrong OCR.
        report = PIPELINE.qa(fixture.path, fixture.path, plan)
        self.assertFalse(report['ok'], report)
        self.assertTrue(report['errors'])

    def test_qa_rejects_rewritten_image_stream_even_when_pixels_are_identical(self):
        fixture = make_scan_pdf(self.root / 'synthetic.pdf')
        plan = plan_for_patch(fixture.path, {'30A': '304', '1I2': '112'})
        target, _ = self.build(fixture.path, plan)
        rewritten = self.root / 'same-pixels-different-jpeg.pdf'
        with fitz.open(target) as doc:
            xref = doc[0].get_images(full=True)[0][0]
            jpeg = doc.xref_stream_raw(xref)
            self.assertEqual(jpeg[:2], b'\xff\xd8')
            comment = b'Synthetic no-pixel-change rewrite regression'
            marker = b'\xff\xfe' + (len(comment) + 2).to_bytes(2, 'big') + comment
            doc.update_stream(xref, jpeg[:2] + marker + jpeg[2:], compress=False)
            doc.xref_set_key(xref, 'Filter', '/DCTDecode')
            doc.save(rewritten, garbage=0, deflate=False)
        self.assert_same_page_appearance(target, rewritten)
        report = PIPELINE.qa(fixture.path, rewritten, plan)
        self.assertFalse(report['ok'], report)
        self.assertTrue(report['errors'])

    def test_search_location_must_match_plan(self):
        fixture = make_scan_pdf(self.root / 'synthetic.pdf')
        plan = plan_for_patch(fixture.path, {'30A': '304', '1I2': '112'})
        plan['pages'][0]['search_checks'][0]['bbox'] = [450, 600, 510, 625]
        target = self.root / 'must-not-publish.pdf'
        with self.assertRaises(PIPELINE.PipelineError):
            PIPELINE.build(fixture.path, plan, target, font_path=FONT_PATH)
        self.assertFalse(target.exists())

    def test_review_hash_and_page_coverage_gates_reject_unfinished_plans(self):
        fixture = make_scan_pdf(self.root / 'synthetic.pdf', blank_page=True)
        valid = plan_for_patch(fixture.path, {'30A': '304', '1I2': '112'})
        cases = {}
        unresolved = copy.deepcopy(valid)
        unresolved['unresolved'] = ['p1-b1: verify whether digit is 4 or A']
        cases['unresolved'] = unresolved
        incomplete = copy.deepcopy(valid)
        incomplete['review_complete'] = False
        cases['review incomplete'] = incomplete
        wrong_hash = copy.deepcopy(valid)
        wrong_hash['source_sha256'] = '0' * 64
        cases['wrong source hash'] = wrong_hash
        missing_page = copy.deepcopy(valid)
        missing_page['pages'].pop()
        cases['missing page'] = missing_page
        duplicate_page = copy.deepcopy(valid)
        duplicate_page['pages'][1]['page'] = 1
        cases['duplicate page'] = duplicate_page
        for index, (label, plan) in enumerate(cases.items()):
            with self.subTest(case=label):
                target = self.root / f'not-published-{index}.pdf'
                with self.assertRaises(PIPELINE.PipelineError):
                    PIPELINE.build(fixture.path, plan, target, font_path=FONT_PATH)
                self.assertFalse(target.exists())

    def test_new_layer_rejects_geometry_outside_page(self):
        source = make_image(self.root / 'synthetic.png')
        info = PIPELINE.prepare(source, self.root / 'image-work')
        base = Path(info['base_pdf'])
        plan = plan_for_new_layer(base, [{'text': 'PLT 304', 'bbox': [-10, 25, 140, 40]}])
        target = self.root / 'must-not-publish.pdf'
        with self.assertRaises(PIPELINE.PipelineError):
            PIPELINE.build(base, plan, target, font_path=FONT_PATH)
        self.assertFalse(target.exists())

    def test_prepare_distinguishes_unsigned_empty_field_and_embedded_signature(self):
        unsigned = make_scan_pdf(self.root / 'unsigned.pdf')
        empty = make_signature_pdf(self.root / 'empty-signature.pdf', populated=False)
        signed = make_signature_pdf(self.root / 'signed-synthetic.pdf', populated=True)
        reports = {
            'unsigned': PIPELINE.prepare(unsigned.path, self.root / 'unsigned-work'),
            'empty': PIPELINE.prepare(empty, self.root / 'empty-work'),
            'signed': PIPELINE.prepare(signed, self.root / 'signed-work'),
        }
        # Inspect structured presence rather than visual marks or field names.
        for name in ('unsigned', 'empty'):
            detection = reports[name]['signature_detection']
            self.assertEqual(detection['status'], 'not_present', (name, detection))
        detection = reports['signed']['signature_detection']
        self.assertEqual(detection['status'], 'present', detection)
        self.assertGreaterEqual(detection['count'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
