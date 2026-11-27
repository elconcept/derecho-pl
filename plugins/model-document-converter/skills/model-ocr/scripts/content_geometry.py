"""Bind content coordinates to actual PDF word occurrences, including repeated text.

No OCR is performed. Each representation consumes the same concrete occurrences.
Overlapping stamps are allowed; two source words remain two different occurrences.
"""
from __future__ import annotations
from collections import deque
import hashlib
import json
import unicodedata
import pymupdf as fitz


class GeometryError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise GeometryError(message)


def norm(text):
    return " ".join(unicodedata.normalize("NFC", text).split())


def displayed_rect(page, box):
    return fitz.Rect(box) * page.rotation_matrix


def content_rect(page, box):
    r = page.rect
    return fitz.Rect(box[0]*r.width, box[1]*r.height, box[2]*r.width, box[3]*r.height)


def contains(parent, child, tolerance=2.0):
    return (child.x0 >= parent.x0-tolerance and child.y0 >= parent.y0-tolerance
            and child.x1 <= parent.x1+tolerance and child.y1 <= parent.y1+tolerance)


def units(block):
    if "table" in block:
        return [("cell-%d-%d" % (x["row"], x["column"]), x)
                for x in sorted(block["table"]["cells"], key=lambda x:(x["row"],x["column"]))]
    if "lines" in block:
        return [("line-%d" % n, x) for n,x in enumerate(block["lines"])]
    return [("text", block)]


def requests(page, block_id, parts):
    result=[]
    for part_id,part in parts:
        box=content_rect(page,part["bbox"])
        for token in norm(part["text"]).split():
            result.append({"owner":block_id,"part":part_id,"text":token,"bbox":box})
    return result


def assign(reqs, words, allowed=None):
    """One-to-one bipartite assignment, never reuse an occurrence to satisfy repetition."""
    allowed=set(range(len(words))) if allowed is None else set(allowed)
    require(len(reqs)==len(allowed), "Text occurrence count differs from its PDF region")
    by_text={}
    for i in allowed:
        by_text.setdefault(words[i]["text"],[]).append(i)
    candidates=[]
    for request in reqs:
        r=request["bbox"]
        found=[i for i in by_text.get(request["text"],[]) if contains(r,words[i]["bbox"])]
        require(found, "%s/%s: no PDF occurrence of %r inside approved bbox" %
                (request["owner"],request["part"],request["text"]))
        # Stable preference for the nearest occurrence; uniqueness is enforced below.
        found.sort(key=lambda i:(abs((words[i]["bbox"].x0+words[i]["bbox"].x1)-(r.x0+r.x1))
                                 +abs((words[i]["bbox"].y0+words[i]["bbox"].y1)-(r.y0+r.y1)),i))
        candidates.append(found)
    owners={}
    assigned={}
    for start in sorted(range(len(reqs)),key=lambda n:(len(candidates[n]),n)):
        queue=deque([start]); seen_requests={start}; parents={}; free=None
        while queue and free is None:
            request=queue.popleft()
            for word in candidates[request]:
                if word in parents:
                    continue
                parents[word]=request
                if word not in owners:
                    free=word;break
                previous=owners[word]
                if previous not in seen_requests:
                    seen_requests.add(previous);queue.append(previous)
        require(free is not None, "Two content occurrences point to the same PDF occurrence; distinct source region missing")
        word=free
        while True:
            request=parents[word]
            previous_word=assigned.get(request)
            assigned[request]=word;owners[word]=request
            if previous_word is None:
                break
            word=previous_word
    require(set(owners)==allowed, "PDF contains source words not represented in JSON")
    return assigned


def verify_grid(page, block, actual_boxes=None):
    """Rows/columns must agree with source cell locations, allowing spans and page rotation."""
    if "table" not in block:
        return
    cells=block["table"]["cells"]
    boxes=[(actual_boxes.get((c["row"],c["column"]),content_rect(page,c["bbox"]))
            if actual_boxes is not None else content_rect(page,c["bbox"]))*page.derotation_matrix for c in cells]
    for i,a in enumerate(cells):
        ar=range(a["row"],a["row"]+a.get("rowspan",1))
        ac=range(a["column"],a["column"]+a.get("colspan",1))
        for j in range(i+1,len(cells)):
            b=cells[j]
            br=range(b["row"],b["row"]+b.get("rowspan",1))
            bc=range(b["column"],b["column"]+b.get("colspan",1))
            ra,rb=boxes[i],boxes[j]
            if max(ac.start,bc.start)<min(ac.stop,bc.stop):
                if ar.stop<=br.start:
                    require((ra.y0+ra.y1)<(rb.y0+rb.y1),block["id"]+": row order disagrees with source cell geometry")
                elif br.stop<=ar.start:
                    require((rb.y0+rb.y1)<(ra.y0+ra.y1),block["id"]+": row order disagrees with source cell geometry")
            if max(ar.start,br.start)<min(ar.stop,br.stop):
                if ac.stop<=bc.start:
                    require((ra.x0+ra.x1)<(rb.x0+rb.x1),block["id"]+": column order disagrees with source cell geometry")
                elif bc.stop<=ac.start:
                    require((rb.x0+rb.x1)<(ra.x0+ra.x1),block["id"]+": column order disagrees with source cell geometry")


def verify_cell_membership(page, block, words, cell_words):
    """Reject conflicting table cell membership; independent stamps may overlap."""
    for cell in block["table"]["cells"]:
        own=(cell["row"],cell["column"])
        rect=content_rect(page,cell["bbox"])
        mx,my=min(1.0,rect.width*.1),min(1.0,rect.height*.1)
        for key,indices in cell_words.items():
            if key==own:
                continue
            for index in indices:
                r=words[index]["bbox"];cx=(r.x0+r.x1)/2;cy=(r.y0+r.y1)/2
                if rect.x0+mx<cx<rect.x1-mx and rect.y0+my<cy<rect.y1-my:
                    problem="declared blank cell contains source text" if not norm(cell["text"]) else "source word ambiguously belongs to distinct cells"
                    raise GeometryError(block["id"]+": "+problem)


def verify_document_geometry(document, pdf_path):
    report={"ok":True,"coordinate_system":document["coordinate_system"],"tolerance_pt":2.0,"pages":[]}
    with fitz.open(pdf_path) as pdf:
        require(pdf.is_pdf and len(pdf)==document["source"]["page_count"],"PDF/content page count differs")
        for page,content in zip(pdf,document["pages"]):
            require(abs(page.rect.width-content["width_pt"])<=0.01
                    and abs(page.rect.height-content["height_pt"])<=0.01,
                    "page %d: JSON dimensions differ from actual displayed CropBox" % content["page_number"])
            words=[]
            for item in page.get_text("words",clip=fitz.INFINITE_RECT(),sort=False):
                text=norm(item[4])
                if not text:
                    continue
                # A PDF word is normally one token. Explicit multi-token items remain
                # individually consumable occurrences sharing the actual extracted bbox.
                for token in text.split():
                    words.append({"text":token,"bbox":displayed_rect(page,item[:4])})
            reqs=[]
            for block in content["blocks"]:
                verify_grid(page,block)
                reqs.extend(requests(page,block["id"],units(block)))
            assigned=assign(reqs,words)
            by_block={}
            actual_cells={}
            cell_words={}
            for i,w in assigned.items():
                by_block.setdefault(reqs[i]["owner"],set()).add(w)
                if reqs[i]["part"].startswith("cell-"):
                    _,row,column=reqs[i]["part"].split("-")
                    key=(int(row),int(column))
                    cell_words.setdefault(reqs[i]["owner"],{}).setdefault(key,set()).add(w)
                    cells=actual_cells.setdefault(reqs[i]["owner"],{})
                    if key in cells:
                        cells[key] |= words[w]["bbox"]
                    else:
                        cells[key] = fitz.Rect(words[w]["bbox"])
            rep_count=0
            for block in content["blocks"]:
                allowed=by_block.get(block["id"],set())
                # No if/elif: every present representation must map to the SAME set.
                assign(requests(page,block["id"],[("text",block)]),words,allowed)
                rep_count+=1
                if "lines" in block:
                    assign(requests(page,block["id"],[("line-%d"%n,x) for n,x in enumerate(block["lines"])]),words,allowed)
                    rep_count+=1
                if "table" in block:
                    assign(requests(page,block["id"],[("cell-%d-%d"%(x["row"],x["column"]),x)
                                                     for x in block["table"]["cells"]]),words,allowed)
                    # Declared oversized/overlapping boxes cannot legitimize swapping
                    # values between labels. Prove the grid from actual assigned words.
                    verify_grid(page,block,actual_cells.get(block["id"],{}))
                    verify_cell_membership(page,block,words,cell_words.get(block["id"],{}))
                    rep_count+=1
            mapping=[{"block":r["owner"],"part":r["part"],"pdf_word":assigned[i]} for i,r in enumerate(reqs)]
            report["pages"].append({"page":content["page_number"],"words":len(words),"representations":rep_count,
                                    "table_grids_from_pdf_words":sum("table" in b for b in content["blocks"]),
                                    "unique_occurrences":True,"mapping_sha256":hashlib.sha256(
                                        json.dumps(mapping,sort_keys=True,separators=(",",":")).encode()).hexdigest()})
    return report

