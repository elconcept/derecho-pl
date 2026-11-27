"""Observable signature routing and honest reporting; no trust claims."""
from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import fitz

from pdf_fixtures import make_image, make_scan_pdf, make_signature_pdf, sha

SCRIPT_DIR = (Path(__file__).resolve().parents[1] / 'skills' / 'model-ocr' / 'scripts')
sys.path.insert(0, str(SCRIPT_DIR))
import check_signatures as CHECK


class SignatureReportingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='model-signature-synthetic-')
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def backend_for(self, source, *, status=None, error=None):
        candidate = CHECK.detect_signatures(source)['candidates'][0]
        embedded = SimpleNamespace(field_name=candidate['field_name'], sig_object={
            '/Type': candidate['type'], '/SubFilter': candidate['subfilter'],
            '/ByteRange': candidate['byte_range']})
        validate = mock.Mock(side_effect=error) if error else mock.Mock(return_value=status)
        return {
            'reader': lambda _: SimpleNamespace(embedded_signatures=[embedded]),
            'context': mock.Mock(return_value=object()), 'load_cert': mock.Mock(),
            'validate_signature': validate, 'validate_timestamp': validate,
            'version': 'synthetic-test-backend',
        }

    def test_unsigned_and_empty_field_skip_without_loading_crypto_backend(self):
        unsigned = make_scan_pdf(self.root / 'unsigned.pdf').path
        empty = make_signature_pdf(self.root / 'empty.pdf', populated=False)
        for path in (unsigned, empty):
            with self.subTest(source=path.name), mock.patch.object(CHECK, '_load_backend') as backend:
                digest = sha(path.read_bytes())
                report = CHECK.check(path)
                self.assertEqual(report['status'], 'skipped')
                self.assertEqual(report['detection']['status'], 'not_present')
                self.assertFalse(report['cryptographic_validation_performed'])
                self.assertEqual(report['original_sha256'], digest)
                self.assertEqual(sha(path.read_bytes()), digest)
                backend.assert_not_called()

    def test_image_is_not_applicable(self):
        source = make_image(self.root / 'synthetic.png')
        with mock.patch.object(CHECK, '_load_backend') as backend:
            report = CHECK.check(source)
        self.assertEqual(report['status'], 'not_applicable')
        self.assertEqual(report['source_kind'], 'image')
        self.assertFalse(report['cryptographic_validation_performed'])
        backend.assert_not_called()

    def test_real_selfsigned_cms_without_optional_validator_is_not_verified(self):
        source = make_signature_pdf(self.root / 'signed.pdf', populated=True)
        digest = sha(source.read_bytes())
        with mock.patch.object(CHECK, '_load_backend', side_effect=ImportError('synthetic missing dependency')):
            report = CHECK.check(source)
        self.assertEqual(report['detection']['status'], 'present')
        self.assertEqual(report['status'], 'not_verified')
        self.assertFalse(report['cryptographic_validation_performed'])
        self.assertEqual(report['qualified_signature_status'], 'not_assessed')
        self.assertFalse(report['network_fetching'])
        self.assertEqual(sha(source.read_bytes()), digest)
        self.assertIs(CHECK.validate_report(source, report), report)

    def test_failed_signature_does_not_skip_next_and_unknown_is_not_invalid(self):
        # Controlled validator responses test reporting/isolation, not crypto.
        source = make_signature_pdf(self.root / 'signed.pdf', populated=True)
        embedded = [SimpleNamespace(field_name=f'fixture-{n}',
                    sig_object={'/Type': '/Sig', '/ByteRange': [0, 10, 20, 30]})
                    for n in range(2)]
        context = mock.Mock(return_value=object())
        valid = SimpleNamespace(intact=True, valid=True, trusted=False,
                    coverage=SimpleNamespace(name='ENTIRE_REVISION'),
                    modification_level=SimpleNamespace(name='LTA_UPDATES'),
                    docmdp_ok=True, timestamp_validity=None, signing_cert=None,
                    trust_problem_indic=None, signer_reported_dt=None)
        validate = mock.Mock(side_effect=[ValueError('synthetic damaged signature'), valid])
        backend = {'reader': lambda _: SimpleNamespace(embedded_signatures=embedded),
                   'context': context, 'load_cert': mock.Mock(),
                   'validate_signature': validate, 'validate_timestamp': mock.Mock(),
                   'version': 'synthetic-test-backend'}
        detection = {'status': 'present', 'count': 2, 'signatures': []}
        with mock.patch.object(CHECK, '_load_backend', return_value=backend), \
             mock.patch.object(CHECK, 'detect_signatures', return_value=detection):
            report = CHECK.check(source)
        self.assertEqual(validate.call_count, 2)
        self.assertEqual(report['status'], 'partially_checked')
        self.assertEqual(report['signatures'][0]['integrity'], 'unknown')
        second = report['signatures'][1]
        self.assertEqual(second['integrity'], 'valid')
        self.assertFalse(second['trusted_in_supplied_context'])
        self.assertEqual(second['conclusion'], 'integrity_valid_signed_revision_only')
        self.assertEqual(second['modification_level'], 'LTA_UPDATES')
        self.assertEqual(second['qualified_signature_status'], 'not_assessed')
        self.assertFalse(context.call_args.kwargs['allow_fetching'])
        self.assertEqual(context.call_args.kwargs['trust_roots'], [])
        self.assertTrue(report['cryptographic_validation_attempted'])
        self.assertTrue(report['cryptographic_validation_performed'])
        self.assertFalse(report['cryptographic_validation_completed'])
        self.assertEqual(report['validation_counts']['attempted'], 2)
        self.assertEqual(report['validation_counts']['completed'], 1)

    def test_missing_integrity_values_remain_unknown(self):
        partial = SimpleNamespace(intact=True, valid=None, trusted=None,
                                  timestamp_validity=None)
        report = CHECK._status_record(partial, document_timestamp=False)
        self.assertEqual(report['integrity'], 'unknown')
        self.assertEqual(report['conclusion'], 'integrity_unknown')
        self.assertIsNone(report['signature_math_valid'])
        self.assertIsNone(report['trusted_in_supplied_context'])

    def test_bad_source_is_error_not_unsigned(self):
        source = self.root / 'malformed.pdf'
        source.write_bytes(b'This is not a PDF or image.')
        report = CHECK.check(source)
        self.assertEqual(report['status'], 'error')
        self.assertEqual(report['detection']['status'], 'unknown')
        self.assertFalse(report['cryptographic_validation_performed'])

    def test_all_time_kinds_remain_distinct_and_keep_their_verification_scope(self):
        self_reported = datetime(2026, 1, 2, 8, 0, tzinfo=timezone.utc)
        content_time = datetime(2026, 1, 2, 8, 1, tzinfo=timezone.utc)
        signature_time = datetime(2026, 1, 2, 8, 2, tzinfo=timezone.utc)
        content = SimpleNamespace(timestamp=content_time, intact=None, valid=None, trusted=None)
        signature = SimpleNamespace(timestamp=signature_time, intact=True, valid=True, trusted=False)
        for label, reported, content_ts, signature_ts in [
            ('signer only', self_reported, None, None),
            ('content only', None, content, None),
            ('signature only', None, None, signature),
            ('all ordinary kinds', self_reported, content, signature),
        ]:
            with self.subTest(case=label):
                status = SimpleNamespace(intact=True, valid=True, trusted=False,
                    signer_reported_dt=reported, content_timestamp_validity=content_ts,
                    timestamp_validity=signature_ts)
                row = CHECK._status_record(status, document_timestamp=False)
                self.assertEqual(row['signer_reported_time'], reported.isoformat() if reported else None)
                self.assertEqual(row['signer_reported_time_basis'], 'self_reported_unverified')
                self.assertEqual(row['content_timestamp']['presence'], 'present' if content_ts else 'not_present')
                self.assertEqual(row['signature_timestamp']['presence'], 'present' if signature_ts else 'not_present')
                self.assertEqual(row['document_timestamp']['presence'], 'not_applicable')
                if content_ts:
                    self.assertEqual(row['content_timestamp']['time'], content_time.isoformat())
                    self.assertEqual(row['content_timestamp']['integrity'], 'unknown')
                    self.assertIsNone(row['content_timestamp']['trusted'])
                    self.assertFalse(row['content_timestamp']['validation_completed'])
                if signature_ts:
                    self.assertEqual(row['signature_timestamp']['time'], signature_time.isoformat())
                    self.assertEqual(row['signature_timestamp']['integrity'], 'valid')
                    self.assertFalse(row['signature_timestamp']['trusted'])
                self.assertNotIn('timestamp', row, 'Ambiguous aggregate timestamp field must not return')

    def test_document_timestamp_and_unsupported_time_attributes_are_not_absence(self):
        moment = datetime(2026, 1, 2, 8, 3, tzinfo=timezone.utc)
        row = CHECK._status_record(SimpleNamespace(timestamp=moment, intact=True, valid=True,
                                                   trusted=None), document_timestamp=True)
        self.assertEqual(row['document_timestamp']['presence'], 'present')
        self.assertEqual(row['document_timestamp']['time'], moment.isoformat())
        self.assertIsNone(row['document_timestamp']['trusted'])
        self.assertEqual(row['content_timestamp']['presence'], 'not_applicable')
        self.assertEqual(row['signature_timestamp']['presence'], 'not_applicable')
        self.assertIsNone(row['signer_reported_time'])
        unsupported = CHECK._status_record(SimpleNamespace(intact=True, valid=True), document_timestamp=False)
        self.assertEqual(unsupported['content_timestamp']['presence'], 'unknown')
        self.assertEqual(unsupported['signature_timestamp']['presence'], 'unknown')

    def test_precalculation_failure_is_attempted_but_not_performed_or_completed(self):
        source = make_signature_pdf(self.root / 'signed.pdf', populated=True)
        backend = self.backend_for(source, error=NotImplementedError('Synthetic unsupported algorithm; no math'))
        with mock.patch.object(CHECK, '_load_backend', return_value=backend):
            report = CHECK.check(source)
        self.assertEqual(report['status'], 'not_verified')
        self.assertTrue(report['cryptographic_validation_attempted'])
        self.assertFalse(report['cryptographic_validation_performed'])
        self.assertFalse(report['cryptographic_validation_completed'])
        row = report['signatures'][0]
        self.assertTrue(row['validation_attempted'])
        self.assertFalse(row['backend_returned'])
        self.assertFalse(row['validation_completed'])
        self.assertFalse(row['cryptographic_validation_performed'])
        self.assertEqual(report['validation_counts']['attempted'], 1)
        self.assertEqual(report['validation_counts']['completed'], 0)
        self.assertIs(CHECK.validate_report(source, report), report)

    def test_returned_partial_results_are_preserved_without_claiming_full_completion(self):
        source = make_signature_pdf(self.root / 'signed.pdf', populated=True)
        status = SimpleNamespace(intact=True, valid=None, trusted=None,
                                 timestamp_validity=None, content_timestamp_validity=None)
        with mock.patch.object(CHECK, '_load_backend', return_value=self.backend_for(source, status=status)):
            report = CHECK.check(source)
        self.assertEqual(report['status'], 'partially_checked')
        self.assertTrue(report['cryptographic_validation_attempted'])
        self.assertTrue(report['cryptographic_validation_performed'])
        self.assertFalse(report['cryptographic_validation_completed'])
        row = report['signatures'][0]
        self.assertTrue(row['backend_returned'])
        self.assertEqual(row['integrity'], 'unknown')
        self.assertTrue(row['intact'])
        self.assertIsNone(row['signature_math_valid'])
        self.assertIs(CHECK.validate_report(source, report), report)

    def test_backend_return_without_math_results_does_not_claim_performed(self):
        source = make_signature_pdf(self.root / 'signed.pdf', populated=True)
        status = SimpleNamespace(intact=None, valid=None, trusted=None)
        with mock.patch.object(CHECK, '_load_backend', return_value=self.backend_for(source, status=status)):
            report = CHECK.check(source)
        self.assertTrue(report['signatures'][0]['backend_returned'])
        self.assertTrue(report['cryptographic_validation_attempted'])
        self.assertFalse(report['cryptographic_validation_performed'])
        self.assertFalse(report['cryptographic_validation_completed'])
        self.assertEqual(report['status'], 'not_verified')
        self.assertIs(CHECK.validate_report(source, report), report)

    def test_report_binding_rejects_missing_stale_and_forged_absence(self):
        unsigned = make_scan_pdf(self.root / 'unsigned.pdf').path
        signed = make_signature_pdf(self.root / 'signed.pdf', populated=True)
        ordinary = CHECK.check(unsigned)
        self.assertIs(CHECK.validate_report(unsigned, ordinary), ordinary)
        with self.assertRaises(CHECK.SignatureReportError):
            CHECK.validate_report(unsigned, None)
        stale = copy.deepcopy(ordinary)
        stale['original_sha256'] = '0' * 64
        with self.assertRaises(CHECK.SignatureReportError):
            CHECK.validate_report(unsigned, stale)
        forged = copy.deepcopy(ordinary)
        forged['original_filename'] = signed.name
        forged['original_sha256'] = sha(signed.read_bytes())
        with self.assertRaises(CHECK.SignatureReportError):
            CHECK.validate_report(signed, forged)
        incomplete = copy.deepcopy(ordinary)
        incomplete.pop('validation_counts')
        with self.assertRaises(CHECK.SignatureReportError):
            CHECK.assert_report_structure(incomplete, sha(unsigned.read_bytes()))

    def test_report_binding_checks_real_kind_and_detects_source_change(self):
        source = make_scan_pdf(self.root / 'source.pdf').path
        report = CHECK.check(source)
        forged = copy.deepcopy(report)
        forged['source_kind'] = 'image'
        with self.assertRaises(CHECK.SignatureReportError):
            CHECK.validate_report(source, forged)
        source.write_bytes(source.read_bytes() + b'\n% synthetic later modification\n')
        with self.assertRaises(CHECK.SignatureReportError):
            CHECK.validate_report(source, report)

    def test_pdf_with_image_extension_is_still_checked_as_pdf(self):
        original = make_scan_pdf(self.root / 'source.pdf').path
        misnamed = self.root / 'source.png'
        misnamed.write_bytes(original.read_bytes())
        report = CHECK.check(misnamed)
        self.assertEqual(report['source_kind'], 'pdf')
        self.assertEqual(report['status'], 'skipped')
        self.assertEqual(report['detection']['status'], 'not_present')
        self.assertIs(CHECK.validate_report(misnamed, report), report)

    def test_completed_results_bind_and_report_flags_cannot_be_invented(self):
        source = make_signature_pdf(self.root / 'signed.pdf', populated=True)
        for intact, integrity in [(True, 'valid'), (False, 'invalid')]:
            with self.subTest(integrity=integrity):
                status = SimpleNamespace(intact=intact, valid=True, trusted=False,
                    coverage=SimpleNamespace(name='ENTIRE_FILE'),
                    content_timestamp_validity=None, timestamp_validity=None)
                with mock.patch.object(CHECK, '_load_backend', return_value=self.backend_for(source, status=status)):
                    report = CHECK.check(source)
                self.assertEqual(report['status'], 'checked')
                self.assertTrue(report['cryptographic_validation_attempted'])
                self.assertTrue(report['cryptographic_validation_performed'])
                self.assertTrue(report['cryptographic_validation_completed'])
                self.assertEqual(report['signatures'][0]['integrity'], integrity)
                self.assertIs(CHECK.validate_report(source, report), report)
                forged = copy.deepcopy(report)
                forged['signatures'][0]['intact'] = None
                forged['signatures'][0]['signature_math_valid'] = None
                with self.assertRaises(CHECK.SignatureReportError):
                    CHECK.assert_report_structure(forged, sha(source.read_bytes()))

    def test_malformed_populated_candidate_remains_visible_and_unverified(self):
        for label, value in [('missing', 'null'), ('short', '[0 10]')]:
            with self.subTest(case=label):
                source = make_signature_pdf(self.root / f'populated-{label}.pdf', populated=True)
                altered = self.root / f'malformed-{label}.pdf'
                with fitz.open(source) as doc:
                    widget = next(doc[0].widgets())
                    sig_ref = int(doc.xref_get_key(widget.xref, 'V')[1].split()[0])
                    doc.xref_set_key(sig_ref, 'ByteRange', value)
                    doc.save(altered)
                with mock.patch.object(CHECK, '_load_backend', side_effect=ImportError('Synthetic unavailable backend')):
                    report = CHECK.check(altered)
                self.assertEqual(report['detection']['status'], 'malformed')
                self.assertEqual(report['detection']['count'], 1)
                self.assertTrue(report['detection']['candidates'][0]['issues'])
                self.assertEqual(report['status'], 'not_verified')
                self.assertFalse(report['cryptographic_validation_performed'])
                self.assertIs(CHECK.validate_report(altered, report), report)


if __name__ == '__main__':
    unittest.main(verbosity=2)
