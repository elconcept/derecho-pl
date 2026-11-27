"""Corrected-code regressions for confirmed G62 PDF findings.

These tests exercise the current implementation only. They never load an old
plugin release or execute the external auditor's reproduction scripts.
"""
from __future__ import annotations

import io
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

import fitz
from PIL import Image, ImageDraw

from pdf_fixtures import FONT_PATH, make_image, make_scan_pdf, sha
from test_pdf_pipeline import PIPELINE, plan_for_patch, trace_text


class ConfirmedPdfAuditFixes(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='model-ocr-corrected-pdf-')
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _line_pdf(self, path, text='AAA BBBBBB 30A', shift=(0, 0)):
        raster = Image.new('RGB', (800, 400), 'white')
        ImageDraw.Draw(raster).text((60, 100), 'Synthetic audit fixture', fill='black')
        stream = io.BytesIO()
        raster.save(stream, format='PNG')
        with fitz.open() as document:
            page = document.new_page(width=400, height=200)
            page.insert_image(page.rect, stream=stream.getvalue())
            page.insert_text((35 + shift[0], 70 + shift[1]), text,
                             fontfile=str(FONT_PATH), fontname='Fixture', fontsize=12,
                             render_mode=3)
            document.save(path, garbage=0, deflate=False)
        return path

    def test_g62_04_multiword_patch_rejected_before_publication(self):
        source = self._line_pdf(self.root / 'source.pdf', 'III MMMMMMMMMM II1')
        plan = plan_for_patch(source, {'III MMMMMMMMMM II1': 'III MMMMMMMMMM III'},
                              search_checks=False)
        original_bytes = source.read_bytes()
        output = self.root / 'must-not-exist.pdf'
        with self.assertRaisesRegex(PIPELINE.PipelineError, 'word|token'):
            PIPELINE.build(source, plan, output)
        self.assertFalse(output.exists())
        self.assertEqual(original_bytes, source.read_bytes())

    def test_g62_04_single_word_within_trace_preserves_every_neighbor(self):
        source = self._line_pdf(self.root / 'source.pdf')
        with fitz.open(source) as document:
            trace = document[0].get_texttrace()[0]
            old = trace_text(trace)
            start = old.index('30A')
            source_words = document[0].get_text('words')
            expected = document[0].get_text('text', sort=True).replace('30A', '304')
        plan = {'schema_version': PIPELINE.PLAN_VERSION, 'source_sha256': sha(source.read_bytes()),
                'review_complete': True, 'unresolved': [], 'pages': [{
                    'page': 1, 'mode': 'patch', 'expected_text': expected,
                    'lines': [{'text': '304', 'geometry_verified': True,
                               'source': {'trace_index': 0, 'char_start': start,
                                          'char_end': start + 3, 'original_text': '30A'}}],
                    'search_checks': []}]}
        output = self.root / 'corrected.pdf'
        report = PIPELINE.build(source, plan, output)
        self.assertTrue(report['ok'])
        proof = report['pages'][0]['retained_hidden_geometry']
        self.assertTrue(proof['equal'])
        self.assertEqual(proof['expected_retained_characters'], start)
        with fitz.open(output) as document:
            after_words = document[0].get_text('words')
            self.assertEqual(source_words[:2], after_words[:2])
            self.assertTrue(document[0].search_for('304'))

    def test_g62_05_keep_rejects_moved_hidden_glyphs_without_optional_searches(self):
        source = self._line_pdf(self.root / 'source.pdf', 'APPROVED HIDDEN TEXT')
        candidate = self._line_pdf(self.root / 'moved.pdf', 'APPROVED HIDDEN TEXT', (80, 90))
        plan = plan_for_patch(source, {}, search_checks=False)
        report = PIPELINE.qa(source, candidate, plan)
        self.assertFalse(report['ok'])
        page = report['pages'][0]
        self.assertTrue(page['visual_parity']['equal'])
        self.assertEqual(page['expected_text_sha256'], page['extracted_text_sha256'])
        self.assertIn('retained_hidden_text_or_geometry_changed', page['errors'])
        self.assertGreater(page['retained_hidden_geometry']['unmatched_retained_characters'], 0)

    def test_g62_05_patch_proof_covers_unselected_ocr_without_search_checks(self):
        fixture = make_scan_pdf(self.root / 'source.pdf')
        plan = plan_for_patch(fixture.path, {'30A': '304'}, search_checks=False)
        output = self.root / 'corrected.pdf'
        report = PIPELINE.build(fixture.path, plan, output)
        proof = report['pages'][0]['retained_hidden_geometry']
        with fitz.open(fixture.path) as source:
            hidden_count = sum(len(t['chars']) for t in source[0].get_texttrace() if t['type'] == 3)
        self.assertTrue(proof['equal'])
        self.assertEqual(proof['expected_retained_characters'], hidden_count - 3)
        self.assertEqual(proof['matched_retained_characters'], hidden_count - 3)

    def test_g62_06_high_bit_and_float_sources_fail_before_any_base(self):
        high = Image.frombytes('I;16', (2, 1), struct.pack('<HH', 1000, 50000))
        high.save(self.root / 'two-level.tiff')
        high.save(self.root / 'two-level.png')
        floating = Image.new('F', (2, 1))
        floating.putdata([0.25, 0.75])
        floating.save(self.root / 'float.tiff')
        (self.root / 'rgb16.ppm').write_bytes(b'P6\n2 1\n65535\n' +
            struct.pack('>HHHHHH', 1000, 1000, 1000, 50000, 50000, 50000))
        for name in ('two-level.tiff', 'two-level.png', 'float.tiff', 'rgb16.ppm'):
            with self.subTest(name=name):
                source = self.root / name
                before = source.read_bytes()
                work = self.root / (name + '-work')
                with self.assertRaisesRegex(PIPELINE.PipelineError, 'high-bit|float'):
                    PIPELINE.prepare(source, work)
                self.assertEqual(source.read_bytes(), before)
                self.assertFalse((work / 'image-base.pdf').exists())
                self.assertFalse((work / 'inventory.json').exists())
                self.assertFalse(list((work / 'renders').glob('*.png')))

    def test_g62_06_container_depth_detects_rgb16_even_if_decoder_reports_rgb(self):
        def chunk(kind, data):
            return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
        header = struct.pack('>IIBBBBB', 2, 1, 16, 2, 0, 0, 0)
        samples = b'\x00' + struct.pack('>HHHHHH', 1000, 1000, 1000, 50000, 50000, 50000)
        source = self.root / 'rgb16.png'
        source.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header)
                           + chunk(b'IDAT', zlib.compress(samples)) + chunk(b'IEND', b''))
        with Image.open(source) as image:
            self.assertEqual(image.mode, 'RGB', 'Fixture must exercise container-depth inspection')
        work = self.root / 'rgb16-work'
        with self.assertRaisesRegex(PIPELINE.PipelineError, 'high-bit'):
            PIPELINE.prepare(source, work)
        self.assertFalse((work / 'image-base.pdf').exists())

    def test_g62_06_later_high_bit_tiff_frame_does_not_leave_partial_pdf(self):
        first = Image.new('L', (40, 60), 180)
        second = Image.frombytes('I;16', (40, 60), struct.pack('<H', 1000) * 2400)
        source = self.root / 'mixed-depth.tiff'
        first.save(source, save_all=True, append_images=[second])
        with Image.open(source) as image:
            image.seek(1)
            self.assertEqual(image.mode, 'I;16')
        work = self.root / 'mixed-work'
        with self.assertRaisesRegex(PIPELINE.PipelineError, 'high-bit'):
            PIPELINE.prepare(source, work)
        self.assertFalse((work / 'image-base.pdf').exists())
        self.assertFalse(list((work / 'renders').glob('*.png')))

    def test_g62_07_alpha_preview_matches_actual_pdf_on_white_background(self):
        source = self.root / 'transparent.png'
        image = Image.new('RGBA', (180, 240), (0, 0, 0, 0))
        drawing = ImageDraw.Draw(image)
        drawing.rectangle((30, 50, 140, 80), fill=(0, 0, 0, 255))
        drawing.rectangle((30, 100, 140, 130), fill=(200, 20, 50, 128))
        image.save(source)
        info = PIPELINE.prepare(source, self.root / 'alpha-work')
        page_info = info['pages'][0]
        with Image.open(page_info['render']) as preview, fitz.open(info['base_pdf']) as base:
            self.assertEqual(preview.mode, 'RGB')
            self.assertGreaterEqual(min(preview.size), 1536)
            self.assertEqual(preview.getpixel((0, 0)), (255, 255, 255))
            scale = page_info['render_dpi'] / 72
            actual = base[0].get_pixmap(matrix=fitz.Matrix(scale, scale),
                                      colorspace=fitz.csRGB, alpha=False, annots=True)
            self.assertEqual(preview.size, (actual.width, actual.height))
            self.assertEqual(preview.tobytes(), actual.samples)
        self.assertTrue(info['source_base_binding']['ok'])

    def test_g62_02_pdf_kind_spoof_cannot_bypass_original_byte_binding(self):
        original = self._line_pdf(self.root / 'actual-pdf.png')
        other = self._line_pdf(self.root / 'other.pdf', 'UNRELATED CONTENT')
        for expected_kind in ('image', 'pdf', None):
            with self.subTest(expected_kind=expected_kind):
                with self.assertRaises(PIPELINE.PipelineError):
                    PIPELINE.verify_source_base(original, other, expected_kind,
                        {'input_sha256': sha(original.read_bytes()), 'source_sha256': sha(other.read_bytes())})
        proof = PIPELINE.verify_source_base(original, original, 'pdf')
        self.assertEqual(proof['binding'], 'byte_identical_pdf')
        self.assertEqual(proof['actual_kind'], 'pdf')
        self.assertEqual(proof['page_count'], 1)

    def test_g62_02_image_binding_checks_actual_pixels_not_supplied_hashes(self):
        original = make_image(self.root / 'source.png', size=(240, 320))
        info = PIPELINE.prepare(original, self.root / 'source-work')
        unrelated = self.root / 'unrelated.png'
        Image.new('RGB', (240, 320), 'navy').save(unrelated)
        false_inventory = json.loads(json.dumps(info))
        false_inventory['input_sha256'] = sha(unrelated.read_bytes())
        false_inventory['original_input_sha256'] = false_inventory['input_sha256']
        with self.assertRaisesRegex(PIPELINE.PipelineError, 'pixels|mask|color'):
            PIPELINE.verify_source_base(unrelated, info['base_pdf'], 'image', false_inventory)
        proof = PIPELINE.verify_source_base(original, info['base_pdf'], 'image', info)
        self.assertEqual(proof['binding'], 'verified_image_pixels')
        self.assertTrue(proof['frames'][0]['pixels_and_mask_equal'])
        with self.assertRaisesRegex(PIPELINE.PipelineError, 'inventory'):
            PIPELINE.verify_source_base(original, info['base_pdf'], 'image',
                {'input_sha256': info['input_sha256'], 'source_sha256': info['source_sha256']})

    def test_g62_02_every_original_tiff_frame_is_bound_in_order(self):
        source = self.root / 'two-frames.tiff'
        first = Image.new('RGB', (140, 180), (200, 20, 30))
        second = Image.new('RGB', (160, 200), (10, 30, 190))
        first.save(source, save_all=True, append_images=[second])
        info = PIPELINE.prepare(source, self.root / 'frames-work')
        proof = PIPELINE.verify_source_base(source, info['base_pdf'], 'image', info)
        self.assertEqual(proof['page_count'], 2)
        self.assertEqual([frame['oriented_pixels'] for frame in proof['frames']], [[140, 180], [160, 200]])
        reversed_pdf = self.root / 'reversed.pdf'
        with fitz.open(info['base_pdf']) as document:
            document.select([1, 0])
            document.save(reversed_pdf)
        with self.assertRaises(PIPELINE.PipelineError):
            PIPELINE.verify_source_base(source, reversed_pdf, 'image')


if __name__ == '__main__':
    unittest.main()
