"""Acceptance regressions for the confirmed 0.1.0 audit, executed ONLY on corrected code."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import pymupdf as fitz
from test_content_bundle import example, bind

SCRIPTS=Path(__file__).resolve().parents[1]/"skills/model-ocr/scripts"
sys.path.insert(0,str(SCRIPTS))
import assemble_bundle as bundle
import check_signatures
from content_geometry import GeometryError


class Fixture:
    def __init__(self, root, texts=("PLT 304",), rotation=0, crop=False, graphic=False):
        self.root=Path(root);self.source=self.root/"source.pdf"
        self.output=self.root/"searchable.pdf"
        blocks=[]
        with fitz.open() as pdf:
            page=pdf.new_page(width=600,height=800)
            if crop:
                page.set_cropbox(fitz.Rect(20,30,580,770))
            for i,text in enumerate(texts):
                page.insert_text((50,110+i*50),text,fontsize=12)
            if graphic:
                page.draw_polyline([(50,200),(70,180),(65,210),(100,180),(120,205)],color=(0,0,1),width=1)
            page.set_rotation(rotation)
            pdf.save(self.source)
        with fitz.open(self.source) as pdf:
            page=pdf[0]
            words=page.get_text("words",sort=False)
            for n,text in enumerate(texts,1):
                line_words=[w for w in words if abs(w[1]-(110+(n-1)*50-12*1.075))<0.2]
                rect=fitz.Rect(line_words[0][:4])
                for word in line_words[1:]:rect|=fitz.Rect(word[:4])
                rect*=page.rotation_matrix
                b={"id":f"p001-b{n:03}","order":n,"type":"paragraph","text":text,
                   "bbox":[rect.x0/page.rect.width,rect.y0/page.rect.height,rect.x1/page.rect.width,rect.y1/page.rect.height]}
                blocks.append(b)
            if graphic:
                rect=fitz.Rect(45,175,125,215)*page.rotation_matrix
                blocks.append({"id":f"p001-b{len(blocks)+1:03}","order":len(blocks)+1,"type":"signature","text":"",
                               "bbox":[rect.x0/page.rect.width,rect.y0/page.rect.height,rect.x1/page.rect.width,rect.y1/page.rect.height],
                               "visual_description":"Podpis odręczny: nieczytelny.","evidence_roles":["signature_state"]})
            self.doc={"source":{"filename":"source.pdf","kind":"pdf","page_count":1},
                      "coordinate_system":"normalized-displayed-cropbox-top-left-xyxy",
                      "pages":[{"page_number":1,"width_pt":page.rect.width,"height_pt":page.rect.height,
                                "page_kind":"mixed" if graphic else "text","blocks":blocks}]}
            self.plan={"schema_version":"model-ocr-layer-plan-1","source_sha256":bundle.sha256(self.source),
                       "review_complete":True,"unresolved":[],
                       "pages":[{"page":1,"mode":"keep","expected_text":page.get_text("text",sort=True),"lines":[]}]}
        self.review={"source_sha256":bundle.sha256(self.source),"signature_report":check_signatures.check(self.source),
                     "complete":True,"unresolved_questions":[],
                     "page_checks":[{"page":1,"image_reviewed":True,"transcription_verified":True,"geometry_verified":True}],
                     "blocks":{b["id"]:{"status":"verified","md_action":"include"} for b in blocks}}
        shutil.copyfile(self.source,self.output)
        self.paths={k:self.root/(k+".json") for k in ("document","review","plan")}
        self.write()

    def write(self):
        bind(self.doc,self.review,self.plan)
        for key,value in (("document",self.doc),("review",self.review),("plan",self.plan)):
            self.paths[key].write_text(json.dumps(value,ensure_ascii=False),encoding="utf-8")

    def stage(self,name="bundle"):
        self.write()
        target=self.root/name
        bundle.stage(self.source,self.source,self.output,self.paths["document"],self.paths["review"],self.paths["plan"],target)
        return target

    def seal(self,target,name="bundle.zip",base=None):
        self.write()
        return bundle.seal(target,self.source,base or self.source,self.paths["document"],self.paths["review"],self.paths["plan"],self.root/name)

    def table(self):
        block=self.doc["pages"][0]["blocks"][0]
        block["type"]="table"
        with fitz.open(self.source) as pdf:
            page=pdf[0];cells=[]
            for n,w in enumerate(page.get_text("words",sort=False)):
                rect=fitz.Rect(w[:4])*page.rotation_matrix
                cells.append({"row":0,"column":n,"text":w[4],
                              "bbox":[rect.x0/page.rect.width,rect.y0/page.rect.height,rect.x1/page.rect.width,rect.y1/page.rect.height]})
        block["table"]={"rows":1,"columns":len(cells),"cells":cells}
        block["lines"]=[{"text":block["text"],"bbox":block["bbox"][:]}]
        self.write()
        return block


class AuditAcceptanceTests(unittest.TestCase):
    def test_G62_01_all_representations_conflict_rejected_without_plan_and_at_gates(self):
        with tempfile.TemporaryDirectory() as td:
            f=Fixture(td);table=f.table();target=f.stage()
            table["table"]["cells"][1]["text"]="999";f.write()
            for plan in (None,f.plan):
                with self.assertRaisesRegex(bundle.BundleError,"cell text"):
                    bundle.validate_content(f.doc,f.review,plan)
            with self.assertRaisesRegex(bundle.BundleError,"cell text"):f.stage("bad-stage")
            with self.assertRaisesRegex(bundle.BundleError,"cell text"):f.seal(target,"bad.zip")

    def test_G62_01_correct_table_and_units_survive_compact_render(self):
        with tempfile.TemporaryDirectory() as td:
            f=Fixture(td,("PLT 304 10^9/l",));f.table();target=f.stage();f.seal(target)
            md=(target/"source.md").read_text()
            self.assertIn("|PLT|304|10^9/l|",md)
            self.assertNotIn("<table>",md)

    def test_G62_02_foreign_base_rejected_by_direct_seal_and_stage(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/"a").mkdir();(root/"b").mkdir()
            original=Fixture(root/"a",("ORIGINAL 1",));other=Fixture(root/"b",("OTHER 2",))
            # The approved content can be wrong, but a foreign PDF base still cannot be released.
            original.doc=copy.deepcopy(other.doc);original.plan=copy.deepcopy(other.plan)
            original.review["blocks"]=copy.deepcopy(other.review["blocks"]);original.write()
            with self.assertRaisesRegex(Exception,"original|identical|base"):
                bundle.stage(original.source,other.source,other.output,original.paths["document"],original.paths["review"],
                             original.paths["plan"],root/"bad-stage")
            target=root/"manual";(target/"raw").mkdir(parents=True)
            shutil.copyfile(original.source,target/"raw/source.pdf")
            shutil.copyfile(other.output,target/"source_searchable.pdf")
            (target/"source.md").write_text(bundle.markdown(original.doc,original.review))
            (target/"source.json").write_text(json.dumps(original.doc))
            (target/"LOG.md").write_text("arbitrary")
            with self.assertRaisesRegex(Exception,"original|identical|base"):
                original.seal(target,"bad.zip",base=other.source)

    def test_G62_01_swapped_values_between_rows_rejected_by_actual_cell_geometry(self):
        with tempfile.TemporaryDirectory() as td:
            f=Fixture(td,("PLT 304 unitA","OTHER 112 unitB"))
            first,second=f.doc["pages"][0]["blocks"]
            first["type"]="table";first["bbox"][3]=second["bbox"][3]
            first["bbox"][2]=max(first["bbox"][2],second["bbox"][2])
            cells=[]
            with fitz.open(f.source) as pdf:
                page=pdf[0]
                for n,w in enumerate(page.get_text("words",sort=False)):
                    cells.append({"row":n//3,"column":n%3,"text":w[4],
                                  "bbox":[w[0]/600,w[1]/800,w[2]/600,w[3]/800]})
            first["table"]={"rows":2,"columns":3,"cells":cells}
            first["text"]=" ".join(c["text"] for c in cells)
            f.doc["pages"][0]["blocks"]=[first];del f.review["blocks"][second["id"]]
            f.write();target=f.stage();f.seal(target)
            cells[1]["text"],cells[4]["text"]=cells[4]["text"],cells[1]["text"]
            first["text"]=" ".join(c["text"] for c in cells)
            first["lines"]=[{"text":first["text"],"bbox":first["bbox"][:]}]
            f.write()
            with self.assertRaisesRegex(GeometryError,"no PDF occurrence"):f.stage("wrong-values")
            with self.assertRaisesRegex(GeometryError,"no PDF occurrence"):f.seal(target,"wrong-values.zip")
            # Broad declarations cannot legitimize a wrong row/value association.
            value_boxes=[cells[1]["bbox"][:],cells[4]["bbox"][:]]
            x0=min(b[0] for b in value_boxes);x1=max(b[2] for b in value_boxes)
            y0=min(b[1] for b in value_boxes);y1=max(b[3] for b in value_boxes)
            cells[1]["bbox"]=[x0,y0,x1,y1-.5/800]
            cells[4]["bbox"]=[x0,y0+.5/800,x1,y1]
            f.write()
            with self.assertRaisesRegex(GeometryError,"row order"):f.stage("broad-wrong-values")
            with self.assertRaisesRegex(GeometryError,"row order"):f.seal(target,"broad-wrong-values.zip")

    def test_G62_02_declared_type_does_not_override_actual_pdf(self):
        with tempfile.TemporaryDirectory() as td:
            f=Fixture(td);f.doc["source"]["kind"]="image";f.write()
            with self.assertRaises(Exception):f.stage()

    def test_G62_03_wrong_dimensions_and_opposite_corner_fail_both_gates(self):
        for kind in ("dimensions","bbox"):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as td:
                f=Fixture(td);target=f.stage()
                if kind=="dimensions":
                    f.doc["pages"][0].update(width_pt=1,height_pt=2)
                else:f.doc["pages"][0]["blocks"][0]["bbox"]=[.8,.8,.95,.95]
                f.write()
                with self.assertRaises(GeometryError):f.stage("bad-stage")
                with self.assertRaises(GeometryError):f.seal(target,"bad.zip")

    def test_G62_03_repeated_text_requires_distinct_real_occurrences(self):
        with tempfile.TemporaryDirectory() as td:
            f=Fixture(td,("PLT 304","PLT 304"));target=f.stage();f.seal(target)
            f.doc["pages"][0]["blocks"][1]["bbox"]=f.doc["pages"][0]["blocks"][0]["bbox"][:]
            f.write()
            with self.assertRaises(GeometryError):f.stage("bad-stage")
            with self.assertRaises(GeometryError):f.seal(target,"bad.zip")

    def test_G62_03_actual_rotation_and_cropbox_geometry_pass(self):
        for rotation in (0,90,180,270):
            with self.subTest(rotation=rotation),tempfile.TemporaryDirectory() as td:
                f=Fixture(td,("PLT 304","OTHER 112"),rotation=rotation,crop=True)
                target=f.stage();f.seal(target)

    def test_G62_03_overlapping_block_regions_are_not_globally_banned(self):
        with tempfile.TemporaryDirectory() as td:
            f=Fixture(td,("PLT 304","OTHER 112"))
            a,b=f.doc["pages"][0]["blocks"]
            a["bbox"][3]=b["bbox"][3];b["bbox"][1]=a["bbox"][1]
            f.write();target=f.stage();f.seal(target)

    def test_G62_08_empty_visual_include_rejected_description_emits(self):
        with tempfile.TemporaryDirectory() as td:
            f=Fixture(td,(),graphic=True);f.doc["pages"][0]["page_kind"]="image_only"
            target=f.stage();f.seal(target)
            self.assertIn("Podpis odręczny: nieczytelny",(target/"source.md").read_text())
            f.doc["pages"][0]["blocks"][0].pop("visual_description");f.write()
            with self.assertRaisesRegex(bundle.BundleError,"description|content"):f.stage("bad-stage")
            with self.assertRaisesRegex(bundle.BundleError,"description|content"):f.seal(target,"bad.zip")

    def test_G62_09_signature_report_required_and_bound_at_each_gate(self):
        for mode in ("missing","foreign_hash"):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as td:
                f=Fixture(td);target=f.stage()
                if mode=="missing":f.review.pop("signature_report")
                else:f.review["signature_report"]["original_sha256"]="0"*64
                f.write()
                with self.assertRaises(Exception):f.stage("bad-stage")
                with self.assertRaises(Exception):f.seal(target,"bad.zip")

    def test_G62_11_replaced_log_rejected_legal_receipt_allowed(self):
        with tempfile.TemporaryDirectory() as td:
            f=Fixture(td);target=f.stage()
            receipt={"provider":"google_drive","status":"verified","recorded_at":"2026-11-27T12:00:00+01:00",
                     "folder_id":"synthetic","folder_url":"https://drive.google.com/drive/folders/synthetic",
                     "files":[{"path":"source.md","file_id":"synthetic-md","sha256":bundle.sha256(target/"source.md"),
                               "size_bytes":(target/"source.md").stat().st_size}]}
            rp=Path(td)/"receipt.json";rp.write_text(json.dumps(receipt))
            bundle.record_delivery(target,rp)
            f.seal(target,"with-receipt.zip")
            (target/"LOG.md").write_text("# LOG\nEverything is fine.")
            with self.assertRaisesRegex(bundle.BundleError,"LOG"):f.seal(target,"replaced-log.zip")

    def test_G62_11_review_and_qa_cannot_be_removed_from_core(self):
        with tempfile.TemporaryDirectory() as td:
            f=Fixture(td);target=f.stage()
            core,receipt=bundle.parse_log(target/"LOG.md")
            del core["review"]
            (target/"LOG.md").write_text(bundle.log_text(core,receipt))
            with self.assertRaisesRegex(bundle.BundleError,"LOG verified core"):f.seal(target,"missing-review.zip")

    def test_G62_12_dedup_target_must_also_be_unprotected_furniture(self):
        doc,review,plan=example()
        target=doc["pages"][0]["blocks"][0]
        target.update(type="paragraph",text="Glukoza 99",evidence_roles=["medical_result"])
        duplicate=copy.deepcopy(target);duplicate.update(id="p001-b005",order=5,type="footer",evidence_roles=[])
        doc["pages"][0]["blocks"].append(duplicate)
        review["blocks"][duplicate["id"]]={"status":"verified","md_action":"deduplicate_furniture",
                                          "duplicate_of":target["id"],"reason":"Powtórzenie"}
        plan["pages"][0]["expected_text"]="\n".join(b["text"] for b in doc["pages"][0]["blocks"])
        bind(doc,review,plan)
        with self.assertRaisesRegex(bundle.BundleError,"both repetition"):bundle.validate_content(doc,review,plan)

    def test_G62_12_document_status_in_visual_description_is_protected(self):
        doc,review,plan=example()
        block=doc["pages"][0]["blocks"][1]
        block.update(type="logo",text="",visual_description="Znak wodny: DOKUMENT NIEZATWIERDZONY",evidence_roles=[])
        plan["pages"][0]["expected_text"]="\n".join(b["text"] for b in doc["pages"][0]["blocks"])
        bind(doc,review,plan)
        with self.assertRaisesRegex(bundle.BundleError,"protected"):bundle.validate_content(doc,review,plan)

    def test_G62_15_survey_to_patients_omitted_but_print_time_kept(self):
        doc,review,plan=example()
        block=doc["pages"][0]["blocks"][1]
        block.update(text="Zapraszamy pacjentów do wypełnienia ankiety.",evidence_roles=["survey_invitation"])
        plan["pages"][0]["expected_text"]="\n".join(b["text"] for b in doc["pages"][0]["blocks"])
        bind(doc,review,plan)
        bundle.validate_content(doc,review,plan)
        md=bundle.markdown(doc,review)
        self.assertNotIn("ankiety",md);self.assertIn("Data wydruku",md)

    def test_G62_15_reorganization_keeps_page_links_and_all_included_occurrences(self):
        doc,review,plan=example()
        review["md_order"]=["p001-b004","p001-b003","p001-b001"]
        bundle.validate_content(doc,review,plan)
        md=bundle.markdown(doc,review)
        self.assertLess(md.index("Podpis"),md.index("Data wydruku"))
        self.assertIn("[s. 1]",md)
        review["md_order"].pop()
        with self.assertRaisesRegex(bundle.BundleError,"permutation"):bundle.validate_content(doc,review,plan)

    def test_G62_15_process_hashes_rejected_from_public_content(self):
        for extra in ("schema_version","source_sha256"):
            doc,review,plan=example()
            if extra=="schema_version":doc[extra]="model-document-2"
            else:doc["source"]["sha256"]=review["source_sha256"]
            bind(doc,review,plan)
            with self.assertRaises(Exception):bundle.validate_content(doc,review,plan)

    def test_G62_16_flat_table_rejected(self):
        doc,review,plan=example();doc["pages"][0]["blocks"][0]["type"]="table";bind(doc,review,plan)
        with self.assertRaises(Exception):bundle.validate_content(doc,review,plan)

    def test_G62_17_whitespace_or_nonstrings_do_not_resolve_questions(self):
        for q,a in ((" ","\t"),(1,"yes"),("question",False),([],{})):
            doc,review,plan=example()
            review["blocks"]["p001-b003"].update(status="user_verified",question=q,answer=a)
            with self.assertRaisesRegex(bundle.BundleError,"resolution"):bundle.validate_content(doc,review,plan)

    def test_G62_16_source_value_cannot_be_hidden_in_declared_blank_cell(self):
        with tempfile.TemporaryDirectory() as td:
            f=Fixture(td,("99","112"))
            first,second=f.doc["pages"][0]["blocks"]
            top=first["bbox"][:];bottom=second["bbox"][:]
            first.update(type="table",text="99 112",
                         bbox=[min(top[0],bottom[0]),top[1],max(top[2],bottom[2]),bottom[3]],
                         table={"rows":2,"columns":1,"cells":[
                             {"row":0,"column":0,"text":"99","bbox":top},
                             {"row":1,"column":0,"text":"112","bbox":bottom}]})
            f.doc["pages"][0]["blocks"]=[first];del f.review["blocks"][second["id"]]
            f.write();target=f.stage();f.seal(target)
            first["table"]["cells"][0].update(text="99 112",bbox=first["bbox"][:])
            first["table"]["cells"][1]["text"]=""
            f.write()
            with self.assertRaisesRegex(GeometryError,"blank cell contains"):f.stage("false-blank")
            with self.assertRaisesRegex(GeometryError,"blank cell contains"):f.seal(target,"false-blank.zip")

    def test_G62_17_lines_conflict_rejected_without_plan(self):
        doc,review,plan=example()
        block=doc["pages"][0]["blocks"][0]
        block["lines"]=[{"text":"PLT 999","bbox":block["bbox"][:]}];bind(doc,review,plan)
        with self.assertRaisesRegex(bundle.BundleError,"lines"):bundle.validate_content(doc,review)


if __name__=="__main__":unittest.main()

