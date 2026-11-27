"""Content-loss, review-gate and final-package regressions, using synthetic data."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from functools import lru_cache

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parents[1]/"skills/model-ocr/scripts"
sys.path.insert(0,str(SCRIPTS))
import assemble_bundle as bundle
import check_signatures


@lru_cache(maxsize=1)
def unsigned_report():
    import pymupdf as fitz
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/"test.pdf"
        with fitz.open() as pdf:
            pdf.new_page(width=595,height=842)
            pdf.save(path)
        return check_signatures.check(path)


def example():
    blocks=[]
    values=[
        ("SZPITAL TESTOWY","header",["facility_identity"]),
        ("tel. 000 000 000","footer",["facility_contact"]),
        ("Data wydruku: 2024-04-19 09:07","paragraph",["print_time"]),
        ("Podpis lekarza:","signature_field",["signature_state"]),
    ]
    for n,(text,kind,roles) in enumerate(values,1):
        block={"id":f"p001-b{n:03}","order":n,"type":kind,"bbox":[.1,.1*n,.9,.1*n+.04],
               "text":text,"evidence_roles":roles}
        if kind=="signature_field":
            block["visual_description"]="Pole podpisu lekarza: puste."
        blocks.append(block)
    report=copy.deepcopy(unsigned_report())
    digest=report["original_sha256"]
    doc={"source":{"filename":"test.pdf","kind":"pdf","page_count":1},
         "coordinate_system":"normalized-displayed-cropbox-top-left-xyxy",
         "pages":[{"page_number":1,"width_pt":595,"height_pt":842,"page_kind":"text","blocks":blocks}]}
    plan={"schema_version":"model-ocr-layer-plan-1","source_sha256":digest,"review_complete":True,"unresolved":[],
          "pages":[{"page":1,"mode":"keep","expected_text":"\n".join(b["text"] for b in blocks),"lines":[],"search_checks":[]}]}
    ledger={"source_sha256":digest,"signature_report":report,"complete":True,"unresolved_questions":[],
            "page_checks":[{"page":1,"image_reviewed":True,"transcription_verified":True,"geometry_verified":True}],
            "blocks":{b["id"]:{"status":"verified","md_action":"include"} for b in blocks}}
    ledger["blocks"]["p001-b002"].update(md_action="omit_boilerplate",reason="Powtarzalny telefon centrali bez danych dokumentu.")
    bind(doc,ledger,plan)
    return doc,ledger,plan


def bind(doc,ledger,plan):
    ledger["document_sha256"]=bundle.content_hash(doc)
    ledger["layer_plan_sha256"]=bundle.content_hash(plan)


class ContentTests(unittest.TestCase):
    def test_markdown_omits_contact_keeps_print_time_and_blank_signature(self):
        doc,ledger,plan=example()
        bundle.validate_content(doc,ledger,plan)
        md=bundle.markdown(doc,ledger)
        self.assertTrue(md.startswith("# test.pdf\n\nStrony: 1\n\n[s. 1]"))
        self.assertNotIn("000 000 000",md)
        self.assertIn("2024-04-19 09:07",md)
        self.assertIn("Pole podpisu lekarza: puste",md)
        self.assertIn("000 000 000",json.dumps(doc))
        self.assertNotIn("md_action",json.dumps(doc))

    def test_unanswered_question_blocks_finalization(self):
        doc,ledger,plan=example()
        ledger["unresolved_questions"]=[{"page":1,"question":"Czy data to 18 czy 19?"}]
        with self.assertRaises(bundle.BundleError):bundle.validate_content(doc,ledger,plan)

    def test_changed_text_invalidates_previous_review(self):
        doc,ledger,plan=example()
        doc["pages"][0]["blocks"][2]["text"]="Data wydruku: 2024-02-03 08:15"
        with self.assertRaises(bundle.BundleError):bundle.validate_content(doc,ledger,plan)

    def test_print_timestamp_cannot_be_omitted(self):
        doc,ledger,plan=example()
        ledger["blocks"]["p001-b003"].update(md_action="omit_boilerplate",reason="To stopka")
        with self.assertRaises(bundle.BundleError):bundle.validate_content(doc,ledger,plan)

    def test_mixed_contact_and_date_cannot_be_mislabeled_for_omission(self):
        doc,ledger,plan=example()
        doc["pages"][0]["blocks"][1]["text"] += "; Data wydruku: 2024-04-19"
        plan["pages"][0]["expected_text"]="\n".join(b["text"] for b in doc["pages"][0]["blocks"])
        bind(doc,ledger,plan)
        with self.assertRaises(bundle.BundleError):bundle.validate_content(doc,ledger,plan)

    def test_signature_description_cannot_be_omitted(self):
        doc,ledger,plan=example()
        ledger["blocks"]["p001-b004"].update(md_action="omit_boilerplate",reason="Powtorzenie")
        with self.assertRaises(bundle.BundleError):bundle.validate_content(doc,ledger,plan)

    def test_missing_and_extra_pdf_text_rejected(self):
        for suffix in (" EXTRA"," 304"):
            doc,ledger,plan=example()
            plan["pages"][0]["expected_text"]+=suffix
            bind(doc,ledger,plan)
            with self.assertRaises(bundle.BundleError):bundle.validate_content(doc,ledger,plan)

    def test_bbox_and_pipeline_noise_rejected(self):
        for change in ({"bbox":[.9,.1,.1,.2]},{"confidence":.99}):
            doc,ledger,plan=example()
            doc["pages"][0]["blocks"][0].update(change)
            bind(doc,ledger,plan)
            with self.assertRaises(Exception):bundle.validate_content(doc,ledger,plan)

    def test_user_resolution_requires_actual_answer(self):
        doc,ledger,plan=example()
        ledger["blocks"]["p001-b003"]["status"]="user_verified"
        with self.assertRaises(bundle.BundleError):bundle.validate_content(doc,ledger,plan)
        ledger["blocks"]["p001-b003"].update(question="Która data?",answer="Potwierdzam 2024-04-19 09:07 ze skanu.")
        bundle.validate_content(doc,ledger,plan)

    def test_blank_page_still_has_original_page_tag(self):
        doc,ledger,plan=example()
        doc["source"]["page_count"]=2
        doc["pages"].append({"page_number":2,"width_pt":595,"height_pt":842,"page_kind":"blank","blocks":[]})
        ledger["page_checks"].append({"page":2,"image_reviewed":True,"transcription_verified":True,"geometry_verified":True})
        plan["pages"].append({"page":2,"mode":"keep","expected_text":"","lines":[],"search_checks":[]})
        bind(doc,ledger,plan)
        bundle.validate_content(doc,ledger,plan)
        self.assertIn("[s. 2]\n\n[Pusta strona.]",bundle.markdown(doc,ledger))

    def test_table_cells_preserve_relations_and_reject_missing_cell(self):
        doc,ledger,plan=example()
        table={"id":"p001-b005","order":5,"type":"table","bbox":[.1,.5,.9,.6],"text":"PLT 304",
               "table":{"rows":1,"columns":2,"cells":[
                   {"row":0,"column":0,"text":"PLT","bbox":[.1,.5,.5,.6]},
                   {"row":0,"column":1,"text":"304","bbox":[.5,.5,.9,.6]}]}}
        doc["pages"][0]["blocks"].append(table)
        ledger["blocks"][table["id"]]={"status":"verified","md_action":"include"}
        plan["pages"][0]["expected_text"]+="\nPLT 304"
        bind(doc,ledger,plan)
        bundle.validate_content(doc,ledger,plan)
        self.assertIn("|PLT|304|",bundle.markdown(doc,ledger))
        table["table"]["cells"].pop()
        bind(doc,ledger,plan)
        with self.assertRaises(bundle.BundleError):bundle.validate_content(doc,ledger,plan)

    def test_stage_seal_raw_and_exact_final_file_set(self):
        import pymupdf as fitz
        import pdf_pipeline
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            source=tmp/"test.pdf"
            doc,ledger,plan=example()
            with fitz.open() as pdf:
                page=pdf.new_page(width=595,height=842)
                for n,b in enumerate(doc["pages"][0]["blocks"],1):
                    page.insert_text((60,n*75),b["text"],fontsize=10)
                    rect=page.search_for(b["text"])[0]
                    b["bbox"]=[rect.x0/595,rect.y0/842,rect.x1/595,rect.y1/842]
                page.draw_rect(fitz.Rect(170,280,310,315))
                pdf.save(source)
            digest=bundle.sha256(source)
            ledger["source_sha256"]=digest
            ledger["signature_report"]=check_signatures.check(source)
            plan["source_sha256"]=digest
            bind(doc,ledger,plan)
            paths={}
            for name,value in (("document",doc),("review",ledger),("plan",plan)):
                path=tmp/(name+".json");path.write_text(json.dumps(value,ensure_ascii=False),encoding="utf-8");paths[name]=path
            output=tmp/"candidate.pdf"
            pdf_pipeline.build(source,plan,output)
            target=tmp/"bundle"
            bundle.stage(source,source,output,paths["document"],paths["review"],paths["plan"],target)
            zipped=tmp/"bundle.zip"
            bundle.seal(target,source,source,paths["document"],paths["review"],paths["plan"],zipped)
            with zipfile.ZipFile(zipped) as archive:
                self.assertEqual(set(archive.namelist()),{"test_searchable.pdf","test.md","test.json","LOG.md","raw/test.pdf"})
                self.assertEqual(hashlib.sha256(archive.read("raw/test.pdf")).hexdigest(),digest)
                self.assertNotIn("tel. 000",archive.read("test.md").decode())
            (target/"intermediate.png").write_bytes(b"bad")
            with self.assertRaises(bundle.BundleError):
                bundle.seal(target,source,source,paths["document"],paths["review"],paths["plan"],tmp/"bad.zip")


if __name__=="__main__":
    unittest.main()
