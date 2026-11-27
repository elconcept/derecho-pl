#!/usr/bin/env python3
"""Inspect signatures on the unmodified original; never sign or rewrite it.

No signature is a normal skipped branch. This report is internal evidence for
LOG.md, not a sixth document-bundle deliverable. Exit 0 means a report was
produced, not that a signature is valid. Source/read errors return exit 2.

The optional crypto API follows primary pyHanko documentation inspected during
development (2026-11-27):
https://docs.pyhanko.eu/en/latest/lib-guide/validation/general-api.html
https://docs.pyhanko.eu/en/latest/api-docs/pyhanko.sign.validation.html
https://docs.pyhanko.eu/en/latest/api-docs/pyhanko_certvalidator.html

No trust list or revocation data is fetched. Local roots/CRLs/OCSP responses may
be supplied explicitly. No qualified-signature or legal-validity assessment is
made. A valid hash/signature is kept separate from coverage, changes and trust.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import fitz
from PIL import Image

from pdf_pipeline import detect_signatures


REPORT_SCHEMA = 'model-signature-check-2'


class SignatureReportError(ValueError):
    """The report is incomplete, internally inconsistent, or for another source."""


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _enum(value: Any) -> str | None:
    return None if value is None else str(getattr(value, 'name', value))


def _iso(value: Any) -> str | None:
    return None if value is None else (value.isoformat() if hasattr(value, 'isoformat') else str(value))


def _integrity(status: Any) -> str:
    intact, valid = _bool(getattr(status, 'intact', None)), _bool(getattr(status, 'valid', None))
    if intact is False or valid is False:
        return 'invalid'
    if intact is True and valid is True:
        return 'valid'
    return 'unknown'


def _timestamp_record(ts: Any, *, role: str, presence: str | None = None) -> dict:
    presence = presence or ('present' if ts is not None else 'not_present')
    intact = _bool(getattr(ts, 'intact', None)) if ts is not None else None
    valid = _bool(getattr(ts, 'valid', None)) if ts is not None else None
    performed = intact is not None or valid is not None
    completed = intact is not None and valid is not None
    return {
        'role': role, 'presence': presence,
        'integrity': (_integrity(ts) if ts is not None else
                      ('unknown' if presence == 'unknown' else 'not_applicable')),
        'intact': intact, 'signature_math_valid': valid,
        'validation_performed': performed, 'validation_completed': completed,
        'trusted': _bool(getattr(ts, 'trusted', None)) if ts is not None else None,
        'time': _iso(getattr(ts, 'timestamp', None)) if ts is not None else None,
        'trust_problem': _enum(getattr(ts, 'trust_problem_indic', None)) if ts is not None else None,
    }


def _optional_timestamp(status: Any, attribute: str, role: str) -> dict:
    # An unsupported/missing attribute is unknown, not proof of absence.
    if not hasattr(status, attribute):
        return _timestamp_record(None, role=role, presence='unknown')
    return _timestamp_record(getattr(status, attribute), role=role)


def _certificate(status: Any) -> dict | None:
    cert = getattr(status, 'signing_cert', None)
    if cert is None:
        return None
    result = {}
    for name in ('subject', 'issuer'):
        value = getattr(cert, name, None)
        result[name] = str(getattr(value, 'human_friendly', value)) if value is not None else None
    serial = getattr(cert, 'serial_number', None)
    result['serial_number'] = str(serial) if serial is not None else None
    return result


def _status_record(status: Any, *, document_timestamp: bool) -> dict:
    if status is None:
        raise ValueError('Validator returned no status object')
    integrity = _integrity(status)
    intact = _bool(getattr(status, 'intact', None))
    valid = _bool(getattr(status, 'valid', None))
    performed = intact is not None or valid is not None
    completed = intact is not None and valid is not None
    coverage = _enum(getattr(status, 'coverage', None))
    if integrity != 'valid':
        conclusion = 'integrity_invalid' if integrity == 'invalid' else 'integrity_unknown'
    elif coverage == 'ENTIRE_FILE':
        conclusion = 'integrity_valid_full_file_coverage'
    elif coverage == 'ENTIRE_REVISION':
        conclusion = 'integrity_valid_signed_revision_only'
    else:
        conclusion = 'integrity_valid_coverage_requires_review'
    return {
        'validation_status': 'checked' if completed else ('partially_checked' if performed else 'not_verified'),
        'validation_attempted': True,
        'backend_returned': True,
        'validation_completed': completed,
        'cryptographic_validation_performed': performed,
        'integrity': integrity,
        'intact': intact,
        'signature_math_valid': valid,
        'trusted_in_supplied_context': _bool(getattr(status, 'trusted', None)),
        'trust_problem': _enum(getattr(status, 'trust_problem_indic', None)),
        'coverage': coverage,
        'modification_level': _enum(getattr(status, 'modification_level', None)),
        'docmdp_ok': _bool(getattr(status, 'docmdp_ok', None)),
        'signer_reported_time': None if document_timestamp else _iso(getattr(status, 'signer_reported_dt', None)),
        'signer_reported_time_basis': 'self_reported_unverified',
        'content_timestamp': (_timestamp_record(None, role='content', presence='not_applicable')
                              if document_timestamp else
                              _optional_timestamp(status, 'content_timestamp_validity', 'content')),
        'signature_timestamp': (_timestamp_record(None, role='signature', presence='not_applicable')
                                if document_timestamp else
                                _optional_timestamp(status, 'timestamp_validity', 'signature')),
        'document_timestamp': (_timestamp_record(status, role='document') if document_timestamp
                               else _timestamp_record(None, role='document', presence='not_applicable')),
        'certificate': _certificate(status),
        'conclusion': conclusion,
        'qualified_signature_status': 'not_assessed',
    }


def _blank_signature(number: int) -> dict:
    return {
        'number': number, 'field_name': None, 'kind': None, 'subfilter': None,
        'byte_range': None, 'validation_status': 'not_verified',
        'validation_attempted': False, 'backend_returned': False,
        'validation_completed': False, 'cryptographic_validation_performed': False,
        'integrity': 'unknown', 'intact': None, 'signature_math_valid': None,
        'trusted_in_supplied_context': None, 'trust_problem': None,
        'coverage': None, 'modification_level': None, 'docmdp_ok': None,
        'signer_reported_time': None, 'signer_reported_time_basis': 'self_reported_unverified',
        'content_timestamp': _timestamp_record(None, role='content', presence='unknown'),
        'signature_timestamp': _timestamp_record(None, role='signature', presence='unknown'),
        'document_timestamp': _timestamp_record(None, role='document', presence='unknown'),
        'certificate': None, 'conclusion': 'integrity_unknown',
        'qualified_signature_status': 'not_assessed',
    }


def _image_detection() -> dict:
    return {'status': 'not_applicable', 'count': 0, 'signatures': [], 'candidates': [],
            'issues': [], 'empty_fields': 0, 'cryptographic_validity': 'not_checked'}


def _source_kind(source: Path) -> str:
    try:
        with fitz.open(source) as document:
            if document.is_pdf:
                return 'pdf'
    except Exception:
        pass
    with Image.open(source) as image:
        image.verify()
    return 'image'


def _summarize(report: dict) -> None:
    records = report['signatures']
    counts = {
        'detected_candidates': report['detection']['count'],
        'enumerated': len(records),
        'attempted': sum(r['validation_attempted'] for r in records),
        'completed': sum(r['validation_completed'] for r in records),
        'performed': sum(r['cryptographic_validation_performed'] for r in records),
    }
    report['validation_counts'] = counts
    report['cryptographic_validation_attempted'] = bool(counts['attempted'])
    report['cryptographic_validation_performed'] = bool(counts['performed'])
    report['cryptographic_validation_completed'] = bool(
        counts['detected_candidates'] and report['enumeration_complete'] and
        counts['completed'] == counts['detected_candidates'] and
        report['detection']['status'] == 'present')
    if report['status'] not in {'skipped', 'not_applicable', 'error'}:
        if report['cryptographic_validation_completed']:
            report.update(status='checked', reason_code='validation_results_available')
        elif counts['performed']:
            report.update(status='partially_checked', reason_code='validation_partial')
        else:
            report['status'] = 'not_verified'


def _finish(source: Path, report: dict) -> dict:
    _summarize(report)
    try:
        unchanged = _hash(source) == report['original_sha256']
    except OSError:
        unchanged = False
    report['source_unchanged'] = unchanged
    if not unchanged and report['status'] != 'error':
        report.update(status='error', reason_code='source_changed_during_check')
        report['notes'].append('Original changed during checking; current source state is not established.')
    return report


def _load_backend() -> dict:
    # Optional imports occur only after a signature is actually detected.
    from pyhanko.keys import load_cert_from_pemder
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import validate_pdf_signature, validate_pdf_timestamp
    from pyhanko_certvalidator import ValidationContext
    return {
        'reader': PdfFileReader,
        'context': ValidationContext,
        'load_cert': load_cert_from_pemder,
        'validate_signature': validate_pdf_signature,
        'validate_timestamp': validate_pdf_timestamp,
        'version': importlib.metadata.version('pyhanko'),
    }


def check(source: str | Path, *, trust_roots: list[str | Path] | None = None,
          crls: list[str | Path] | None = None,
          ocsps: list[str | Path] | None = None) -> dict:
    source = Path(source)
    root_paths = [Path(p) for p in (trust_roots or [])]
    crl_paths = [Path(p) for p in (crls or [])]
    ocsp_paths = [Path(p) for p in (ocsps or [])]
    report = {
        'schema_version': REPORT_SCHEMA,
        'original_filename': source.name,
        'original_sha256': None,
        'source_unchanged': False,
        'source_kind': 'unknown',
        'status': 'not_verified',
        'reason_code': 'not_verified',
        'detection': {'status': 'unknown', 'count': 0},
        'enumeration_complete': False,
        'cryptographic_validation_attempted': False,
        'cryptographic_validation_completed': False,
        'cryptographic_validation_performed': False,
        'network_fetching': False,
        'qualified_signature_status': 'not_assessed',
        'trust_context': {'roots_supplied': len(root_paths), 'crls_supplied': len(crl_paths),
                          'ocsps_supplied': len(ocsp_paths), 'revocation_mode': 'soft-fail',
                          'operating_system_roots_used': False},
        'signatures': [],
        'notes': [],
    }
    try:
        report['original_sha256'] = _hash(source)
        kind = _source_kind(source)
        if kind == 'image':
            report.update(source_kind='image', status='not_applicable',
                          reason_code='image_input', enumeration_complete=True,
                          detection=_image_detection())
            report['notes'].append('Embedded PDF signature checking does not apply to an image input.')
            return _finish(source, report)
        report['source_kind'] = 'pdf'
    except Exception as exc:
        report.update(status='error', reason_code='source_read_error')
        report['notes'].append(f'source_read_error: {type(exc).__name__}: {exc}')
        return _finish(source, report)

    report['detection'] = detect_signatures(source)
    presence = report['detection']['status']
    if presence == 'not_present':
        report.update(status='skipped', reason_code='not_present', enumeration_complete=True)
        report['notes'].append('No embedded signature; this is normal and is not a document defect.')
        return _finish(source, report)
    if presence not in {'present', 'malformed'}:
        report['reason_code'] = 'presence_unresolved'
        report['notes'].append('Signature presence could not be established; absence is not inferred.')
        return _finish(source, report)
    if presence == 'malformed':
        report['notes'].append('Populated signature candidate has structural issues; this is not ordinary absence or a finding of forgery.')

    try:
        backend = _load_backend()
    except ImportError:
        report['reason_code'] = 'optional_validator_unavailable'
        report['notes'].append('optional_validator_unavailable: pyHanko is not installed; no cryptographic check was performed.')
        return _finish(source, report)
    except Exception as exc:
        report['reason_code'] = 'optional_validator_unavailable'
        report['notes'].append(f'optional_validator_unavailable: {type(exc).__name__}: {exc}')
        return _finish(source, report)

    report['validator'] = {'name': 'pyHanko', 'version': backend['version']}
    try:
        roots = [backend['load_cert'](str(path)) for path in root_paths]
        crl_data = [path.read_bytes() for path in crl_paths]
        ocsp_data = [path.read_bytes() for path in ocsp_paths]
        # An explicit [] avoids the historical OS/TLS trust-list fallback.
        context = backend['context'](trust_roots=roots, allow_fetching=False,
                                     revocation_mode='soft-fail', crls=crl_data,
                                     ocsps=ocsp_data)
    except Exception as exc:
        report['reason_code'] = 'validation_context_unavailable'
        report['notes'].append(f'validation_context_unavailable: {type(exc).__name__}: {exc}')
        return _finish(source, report)

    if not roots:
        report['notes'].append('No trust anchors supplied; integrity checking does not establish trust or qualified status.')
    report['notes'].append('Offline soft-fail revocation policy: lack of revocation evidence is not proof of non-revocation.')
    try:
        with source.open('rb') as input_file:
            reader = backend['reader'](input_file)
            # The documented property may itself fail on malformed containers.
            # If enumeration fails, report incomplete coverage, never absence.
            signatures = reader.embedded_signatures
            for number, embedded in enumerate(signatures, 1):
                item = _blank_signature(number)
                try:
                    item['field_name'] = str(embedded.field_name)
                    sig_object = embedded.sig_object
                    kind = str(sig_object.get('/Type', '/Sig'))
                    item['kind'] = kind
                    item['subfilter'] = str(sig_object.get('/SubFilter', ''))
                    byte_range = sig_object.get('/ByteRange')
                    item['byte_range'] = [int(n) for n in byte_range] if byte_range is not None else None
                    item['validation_attempted'] = True
                    if kind == '/DocTimeStamp':
                        status = backend['validate_timestamp'](embedded,
                                    validation_context=context, skip_diff=False)
                    else:
                        status = backend['validate_signature'](embedded,
                                    signer_validation_context=context,
                                    ts_validation_context=context, skip_diff=False)
                    # A call is merely an attempt. A return is recorded separately;
                    # performed/completed require concrete mathematical results.
                    item['backend_returned'] = True
                    item.update(_status_record(status, document_timestamp=kind == '/DocTimeStamp'))
                except Exception as exc:
                    # A failure on one signature must not skip the next one.
                    item['error'] = f'{type(exc).__name__}: {exc}'
                report['signatures'].append(item)
            report['enumeration_complete'] = len(report['signatures']) == report['detection']['count']
    except Exception as exc:
        report['reason_code'] = 'signature_enumeration_incomplete'
        report['notes'].append(f'signature_enumeration_incomplete: {type(exc).__name__}: {exc}')

    detected = report['detection']['count']
    if len(report['signatures']) != detected:
        report['notes'].append('Detected and enumerated counts differ; signature inspection coverage is incomplete.')
    if report['reason_code'] == 'not_verified':
        report['reason_code'] = 'validation_did_not_complete'
    return _finish(source, report)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SignatureReportError(message)


def _timestamp_structure(record: Any, role: str) -> None:
    _require(isinstance(record, dict), f'Missing {role} timestamp record')
    required = {'role', 'presence', 'integrity', 'intact', 'signature_math_valid',
                'validation_performed', 'validation_completed', 'trusted', 'time', 'trust_problem'}
    _require(required <= record.keys(), f'Incomplete {role} timestamp record')
    _require(record['role'] == role, f'Wrong timestamp role: {role}')
    presence = record['presence']
    _require(presence in {'present', 'not_present', 'not_applicable', 'unknown'},
             f'Invalid {role} timestamp presence')
    for name in ('intact', 'signature_math_valid', 'trusted'):
        _require(record[name] is None or type(record[name]) is bool,
                 f'Invalid {role} timestamp {name}')
    for name in ('validation_performed', 'validation_completed'):
        _require(type(record[name]) is bool, f'Invalid {role} timestamp {name}')
    _require(record['time'] is None or (isinstance(record['time'], str) and bool(record['time'].strip())),
             f'Invalid {role} timestamp time')
    _require(record['trust_problem'] is None or isinstance(record['trust_problem'], str),
             f'Invalid {role} timestamp trust problem')
    if presence != 'present':
        _require(all(record[name] is None for name in ('intact', 'signature_math_valid', 'trusted', 'time', 'trust_problem')),
                 f'{role} timestamp absence/unknown contains unsupported results')
        _require(not record['validation_performed'] and not record['validation_completed'],
                 f'{role} timestamp absence/unknown claims validation')
        _require(record['integrity'] == ('unknown' if presence == 'unknown' else 'not_applicable'),
                 f'Inconsistent {role} timestamp integrity')
    else:
        intact, valid = record['intact'], record['signature_math_valid']
        expected_integrity = 'invalid' if False in (intact, valid) else (
            'valid' if intact is True and valid is True else 'unknown')
        _require(record['integrity'] == expected_integrity, f'Inconsistent {role} timestamp result')
        _require(record['validation_performed'] == (intact is not None or valid is not None),
                 f'Unsupported {role} timestamp performed flag')
        _require(record['validation_completed'] == (intact is not None and valid is not None),
                 f'Unsupported {role} timestamp completed flag')


def assert_report_structure(report: Any, original_sha256: str,
                            expected_kind: str | None = None) -> dict:
    """Check completeness/internal consistency without reading a source file.

    Call validate_report at BOTH stage and seal to bind this structure to the
    real original. This is not an execution attestation for hand-authored data.
    """
    _require(isinstance(report, dict), 'A source-bound signature_report is required')
    required = {'schema_version', 'original_filename', 'original_sha256', 'source_kind',
                'source_unchanged', 'status', 'reason_code', 'detection', 'enumeration_complete',
                'cryptographic_validation_attempted', 'cryptographic_validation_completed',
                'cryptographic_validation_performed', 'validation_counts', 'network_fetching',
                'qualified_signature_status', 'trust_context', 'signatures', 'notes'}
    _require(required <= report.keys(), 'Incomplete signature_report fields')
    _require(report['schema_version'] == REPORT_SCHEMA, 'Unsupported signature_report schema; regenerate it')
    _require(isinstance(original_sha256, str) and re.fullmatch(r'[0-9a-f]{64}', original_sha256) is not None,
             'Expected original hash is invalid')
    _require(report['original_sha256'] == original_sha256, 'Signature report belongs to a different original hash')
    _require(isinstance(report['original_filename'], str) and bool(report['original_filename'].strip()),
             'Signature report has no original filename')
    _require(report['source_kind'] in {'pdf', 'image'}, 'Unsupported signature report source kind')
    if expected_kind is not None:
        _require(report['source_kind'] == expected_kind, 'Signature report source kind differs')
    _require(report['source_unchanged'] is True, 'Original was not confirmed unchanged during signature checking')
    _require(report['network_fetching'] is False, 'Report does not describe the supported local validation policy')
    _require(report['qualified_signature_status'] == 'not_assessed', 'Unsupported qualified-signature claim')
    _require(report['status'] in {'skipped', 'not_applicable', 'not_verified', 'checked', 'partially_checked'},
             'Signature report is errored or has an invalid status')
    _require(isinstance(report['reason_code'], str) and bool(report['reason_code'].strip()),
             'Signature report requires a reason code')
    _require(isinstance(report['notes'], list) and all(isinstance(n, str) and n.strip() for n in report['notes']),
             'Invalid signature report notes')
    if report['status'] == 'not_verified':
        _require(bool(report['notes']), 'Unverified signatures require an explicit reason')
        _require(report['reason_code'] in {'presence_unresolved', 'optional_validator_unavailable',
                  'validation_context_unavailable', 'signature_enumeration_incomplete',
                  'validation_did_not_complete'}, 'Unverified signature reason is unsupported')

    detection = report['detection']
    _require(isinstance(detection, dict), 'Signature detection snapshot is required')
    _require({'status', 'count', 'candidates', 'signatures', 'issues', 'empty_fields',
              'cryptographic_validity'} <= detection.keys(), 'Incomplete signature detection snapshot')
    _require(detection['status'] in {'not_present', 'present', 'malformed', 'unknown', 'not_applicable'},
             'Invalid signature detection state')
    _require(type(detection['count']) is int and detection['count'] >= 0, 'Invalid signature candidate count')
    _require(type(detection['empty_fields']) is int and detection['empty_fields'] >= 0,
             'Invalid empty signature field count')
    _require(isinstance(detection['candidates'], list) and
             detection['signatures'] == detection['candidates'] and
             len(detection['candidates']) == detection['count'], 'Inconsistent signature candidates')
    _require(isinstance(detection['issues'], list), 'Invalid detection issue list')
    _require(detection['cryptographic_validity'] == 'not_checked', 'Detection is not cryptographic validation')
    if detection['status'] in {'not_present', 'not_applicable'}:
        _require(detection['count'] == 0 and not detection['issues'], 'Absence hides signature candidates or issues')
    if detection['status'] in {'present', 'malformed'}:
        _require(detection['count'] > 0, 'Populated signature state has no candidates')
    for candidate in detection['candidates']:
        _require(isinstance(candidate, dict), 'Invalid signature candidate')
        _require({'field_name', 'type', 'subfilter', 'byte_range', 'contents_sha256',
                  'contents_bytes', 'issues'} <= candidate.keys(), 'Incomplete signature candidate')

    trust = report['trust_context']
    _require(isinstance(trust, dict), 'Missing trust-context scope')
    for key in ('roots_supplied', 'crls_supplied', 'ocsps_supplied'):
        _require(type(trust.get(key)) is int and trust[key] >= 0, f'Invalid trust context {key}')
    _require(trust.get('revocation_mode') == 'soft-fail' and trust.get('operating_system_roots_used') is False,
             'Unsupported trust-context policy')

    records = report['signatures']
    _require(isinstance(records, list), 'Missing per-signature results')
    used_candidates = set()
    for number, item in enumerate(records, 1):
        _require(isinstance(item, dict), 'Invalid per-signature result')
        _require(_blank_signature(number).keys() <= item.keys(), 'Incomplete per-signature result')
        _require(item['number'] == number, 'Per-signature results are missing or duplicated')
        _require(type(item['number']) is int, 'Per-signature number is not an integer')
        for flag in ('validation_attempted', 'backend_returned', 'validation_completed',
                     'cryptographic_validation_performed'):
            _require(type(item[flag]) is bool, f'Invalid per-signature {flag}')
        for flag in ('intact', 'signature_math_valid', 'trusted_in_supplied_context', 'docmdp_ok'):
            _require(item[flag] is None or type(item[flag]) is bool, f'Invalid per-signature {flag}')
        intact, valid = item['intact'], item['signature_math_valid']
        performed = intact is not None or valid is not None
        completed = intact is not None and valid is not None
        _require(item['cryptographic_validation_performed'] == performed and item['validation_completed'] == completed,
                 'Per-signature performed/completed flags lack supporting results')
        _require(not (performed or item['backend_returned']) or item['validation_attempted'],
                 'Per-signature result was not attempted')
        _require(not performed or item['backend_returned'], 'Cryptographic results precede backend return')
        expected_status = 'checked' if completed else ('partially_checked' if performed else 'not_verified')
        _require(item['validation_status'] == expected_status, 'Per-signature status contradicts completed checks')
        integrity = 'invalid' if False in (intact, valid) else ('valid' if intact is True and valid is True else 'unknown')
        _require(item['integrity'] == integrity, 'Per-signature integrity contradicts raw results')
        conclusion = ('integrity_invalid' if integrity == 'invalid' else
                      'integrity_unknown' if integrity == 'unknown' else
                      'integrity_valid_full_file_coverage' if item['coverage'] == 'ENTIRE_FILE' else
                      'integrity_valid_signed_revision_only' if item['coverage'] == 'ENTIRE_REVISION' else
                      'integrity_valid_coverage_requires_review')
        _require(item['conclusion'] == conclusion, 'Per-signature conclusion contradicts available evidence')
        _require(item['qualified_signature_status'] == 'not_assessed', 'Unsupported per-signature qualification')
        _require(item['signer_reported_time_basis'] == 'self_reported_unverified', 'Signer-reported time is not trusted timestamp evidence')
        _require(item['signer_reported_time'] is None or (isinstance(item['signer_reported_time'], str) and item['signer_reported_time'].strip()),
                 'Invalid signer-reported time')
        for role in ('content', 'signature', 'document'):
            _timestamp_structure(item[f'{role}_timestamp'], role)
        if performed:
            matching = [index for index, candidate in enumerate(detection['candidates'])
                        if index not in used_candidates and candidate['byte_range'] == item['byte_range']
                        and candidate['type'] == item['kind'] and candidate['subfilter'] == item['subfilter']]
            _require(bool(matching), 'Per-signature result is not tied to a detected original candidate')
            used_candidates.add(matching[0])
    if records:
        validator = report.get('validator')
        _require(isinstance(validator, dict) and validator.get('name') == 'pyHanko' and
                 isinstance(validator.get('version'), str) and bool(validator['version'].strip()),
                 'Per-signature results require validator identity/version')

    for flag in ('enumeration_complete', 'cryptographic_validation_attempted',
                 'cryptographic_validation_completed', 'cryptographic_validation_performed'):
        _require(type(report[flag]) is bool, f'Invalid report {flag}')
    if report['enumeration_complete']:
        _require(len(records) == detection['count'], 'Complete enumeration has missing signatures')
    expected = copy.deepcopy(report)
    _summarize(expected)
    _require(isinstance(report['validation_counts'], dict) and
             set(report['validation_counts']) == set(expected['validation_counts']) and
             all(type(value) is int and value >= 0 for value in report['validation_counts'].values()),
             'Invalid signature validation counters')
    for key in ('validation_counts', 'cryptographic_validation_attempted',
                'cryptographic_validation_completed', 'cryptographic_validation_performed'):
        _require(report[key] == expected[key], f'Inconsistent signature report {key}')
    presence = detection['status']
    if report['source_kind'] == 'image':
        _require(presence == 'not_applicable' and report['status'] == 'not_applicable' and not records,
                 'Image signature handling must be not_applicable')
        _require(report['enumeration_complete'] and report['reason_code'] == 'image_input',
                 'Incomplete image signature scope')
    elif presence == 'not_present':
        _require(report['status'] == 'skipped' and not records, 'Unsigned source must use the normal skipped branch')
        _require(report['enumeration_complete'] and report['reason_code'] == 'not_present',
                 'Incomplete unsigned signature scope')
    else:
        _require(presence != 'not_applicable', 'PDF cannot claim image-only signature handling')
        derived = ('checked' if expected['cryptographic_validation_completed'] else
                   ('partially_checked' if expected['cryptographic_validation_performed'] else 'not_verified'))
        _require(report['status'] == derived, 'Report status contradicts signature evidence')
    return report


def validate_report(original: str | Path, report: Any) -> dict:
    """Bind a complete report to actual source bytes, type and current detection.

    Does not rerun crypto or authenticate arbitrary authorship of the report.
    The host must use the check() result produced before the reviewed ledger.
    """
    original = Path(original)
    try:
        source_hash = _hash(original)
        kind = _source_kind(original)
        assert_report_structure(report, source_hash, expected_kind=kind)
        _require(report['original_filename'] == original.name, 'Signature report filename differs from the original')
        observed = detect_signatures(original) if kind == 'pdf' else _image_detection()
        _require(report['detection'] == observed, 'Signature report detection differs from the actual original')
        _require(_hash(original) == source_hash, 'Original changed during signature-report binding')
    except SignatureReportError:
        raise
    except Exception as exc:
        raise SignatureReportError(f'Cannot bind signature report to original: {type(exc).__name__}: {exc}') from exc
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, help='Internal JSON report for LOG.md assembly')
    parser.add_argument('--trust-root', action='append', default=[], type=Path)
    parser.add_argument('--crl', action='append', default=[], type=Path)
    parser.add_argument('--ocsp', action='append', default=[], type=Path)
    args = parser.parse_args(argv)
    if args.output and args.output.resolve() == args.source.resolve():
        parser.error('--output must not overwrite the original')
    report = check(args.source, trust_roots=args.trust_root, crls=args.crl, ocsps=args.ocsp)
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                dir=args.output.parent, prefix='.signature-report-',
                suffix='.tmp', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(serialized)
        try:
            os.replace(temporary, args.output)
        finally:
            temporary.unlink(missing_ok=True)
    print(serialized, end='')
    return 2 if report['status'] == 'error' else 0


if __name__ == '__main__':
    raise SystemExit(main())
