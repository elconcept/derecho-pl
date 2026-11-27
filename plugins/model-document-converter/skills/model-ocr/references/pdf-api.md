# PDF helper: preparation, invisible text and verification

`scripts/pdf_pipeline.py` performs deterministic file operations. MODEL reads the page images, decides what the source actually says, verifies line/word geometry and supplies the approved layer plan. The helper does not invoke OCR backends, another model, a remote API, or an extraction service.

Input PDFs remain the PDF base. The helper never rebuilds a PDF input from rendered pages. Existing image streams, pixel dimensions, masks, placements, page geometry, visible native text, links, annotations and form widgets are checked after modification. Renders are working evidence only and must not enter the final document bundle.

## Commands

Run with the host's available Python interpreter from the Skill directory, or use absolute paths to the script:

```bash
python scripts/pdf_pipeline.py prepare input.pdf work/run-001
python scripts/prepare_font.py
python scripts/pdf_pipeline.py build input.pdf work/layer-plan.json work/searchable.pdf --font /verified/path/DejaVuSans.ttf --qa-report work/pdf-qa.json
python scripts/pdf_pipeline.py qa input.pdf work/searchable.pdf work/layer-plan.json --report work/pdf-qa-final.json
```

For an image input, run `prepare` on that original image and then supply the returned `base_pdf` to `build` and `qa`. Never supply the upscaled PNG working render as the PDF source.

`prepare` accepts `--image-dpi` (default 300, the recorded physical-size assumption for an image without PDF dimensions) and `--max-render-pixels` (default 40,000,000 per rendered page). `build` accepts `--font`, `--qa-report` and `--max-render-pixels`. `qa` accepts `--report` and `--max-render-pixels`. A limit failure does not authorize silently downscaling text or dropping pages. Use reviewed tiles or an explicit, feasible higher limit.

Exit 0 means that command completed its defined checks. Exit 2 means failure. A successful `prepare` is not an OCR-quality verdict. A successful PDF QA verifies the PDF mechanics against the supplied approved plan; MODEL's content verification remains necessary.

## Python API

```python
inventory = prepare(input_path, work_dir,
                    max_render_pixels=40_000_000,
                    max_input_pixels=120_000_000,
                    image_dpi=300.0)

report = build(source_pdf_path, plan_dict_or_path, output_path,
               font_path=None, qa_report_path=None,
               max_render_pixels=40_000_000)

report = qa(source_pdf_path, output_path, plan_dict_or_path,
            max_render_pixels=40_000_000)

binding = verify_source_base(original_path, base_pdf,
                             expected_kind=None, inventory=None,
                             max_input_pixels=120_000_000,
                             max_render_pixels=40_000_000)
```

`PipelineError` means a required invariant failed. `build` does not overwrite an original or existing output, and publishes the new output only after mandatory QA succeeds. An unsuccessful candidate is deleted; an optional QA report may remain as working evidence. `qa` returns `ok`, `errors` and per-page checks for an actual candidate. Invalid plans or unavailable required operations can raise `PipelineError`; never interpret that as a pass.

The archive distribution's default Unicode font is `assets/DejaVuSans.ttf`. For the GitHub source distribution, run `python scripts/prepare_font.py` and use the actual verified path returned by the command as `--font` or `font_path`; `/verified/path/DejaVuSans.ttf` in the example is a placeholder. For local tests and packaging, `python scripts/prepare_font.py --install` provisions the same verified font in the writable asset directory. No automatic network download is performed. Missing glyphs are a blocking error. Supply a suitable font if the source needs a script outside that font's coverage; do not replace letters with approximations. Actual font use must remain invisible (`render_mode=3`).

## Preparation inventory and source binding

`prepare` writes `work_dir/inventory.json` and `work_dir/renders/page-00001.png`, etc. Important inventory fields:

| Field | Meaning |
|---|---|
| `schema_version` | `model-ocr-inventory-1` |
| `source_kind` | `pdf` or `image` |
| `original_filename` | Exact uploaded filename |
| `original_input` | Absolute working path to original input |
| `input_sha256` | SHA256 of exact original uploaded bytes |
| `original_input_sha256` | Explicit alias for `input_sha256` |
| `base_pdf` | Original PDF path, or the newly prepared PDF for an image |
| `source_sha256` | SHA256 of exact `base_pdf` bytes; binds the layer plan |
| `page_count` | Independent source PDF page count |
| `coordinate_system` | `unrotated_mupdf_points` |
| `signature_detection` | Presence only: status, count and observed signature structure |
| `source_base_binding` | Fresh source-to-base verification from actual bytes, frames, pixels and geometry |
| `pages` | Ordered geometry, renders, original text candidates and image descriptors |

For PDF input, `input_sha256 == source_sha256`, and `base_pdf` refers to the unchanged PDF. For image input, the hashes normally differ: raw original image identity is `input_sha256`, and the layer plan is bound to the created PDF by `source_sha256`. Hashes in a supplied inventory do not prove that an image and a PDF depict the same source. Do not substitute a PDF created from an enlarged working render.

**Call `verify_source_base` at both bundle staging and final sealing**, using the actual original/raw bytes, actual PDF base and declared source kind. The helper detects the real type from content, independently of the filename or declared kind. A PDF mislabeled as an image remains a PDF and must have a byte-identical base. An actual image is independently decoded into ordered source frames; each base page must contain exactly that original-resolution frame, with matching decoded pixels, mask, color interpretation, full-frame placement and visible rendering. Ordinary JPEG input also retains its exact compressed stream. Foreign text, graphics, annotations, widgets, altered frame order, resampling and substituted images fail the binding check.

The optional `inventory` may be a dictionary or JSON path. If supplied, its complete schema, type, hashes, page count, geometry and original/oriented image dimensions must also agree with the files. A two-hash claim is insufficient. Binding is recomputed; neither `source_base_binding` from an earlier run nor a caller-supplied `ok: true` is trusted. The returned report contains `ok`, `actual_kind`, `source_kind`, `input_sha256`, `original_input_sha256`, `source_sha256`, `original_filename`, `binding` (`byte_identical_pdf` or `verified_image_pixels`), `page_count`, actual `pages` geometry, image `frames` evidence and `inventory_checked`. `PipelineError` blocks staging/sealing on any disagreement.

Each page records its MediaBox, CropBox, CropBox position, rotation, display rectangle, unrotated rectangle, rotation/derotation matrices and PDF transformation matrix. It also records the render path/size, candidate `text`, `native_dict`, `native_words`, and `texttrace`. Each trace contains `trace_index`, text, type, font, size, direction and individual character boxes/origins. `hidden: true` means texttrace type 3; opacity, white text, a signature-like mark or a background-covered text run do not independently authorize removal.

PDF renders use the exact baseline:

```text
dpi = max((1024 / min(page_width_points, page_height_points)) * 72, 192)
scale = dpi / 72
```

The renderer includes annotations and form appearances (`annots=True`) and produces RGB. It does not flatten or modify the original PDF. Inspect whether all visible form content appears correctly before treating a render as ground truth.

Image-input working previews are rendered **from the prepared PDF** as RGB on a white background, at original image resolution or a larger working scale that brings the shorter side to at least 1536 pixels. This makes transparent black, palette transparency and partial alpha visible in the same way as the actual PDF; simply discarding alpha with `convert("RGB")` is forbidden. The preview records `render_dpi`, `render_pixels`, `working_upscale_only` and `preview_source`. Its increased resolution never changes the embedded source image.

The PDF uses original-resolution image samples. Ordinary single-frame JPEG with normal EXIF orientation retains the original compressed JPEG stream. Ordinary PNG is passed directly to the PDF engine, which embeds its native-resolution samples and transparency mask. An EXIF orientation transform or supported multi-page image uses lossless pixels at original resolution. Raw input remains unchanged. TIFF/MPO frames become ordered pages; ambiguous animated images are rejected rather than silently taking the first frame.

The current helper explicitly rejects high-bit-depth and floating-point image input before writing any PDF base, preview or successful inventory. This includes `I;16`, `I` and `F` modes, TIFF samples above 8 bits, 16-bit PNG including RGB PNG that Pillow exposes as mode `RGB`, and portable-image samples above 255. It does not clip, scale, saturate or label those samples as losslessly converted. Every frame is checked, so an unsupported later TIFF frame cannot leave a partial document. Unsupported sample modes, ambiguous image formats and CMYK transformations requiring an unverified RGB conversion also stop with a precise error. Such an input requires a separately reviewed preservation-capable path; it must not be silently converted to an all-white or otherwise altered base.

`signature_detection` is `not_present`, `present`, `malformed`, `not_applicable` for image input, or `unknown` on incomplete inspection. Empty signature fields without a populated signature value are counted as `empty_fields` and remain the normal `not_present` skip branch. A filled signature value or `/Sig` dictionary with missing, short, invalid or out-of-bounds `ByteRange` is retained as a **malformed candidate**, never silently classified as unsigned. Empty/all-zero Contents in a populated candidate is also an explicit issue.

The detector returns `count`, `candidates` (also exposed under the compatibility alias `signatures`), `issues`, `empty_fields` and `cryptographic_validity: "not_checked"`. Each candidate records field name, type, subfilter, observed byte range or null, Contents length/hash and structural issues. Count includes malformed filled candidates. Detection never claims cryptographic integrity, trusted timestamp, certificate trust or qualified status. Present and malformed candidates require the separate signature workflow on raw original bytes; unknown detection cannot authorize an unsigned skip. That workflow binds its report to the raw hash and recomputed detection snapshot.

## Layer plan

The plan is a temporary operational file, not the clean public paragraph JSON. Do not add it to the final bundle.

```json
{
  "schema_version": "model-ocr-layer-plan-1",
  "source_sha256": "<SHA256 of base_pdf>",
  "review_complete": true,
  "unresolved": [],
  "pages": [
    {
      "page": 1,
      "mode": "patch",
      "expected_text": "<complete approved page text, in logical sorted extraction order>",
      "lines": [
        {
          "text": "304",
          "geometry_verified": true,
          "source": {
            "trace_index": 5,
            "char_start": 0,
            "char_end": 3,
            "original_text": "30A"
          }
        }
      ],
      "search_checks": [
        {"text": "304", "bbox": [180, 130.4, 203.5, 142.4]}
      ]
    }
  ]
}
```

The values above illustrate the format. Obtain actual indices, old text and coordinates from the current input inventory. Source-character indices use a half-open interval: `char_start` included, `char_end` excluded. Select **exactly one complete original word/token**, even if only one character is wrong. Both the selected source range and replacement must be free of whitespace. Replacing just `A` in `30A` with a separate text run can make sorted extraction show `304` while ordinary PDF search cannot find `304`; the helper rejects that unsafe partial-word edit.

A multiword line patch is also rejected: fitting a different font to the old enclosing line box can move individual words while preserving the outer rectangle. For a line containing several errors, create one patch entry per changed original word, each with its own original character selector and derived box. All unaffected glyphs remain untouched. A word that spans several source text runs requires a separately reviewed geometry-preserving operation; an interior-run selector is not accepted as a whole word. Do not switch to `rebuild_hidden` merely to bypass these safeguards when original word geometry is usable.

The plan must contain pages 1 through N exactly once and in order. `review_complete` must be true and `unresolved` must be an empty array **after** visual review and user answers. These fields do not replace that review. `expected_text` includes all approved searchable source text on that page, including retained native text; it is not a summary or the repetition-reduced Markdown. Do not put MODEL commentary or descriptions of non-text pictures into the invisible OCR layer as though they were printed source text.

### Modes

| Mode | Allowed operation |
|---|---|
| `keep` | Preserve the page's current text. `lines` must be empty. Full QA still applies. |
| `add` | Insert approved text into a textless page or verified textless regions of a mixed page. New geometry may not intersect any existing source glyph or another new line/word box. Existing native text and good OCR are retained. |
| `patch` | Replace exactly one complete original word/token per entry, using its type-3 source geometry. Multiword line patches are rejected. Each entry needs `source`; its bbox is derived automatically. An optional bbox assertion must match the original within 0.05 point. |
| `rebuild_hidden` | Replace all confirmed hidden text after unusable old geometry was explicitly reviewed. Requires `geometry_override_reviewed: true`, a non-empty `rebuild_reason`, and independently verified new line/word bboxes. Visible text is retained; new text cannot overlap it. |

For `add` and `rebuild_hidden`, every entry is a single line or word:

```json
{"text": "PLT 304", "bbox": [52, 128, 205, 143], "geometry_verified": true}
```

Never pass a paragraph containing line breaks to `insert_text`. The helper rejects newlines, tabs, paragraph-like multiline selections and invalid/outside rectangles. It fits one approved line or word to its measured rectangle with a Unicode font and invisible text. Horizontal scaling must stay between 0.5 and 2.0; font size must be 2–72 points, and a patch must stay within 0.6–1.6 times the original traced font size. An implausible fit is a blocking request to verify/split geometry or choose a suitable font, not permission to squeeze a paragraph into a line. Longer paragraphs require separate line placements. It does not invent word coordinates from paragraph proportions.

`patch` currently accepts complete horizontal word ranges in unrotated page space. Page `/Rotate` values 0, 90, 180 and 270 are supported via the page transform. Angled or vertical original text, words crossing separate text runs, ambiguous inline images, unsafe intersecting glyphs and malformed annotation structures fail closed and require a reviewed specialized operation; no rasterized substitute is allowed.

### Coordinate conversion

Internal line-plan coordinates use points on the **unrotated** cropped page, with origin at the top left. PyMuPDF's text coordinates already account for the CropBox; do not subtract its offset again.

The public document JSON uses normalized coordinates on the **displayed** page. Convert an internal rectangle using the recorded rotation matrix, then divide by displayed width/height:

```python
display_box = fitz.Rect(internal_box) * page.rotation_matrix
normalized_box = [display_box.x0 / page.rect.width,
                  display_box.y0 / page.rect.height,
                  display_box.x1 / page.rect.width,
                  display_box.y1 / page.rect.height]
```

Convert a displayed PNG bbox to displayed points using its actual pixel-to-point scale; then use `page.derotation_matrix` for the internal plan. Keep the source page number, render dimensions and crop transforms attached to working geometry. A bbox from a separately cropped high-DPI detail image must first be translated back into full-page coordinates.

## Editing guarantees and save sequence

The helper removes only explicitly selected type-3 hidden text. It checks for collateral overlap with unselected text, original annotations, form widgets and links before mutation. It creates temporary redaction annotations with `fill=False, cross_out=False` and applies them with `images=PDF_REDACT_IMAGE_NONE`, `graphics=PDF_REDACT_LINE_ART_NONE`. Images and vector graphics must not be redacted.

Pre-existing source Redact annotations are temporarily detached from the page annotation array while the helper applies only its own temporary annotations. The exact original array is restored before saving. Their original appearance and contents remain subject to final checks. Unsupported annotation arrays are rejected.

Saving proceeds in this order:

1. Insert approved hidden line/word text and subset fonts.
2. Perform the requested optimized save with `garbage=4, deflate=True`.
3. Compare encoded image/mask streams with the original. PyMuPDF can compress previously unfiltered images even when `deflate_images=False`. If that happened, restore the exact original encoded bytes and filter properties, then save without recompressing streams. This is PDF-object restoration, not image regeneration.
4. Reopen the candidate and run full QA. Atomically publish only if every required check passes and the original's hash is unchanged.

The actual restoration count and final compression behavior are recorded in `save_strategy`. ICC color-profile data may be losslessly compressed; its decoded profile and semantic properties must remain identical. Actual image and mask encoded streams remain byte-exact. Object IDs and resource names may change without changing image identity.

## Mandatory QA

`qa` compares the actual source and candidate, independently of build's returned success:

- Same page count, boxes, crop position, rotation and coordinate transforms.
- Same image occurrence dimensions, transformation, decoded pixels, encoded raw stream hashes and masks. Xref/resource-name changes are not treated as content changes.
- Same original annotation/widget/link information and visible native text geometry.
- Every retained invisible glyph has the same Unicode value, origin, bbox, direction, writing mode and opacity. Origins/boxes allow only 0.05 point of numeric roundoff. Matching is independent of text-run segmentation and font-resource renaming. This gate runs automatically for `keep`, `add` and unselected text in `patch`, even when `search_checks` is absent or empty; a moved good OCR layer cannot pass on extraction equality alone. The page report includes `retained_hidden_geometry` with matched/unmatched counts and failure examples.
- Exact RGB rendered-pixel equality at the baseline dynamic DPI, with annotations present.
- **Zero characters outside the displayed page**, allowing only a 2-point coordinate tolerance. Character boxes from unbounded diagnostics are transformed through the page rotation matrix before comparison with displayed `page.rect`.
- Complete `expected_text` equality in ordinary sorted extraction **and explicit page-bounded extraction**, using NFC and whitespace normalization only. Punctuation, signs, case, digits and diacritics are not normalized away.
- The same approved text in infinite-clip diagnostic extraction. Infinite clipping cannot conceal failure of ordinary extraction.
- Default unsorted extraction character coverage, plus exact ordered and spatial checks; a Counter alone never proves fidelity.
- Every inserted line/word and every replaced original word is searchable within its approved region; optional `search_checks` add critical tokens or phrases. Patch geometry comes from each selected original word, and all unmodified hidden glyphs undergo the separate mandatory geometry proof. Wrong/stale text fails the exact page-text comparison.
- File-size and actual encoded-font-stream byte deltas, with residual PDF-object/compression deltas. Image resampling is reported false only after exact preservation is proved; otherwise it remains unknown.

A matching self-authored plan cannot prove that MODEL read an image correctly. Before `review_complete: true`, MODEL must compare its canonical transcription and geometry against the rendered source, inspect critical tokens and resolve uncertain readings with the user. The helper's mechanical checks then establish that the PDF contains that approved transcription without damaging the source's visible content.

## API references and tested runtime

Implementation inspected against installed PyMuPDF 1.26.6 / MuPDF 1.26.11 and Python 3.12. The official API references checked during construction are [Page operations and coordinate rules](https://pymupdf.readthedocs.io/en/latest/page.html), [texttrace and low-level information](https://pymupdf.readthedocs.io/en/latest/functions.html) and [Document saving](https://pymupdf.readthedocs.io/en/latest/document.html). Recheck relevant APIs when upgrading the runtime and rerun the package's preservation regressions.
