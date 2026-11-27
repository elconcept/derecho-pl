#!/usr/bin/env python3
"""Validate approved MODEL content, render clean Markdown, stage and seal a bundle.

This helper performs no OCR and no semantic fact extraction. MODEL authors the
source-grounded content and review ledger. PDF QA is executed afresh before seal.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unicodedata
import zipfile

sys.dont_write_bytecode = True

SCHEMA = Path(__file__).resolve().parent.parent / "references/document.schema.json"
PROTECTED_TYPES = {"signature", "signature_field", "stamp", "handwriting", "table", "equation"}
SAFE_ROLES = {"facility_contact", "survey_invitation", "facility_administration", "routine_media_instructions"}
FURNITURE_TYPES = {"header", "footer", "logo"}
VISUAL_TYPES = {"signature", "signature_field", "stamp", "handwriting", "figure", "logo"}
CONTENT_CONTRACT = "model-document-2"
PROTECTED_ROLES = {
    "department", "encounter_time", "creation_time", "print_time", "export_time",
    "signature_time", "author", "signatory", "professional_id", "patient_id",
    "document_id", "revision", "stamp_identity", "signature_state", "medical_result",
    "specimen_time", "other_evidence", "document_status",
}
PROTECTED_TEXT = re.compile(
    r"(?i)(?:\b(?:PESEL|NPWZ|PWZ|EDM|podpis\w*|piecz[ęe][cć]\w*|"
    r"wydruk\w*|utworzon\w*|wygenerowan\w*|autoryzac\w*|wersj\w*|"
    r"wizy[tc]\w*|lek\.?|lekarz\w*|sygn\.?|anulowan\w*|niezatwierdzon\w*|"
    r"nieautoryzowan\w*|robocz\w*|skorygowan\w*|PLT|KREATYNINA|PESEL)\b|"
    r"\bpacjent(?:ka)?\s*[:=]|\b(?:[12]\d{3}[-/.](?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])|"
    r"(?:0?[1-9]|[12]\d|3[01])[-/.](?:0?[1-9]|1[0-2])[-/.](?:\d{2}|[12]\d{3}))\b|\b\d{1,2}:\d{2}\b)"
)


class BundleError(ValueError):
    pass


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"),
                      parse_constant=lambda x: (_ for _ in ()).throw(BundleError("Non-finite JSON: " + x)))


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalized(text):
    """Comparison only: do not fold case, punctuation, diacritics or digits."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def content_hash(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")).hexdigest()


def require(condition, message):
    if not condition:
        raise BundleError(message)


def safe_stem(filename):
    stem = Path(filename).stem
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", stem).strip(" .")
    return (stem or "dokument")[:150]


def valid_bbox(bbox, label):
    require(len(bbox) == 4 and all(isinstance(x, (int, float)) and not isinstance(x, bool)
                                 and math.isfinite(x) for x in bbox), label + ": bbox must be four finite numbers")
    x0, y0, x1, y1 = bbox
    require(0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1, label + ": invalid bbox bounds/order")


def inside(child, parent):
    eps = 1e-5
    return child[0] >= parent[0]-eps and child[1] >= parent[1]-eps and child[2] <= parent[2]+eps and child[3] <= parent[3]+eps


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def is_protected(block):
    strings = [block["text"], block.get("visual_description", "")]
    strings += [x["text"] for x in block.get("lines", [])]
    for cell in block.get("table", {}).get("cells", []):
        strings.extend([cell["text"], cell.get("visual_description", "")])
    return (block["type"] in PROTECTED_TYPES
            or bool(set(block.get("evidence_roles", [])).intersection(PROTECTED_ROLES))
            or bool(PROTECTED_TEXT.search(" ".join(strings))))


def content_chunks(page):
    chunks = []
    for block in page["blocks"]:
        if "lines" in block:
            require(normalized(" ".join(x["text"] for x in block["lines"])) == normalized(block["text"]),
                    block["id"] + ": lines do not preserve complete block text")
        if "table" in block:
            cells = sorted(block["table"]["cells"], key=lambda x: (x["row"], x["column"]))
            require(normalized(" ".join(c["text"] for c in cells)) == normalized(block["text"]),
                    block["id"] + ": cell text does not preserve full table text")
        # All representations have been checked independently above. Cells are
        # canonical when present; their relationships drive the Markdown output.
        if "table" in block:
            chunks.extend(c["text"] for c in cells if normalized(c["text"]))
        elif "lines" in block:
            chunks.extend(x["text"] for x in block["lines"] if normalized(x["text"]))
        elif normalized(block["text"]):
            chunks.append(block["text"])
    return chunks


def assert_text_coverage(page, expected_text):
    """Account for exact contiguous chunks and multiplicity, even when PDF stream order differs.

    Geometry/order is independently checked by pdf_pipeline. A Counter-only match
    is deliberately insufficient here; each whole line/block must occur intact.
    """
    remaining = normalized(expected_text)
    chunks = sorted((normalized(x) for x in content_chunks(page)), key=len, reverse=True)
    for chunk in chunks:
        # Whitespace boundaries also prevent matching '112' inside '1112'.
        pattern = r"(?<!\S)" + re.escape(chunk) + r"(?!\S)"
        match = re.search(pattern, remaining)
        require(match is not None, f"page {page['page_number']}: missing or reordered source chunk: {chunk[:100]!r}")
        remaining = remaining[:match.start()] + " " * len(match.group()) + remaining[match.end():]
    require(not remaining.strip(), f"page {page['page_number']}: layer expected_text contains unaccounted source text: {remaining.strip()[:100]!r}")


def validate_content(document, review, plan=None):
    import jsonschema
    jsonschema.Draft202012Validator(read_json(SCHEMA)).validate(document)
    source = document["source"]
    require(Path(source["filename"]).name == source["filename"] and not re.search(r"[\x00-\x1f]", source["filename"]),
            "Original filename must be a literal safe basename without control characters")
    count = source["page_count"]
    require([p["page_number"] for p in document["pages"]] == list(range(1, count+1)), "Original page coverage/order is incomplete")
    require(isinstance(review.get("source_sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", review["source_sha256"]),
            "Review requires the original source SHA-256; process hashes belong in LOG")
    from check_signatures import assert_report_structure
    assert_report_structure(review.get("signature_report"), review["source_sha256"], expected_kind=source["kind"])
    require(review.get("document_sha256") == content_hash(document), "Content changed after review; repeat affected review and bind its hash")
    if plan is not None:
        require(review.get("layer_plan_sha256") == content_hash(plan), "Layer plan changed after review")
    require(review.get("complete") is True and review.get("unresolved_questions") == [], "Outstanding human review blocks finalization")
    checks = review.get("page_checks", [])
    require([p.get("page") for p in checks] == list(range(1, count+1)), "Missing page review records")
    for check in checks:
        require(all(check.get(k) is True for k in ("image_reviewed", "transcription_verified", "geometry_verified")),
                f"Page {check.get('page')}: visual/transcription/geometry review incomplete")
    decisions = review.get("blocks", {})
    require(isinstance(decisions, dict), "review.blocks must be an object keyed by block ID")
    seen = {}
    included_facilities = set()
    if plan is not None:
        require(len(plan.get("pages", [])) == count, "Layer plan page count differs from source")
    for page in document["pages"]:
        content_chunks(page)  # Mandatory even in validate without an OCR plan.
        require([b["order"] for b in page["blocks"]] == list(range(1, len(page["blocks"])+1)), "Block reading order must be explicit and complete")
        require(page["page_kind"] != "blank" or not page["blocks"], "A blank page cannot contain unaccounted blocks")
        require(page["page_kind"] == "blank" or bool(page["blocks"]), "Nonblank page needs source blocks")
        for block in page["blocks"]:
            bid = block["id"]
            require(bid not in seen, "Duplicate block ID: " + bid)
            require(int(bid.split('-')[0][1:]) == page["page_number"], "Block ID references wrong source page")
            valid_bbox(block["bbox"], bid)
            if "visual_description" in block:
                require(nonempty(block["visual_description"]), bid + ": visual description cannot be whitespace")
            require(nonempty(block["text"]) or nonempty(block.get("visual_description")), bid + ": source element has no emitted content or description")
            if block["type"] in VISUAL_TYPES:
                require(nonempty(block.get("visual_description")), bid + ": visual element requires a source-grounded description/state")
            for line in block.get("lines", []):
                valid_bbox(line["bbox"], bid + " line")
                require(inside(line["bbox"], block["bbox"]), bid + ": line lies outside its block")
            if "table" in block:
                table = block["table"]
                require(block["type"] == "table", bid + ": table structure on non-table block")
                occupancy = set()
                for cell in table["cells"]:
                    if "visual_description" in cell:
                        require(nonempty(cell["visual_description"]), bid + ": cell description cannot be whitespace")
                    valid_bbox(cell["bbox"], bid + " cell")
                    require(inside(cell["bbox"], block["bbox"]), bid + ": cell outside table bbox")
                    for row in range(cell["row"], cell["row"]+cell.get("rowspan", 1)):
                        for col in range(cell["column"], cell["column"]+cell.get("colspan", 1)):
                            require(row < table["rows"] and col < table["columns"] and (row,col) not in occupancy,
                                    bid + ": overlapping/out-of-range table cells")
                            occupancy.add((row,col))
                require(len(occupancy) == table["rows"]*table["columns"], bid + ": table cells do not cover blank and filled positions")
            require(bid in decisions, "Missing review for " + bid)
            decision = decisions[bid]
            status = decision.get("status")
            require(status in {"verified", "user_verified", "source_illegible_accepted"}, "Unresolved block: " + bid)
            if status != "verified":
                require(nonempty(decision.get("question")) and nonempty(decision.get("answer")), bid + ": user resolution not recorded")
            action = decision.get("md_action")
            require(action in {"include", "omit_boilerplate", "deduplicate_furniture"}, "Unknown Markdown disposition for " + bid)
            roles = set(block.get("evidence_roles", []))
            if action != "include":
                require(nonempty(decision.get("reason")), bid + ": omission requires a logged reason")
                require(not is_protected(block), bid + ": protected evidence cannot be omitted")
                if action == "omit_boilerplate":
                    require(bool(roles) and roles <= SAFE_ROLES or block["type"] == "logo" and not block["text"].strip(),
                            bid + ": only classified routine contact/survey/decorative logo may be omitted")
                else:
                    target = seen.get(decision.get("duplicate_of"))
                    require(target is not None and decisions[target["id"]]["md_action"] == "include",
                            bid + ": repetition must reference an earlier INCLUDED block")
                    require(block["type"] in FURNITURE_TYPES and target["type"] in FURNITURE_TYPES
                            and not is_protected(target), bid + ": both repetition endpoints must be unprotected page furniture")
                    require(block["text"] == target["text"] and block.get("visual_description", "") == target.get("visual_description", ""),
                            bid + ": repeated furniture contains different source information")
            if "facility_identity" in roles and action == "include":
                included_facilities.add(block["text"])
            seen[bid] = block
        if plan is not None:
            layer_page = plan["pages"][page["page_number"]-1]
            require(layer_page.get("page") == page["page_number"], "Layer plan page mapping differs")
            assert_text_coverage(page, layer_page["expected_text"])
    require(set(decisions) == set(seen), "Review contains missing or extra block IDs")
    if any("facility_identity" in b.get("evidence_roles", []) for b in seen.values()):
        require(bool(included_facilities), "Markdown lost all facility identity")
    require(review.get("md_profile", "compact") in {"compact", "legacy_pages"}, "Unknown Markdown profile")
    included = [bid for bid in seen if decisions[bid]["md_action"] == "include"]
    if "md_order" in review:
        order = review["md_order"]
        require(isinstance(order,list) and all(isinstance(x,str) for x in order) and len(order)==len(included)
                and set(order)==set(included), "Markdown reordering must be a permutation of every included source block")
    for bid in included:
        require(nonempty(block_markdown(seen[bid])), bid + ": include would emit no source content")
    return {"pages": count, "blocks": len(seen), "omissions": sum(d["md_action"] != "include" for d in decisions.values()),
            "validation_scope":"content_and_review" if plan is None else "content_review_and_plan"}


def table_markdown(block):
    table = block["table"]
    by_start = {(c["row"],c["column"]): c for c in table["cells"]}
    simple = all(c.get("rowspan",1) == c.get("colspan",1) == 1 for c in table["cells"])
    headers = {(c["row"],c["column"]) for c in table["cells"] if c.get("header")}
    first_row = {(0,c) for c in range(table["columns"])}
    if simple and (not headers or headers == first_row):
        def value(cell):
            text = cell["text"].strip()
            if cell.get("visual_description"):
                text += (" " if text else "") + "[" + cell["visual_description"].strip() + "]"
            return html.escape(text,quote=False).replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")
        def row(n):
            return "|" + "|".join(value(by_start[n,c]) for c in range(table["columns"])) + "|"
        # Empty GFM headings preserve a genuinely headerless source table.
        result = [row(0) if headers else "|" + "|".join("" for _ in range(table["columns"])) + "|",
                  "|" + "|".join("---" for _ in range(table["columns"])) + "|"]
        result.extend(row(n) for n in range(1 if headers else 0,table["rows"]))
        return "\n".join(result)
    rows = ["<table>"]
    for row in range(table["rows"]):
        parts = ["<tr>"]
        for col in range(table["columns"]):
            cell = by_start.get((row,col))
            if cell is None:
                continue
            tag = "th" if cell.get("header") else "td"
            attrs = "".join(f' {k}="{cell[k]}"' for k in ("rowspan","colspan") if cell.get(k,1) > 1)
            text = cell["text"]
            if cell.get("visual_description"):
                text += (" " if text else "") + "[" + cell["visual_description"].strip() + "]"
            parts.append(f"<{tag}{attrs}>{html.escape(text).replace(chr(10), '<br>')}</{tag}>")
        rows.append("".join(parts) + "</tr>")
    return "\n".join(rows + ["</table>"])


def block_markdown(block):
    parts = []
    if nonempty(block.get("visual_description")):
        parts.append("[" + block["visual_description"].strip() + "]")
    if "table" in block:
        parts.append(table_markdown(block))
    elif nonempty(block["text"]):
        parts.append(block["text"].strip())
    return "\n".join(parts)


def markdown(document, review):
    name = document["source"]["filename"]
    count = document["source"]["page_count"]
    compact = review.get("md_profile", "compact") == "compact"
    safe_name = re.sub(r"([\\`*_{}\[\]<>#])", r"\\\1", name)
    output = [f"# {safe_name}\n\nStrony: {count}"] if compact else []
    by_id = {b["id"]:(p,b) for p in document["pages"] for b in p["blocks"]}
    order = review.get("md_order", [bid for bid in by_id if review["blocks"][bid]["md_action"] == "include"])
    entries = [(by_id[bid][0],by_id[bid][1]) for bid in order]
    pages_with_content = {p["page_number"] for p,_ in entries}
    empty = [(p,None) for p in document["pages"] if p["page_number"] not in pages_with_content]
    if "md_order" in review:
        entries.extend(empty)
    else:
        entries.extend(empty)
        entries.sort(key=lambda item:(item[0]["page_number"],item[1]["order"] if item[1] else 0))
    previous = None
    for page, block in entries:
        number = page["page_number"]
        if number != previous:
            output.append(f"[s. {number}]" if compact else f"==== {name} (Page {number}/{count}) ====")
            previous = number
        if block is not None:
            output.append(block_markdown(block))
        elif page["page_kind"] == "blank":
            output.append("[Pusta strona.]")
    return "\n\n".join(output).rstrip() + "\n"


def _binding_summary(binding):
    return {key: binding[key] for key in
            ("actual_kind", "input_sha256", "source_sha256", "original_filename", "page_count", "pages", "frames", "binding")
            if key in binding}


def verify_bundle_inputs(source, base_pdf, searchable, document, review, plan, inventory=None):
    """The same complete causal chain is mandatory at BOTH release gates."""
    from pdf_pipeline import qa, verify_source_base
    from content_geometry import verify_document_geometry
    from check_signatures import validate_report
    summary = validate_content(document, review, plan)
    require(source.name == document["source"]["filename"], "Filename differs from original source")
    require(sha256(source) == review["source_sha256"], "Original source changed after review")
    require(sha256(base_pdf) == plan["source_sha256"], "Layer plan base PDF has changed")
    binding = verify_source_base(source, base_pdf, expected_kind=document["source"]["kind"], inventory=inventory)
    require(binding["page_count"] == document["source"]["page_count"], "Original and JSON page counts differ")
    validate_report(source, review["signature_report"])
    pdf_qa = qa(base_pdf, searchable, plan)
    require(pdf_qa.get("ok") is True, "PDF QA failed: " + json.dumps(pdf_qa.get("errors", []), ensure_ascii=False))
    geometry = verify_document_geometry(document, searchable)
    return {"content_validation": summary, "source_binding": _binding_summary(binding),
            "pdf_qa": pdf_qa, "content_geometry": geometry}


LOG_PREFIX = "# LOG\n\n## Zweryfikowany rdzeń\n\n"
DELIVERY_MARKER = "\n\n## Dostarczenie\n\n"


def json_fence(value):
    return "```json\n" + json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n```"


def _parse_fence(text):
    require(text.startswith("```json\n") and text.endswith("\n```"), "LOG section is not a complete JSON record")
    return json.loads(text[8:-4], parse_constant=lambda x: (_ for _ in ()).throw(BundleError("Non-finite LOG value")))


def validate_delivery(delivery):
    require(isinstance(delivery, dict) and set(delivery) == {"events"} and isinstance(delivery["events"], list),
            "Delivery record must contain a structured events array")
    for event in delivery["events"]:
        require(isinstance(event, dict), "Delivery event must be an object")
        require(set(event) <= {"provider", "status", "recorded_at", "folder_id", "folder_url", "files", "note"},
                "Unknown delivery event field")
        require(event.get("provider") == "google_drive" and event.get("status") in {"verified", "partial", "failed"},
                "Delivery event provider/status invalid")
        require(nonempty(event.get("recorded_at")), "Delivery event timestamp missing")
        if event["status"] != "failed":
            require(nonempty(event.get("folder_id")) and nonempty(event.get("folder_url")), "Delivery folder identity missing")
        require(isinstance(event.get("files", []), list), "Delivery files must be a list")
        for file in event.get("files", []):
            require(isinstance(file, dict) and set(file) <= {"path", "file_id", "size_bytes", "sha256"},
                    "Invalid delivery file record")
            require(nonempty(file.get("path")) and nonempty(file.get("file_id")), "Delivery file identity missing")
            require(not Path(file["path"]).is_absolute() and ".." not in Path(file["path"]).parts,
                    "Unsafe delivery file path")
            if "size_bytes" in file:
                require(isinstance(file["size_bytes"], int) and not isinstance(file["size_bytes"], bool)
                        and file["size_bytes"] >= 0, "Invalid delivery file size")
            if "sha256" in file:
                require(isinstance(file["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", file["sha256"]),
                        "Invalid delivery file hash")
        if "note" in event:
            require(isinstance(event["note"], str), "Delivery note must be text")
    return delivery


def parse_log(path):
    text = Path(path).read_text(encoding="utf-8").rstrip("\n")
    require(text.startswith(LOG_PREFIX) and text.count(DELIVERY_MARKER) == 1, "LOG verified core is missing or replaced")
    core, delivery = text[len(LOG_PREFIX):].split(DELIVERY_MARKER)
    core, delivery = _parse_fence(core), _parse_fence(delivery)
    require(isinstance(core, dict) and core.get("content_contract") == CONTENT_CONTRACT, "LOG core contract differs")
    return core, validate_delivery(delivery)


def log_text(core, delivery):
    validate_delivery(delivery)
    return LOG_PREFIX + json_fence(core) + DELIVERY_MARKER + json_fence(delivery) + "\n"


def log_core(directory, document, review, plan, checks):
    artifacts = {}
    for path in sorted(Path(directory).rglob("*")):
        if path.is_file() and path.name != "LOG.md":
            artifacts[path.relative_to(directory).as_posix()] = {"sha256":sha256(path),"bytes":path.stat().st_size}
    return {
        "content_contract": CONTENT_CONTRACT,
        "source_filename": document["source"]["filename"],
        "original_sha256": review["source_sha256"],
        "base_pdf_sha256": plan["source_sha256"],
        "document_sha256": content_hash(document),
        "layer_plan_sha256": content_hash(plan),
        "md_profile": review.get("md_profile", "compact"),
        "review": review,
        **checks,
        "artifacts": artifacts,
        "notes": [
            "MODEL reads source images; helpers perform no OCR.",
            "Raw is the unchanged original; the searchable derivative does not inherit signed original bytes.",
            "LOG and ZIP hashes are deliberately excluded to avoid self-reference."
        ],
    }


def record_delivery(bundle_dir, receipt_path):
    path = Path(bundle_dir).resolve()/"LOG.md"
    core, delivery = parse_log(path)
    receipt = read_json(receipt_path)
    validate_delivery({"events":[receipt]})
    # A receipt cannot rewrite transformation, review, source or QA records.
    delivery["events"].append(receipt)
    path.write_text(log_text(core, delivery), encoding="utf-8")
    return {"ok":True, "delivery_events":len(delivery["events"])}


def stage(source, base_pdf, searchable, document_path, review_path, plan_path, output_dir, inventory_path=None):
    source, base_pdf, searchable = map(lambda p: Path(p).resolve(), (source, base_pdf, searchable))
    document, review, plan = map(read_json, (document_path, review_path, plan_path))
    inventory = read_json(inventory_path) if inventory_path else None
    checks = verify_bundle_inputs(source, base_pdf, searchable, document, review, plan, inventory)
    output_dir = Path(output_dir).resolve()
    require(not output_dir.exists(), "Bundle directory already exists; use a new version rather than overwrite")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    stem = safe_stem(source.name)
    with tempfile.TemporaryDirectory(prefix=".model-bundle-", dir=output_dir.parent) as temp:
        temp = Path(temp)
        (temp/"raw").mkdir()
        shutil.copyfile(source, temp/"raw"/source.name)
        shutil.copyfile(searchable, temp/f"{stem}_searchable.pdf")
        (temp/f"{stem}.json").write_text(json.dumps(document,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
        (temp/f"{stem}.md").write_text(markdown(document,review),encoding="utf-8")
        core = log_core(temp, document, review, plan, checks)
        (temp/"LOG.md").write_text(log_text(core, {"events":[]}), encoding="utf-8")
        require(sha256(temp/"raw"/source.name) == review["source_sha256"], "Raw copy changed")
        shutil.copytree(temp, output_dir)
    return {"ok":True,"bundle_dir":str(output_dir),"stem":stem,**checks["content_validation"]}


def seal(bundle_dir, source, base_pdf, document, review, plan, output_zip, inventory_path=None):
    """Re-run every source/content/PDF binding and verify the canonical LOG core."""
    bundle = Path(bundle_dir).resolve()
    source, base_pdf = Path(source).resolve(), Path(base_pdf).resolve()
    doc, ledger, layer_plan = map(read_json, (document, review, plan))
    stem = safe_stem(doc["source"]["filename"])
    require(source.name == doc["source"]["filename"], "Source filename mismatch")
    allowed = {f"{stem}_searchable.pdf",f"{stem}.md",f"{stem}.json","LOG.md",f"raw/{source.name}"}
    require(bundle.is_dir() and not bundle.is_symlink(), "Bundle must be a regular directory")
    require(all(not p.is_symlink() for p in bundle.rglob("*")), "Symlink in bundle")
    files = [p for p in bundle.rglob("*") if p.is_file()]
    require({p.relative_to(bundle).as_posix() for p in files} == allowed,
            "Bundle must contain only final PDF, MD, JSON, LOG and raw source")
    require(sha256(source) == ledger["source_sha256"] == sha256(bundle/"raw"/source.name), "Source/raw hash mismatch")
    inventory = read_json(inventory_path) if inventory_path else None
    checks = verify_bundle_inputs(source, base_pdf, bundle/f"{stem}_searchable.pdf", doc, ledger, layer_plan, inventory)
    require((bundle/f"{stem}.md").read_text(encoding="utf-8") == markdown(doc,ledger), "Markdown changed after approval")
    require(read_json(bundle/f"{stem}.json") == doc, "JSON changed after approval")
    recorded_core, delivery = parse_log(bundle/"LOG.md")
    expected_core = log_core(bundle, doc, ledger, layer_plan, checks)
    require(recorded_core == expected_core, "LOG verified core differs from current source, review, QA or artifacts")
    # Validate supplied receipt hashes against immutable payloads when recorded.
    for event in delivery["events"]:
        for item in event.get("files",[]):
            known = expected_core["artifacts"].get(item["path"])
            require(item["path"] in allowed, "Receipt references a file outside this bundle")
            if known is not None:
                if "sha256" in item:
                    require(item["sha256"] == known["sha256"], "Receipt has a stale artifact hash")
                if "size_bytes" in item:
                    require(item["size_bytes"] == known["bytes"], "Receipt has a stale artifact size")
    output = Path(output_zip).resolve()
    require(not output.is_relative_to(bundle), "ZIP must be outside bundle")
    require(not output.exists(), "ZIP exists; do not overwrite a released version")
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in sorted(files):
            info=zipfile.ZipInfo(path.relative_to(bundle).as_posix(),date_time=(1980,1,1,0,0,0))
            info.create_system=3
            info.external_attr=0o100644 << 16
            archive.writestr(info,path.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(output) as archive:
        require(archive.testzip() is None and set(archive.namelist()) == allowed, "ZIP integrity verification failed")
    return {"ok":True,"zip":str(output),"sha256":sha256(output),"bytes":output.stat().st_size,"files":len(files)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest="command",required=True)
    h=commands.add_parser("hash")
    h.add_argument("file")
    v=commands.add_parser("validate")
    v.add_argument("--document",required=True);v.add_argument("--review",required=True);v.add_argument("--plan")
    s=commands.add_parser("stage")
    for key in ("source","base-pdf","searchable","document","review","plan","output-dir"):
        s.add_argument("--"+key,required=True)
    s.add_argument("--inventory")
    z=commands.add_parser("seal")
    for key in ("bundle-dir","source","base-pdf","document","review","plan","output-zip"):
        z.add_argument("--"+key,required=True)
    z.add_argument("--inventory")
    d=commands.add_parser("record-delivery")
    d.add_argument("--bundle-dir",required=True);d.add_argument("--receipt",required=True)
    args=parser.parse_args()
    try:
        if args.command=="hash":
            result={"ok":True,"canonical_sha256":content_hash(read_json(args.file))}
        elif args.command=="validate":
            result=validate_content(read_json(args.document),read_json(args.review),read_json(args.plan) if args.plan else None)
            result={"ok":True,**result}
        elif args.command=="stage":
            result=stage(args.source,args.base_pdf,args.searchable,args.document,args.review,args.plan,args.output_dir,args.inventory)
        elif args.command=="record-delivery":
            result=record_delivery(args.bundle_dir,args.receipt)
        else:
            result=seal(args.bundle_dir,args.source,args.base_pdf,args.document,args.review,args.plan,args.output_zip,args.inventory)
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
        return 0
    except Exception as exc:
        print(json.dumps({"ok":False,"error":str(exc)},ensure_ascii=False),file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
