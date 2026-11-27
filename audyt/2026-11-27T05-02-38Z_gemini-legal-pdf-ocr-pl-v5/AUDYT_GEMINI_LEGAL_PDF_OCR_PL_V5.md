# Audyt niezależny — Gemini `legal-pdf-ocr-pl-v5`

**Stan badany:** archiwum `legal-pdf-ocr-pl-v5.zip` otrzymane 2026-11-27; SHA-256 `db79264247dc42fe3975f58a82a28bedf6c8718008257dac66e53920500410fd`. 10 plików: `SKILL.md`, 5 referencji, 3 skrypty Pythona i 1 plik testów. 

**Środowisko audytu:** Python 3.13.5, PyMuPDF 1.26.7, Pillow 12.3.0, NumPy, jsonschema 4.26.0, pypdf 5.9.0. Biblioteka pyHanko nie była zainstalowana, dlatego rzeczywista kryptografia nie była badana. Kod w ZIP i jego wyniki nie zostały zmienione przez audytora. Wszystkie dodatkowe dokumenty są syntetyczne.

**Wynik:** **NIE ODBIERAĆ v5 jako narzędzia zapewniającego wiarygodną zgodność `raw → PDF → JSON → MD → LOG`.** Samo uruchomienie suity producenta daje **7 PASS / 1 FAIL**. Dodatkowe celowane próby wykazały wielokrotne fałszywe `PASS` dla dokumentów zawierających odmienne dane lub uszkodzony obraz. To testy kontrprzykładowe, nie pomiar odsetka błędów w realnym korpusie.

## A. Faktyczny wynik testów dostarczonych przez Gemini

Polecenie uruchomione na NIEZMIENIONYM źródle: `python -m unittest discover -s tests -v`.

- **8 testów wykonanych, 1 niepowodzenie, exit code 1** (`FAILED (failures=1)`).
- Niepowodzenie: `test_unrelated_raw_and_fake_image_kind_rejected`, `tests/test_audit_acceptance.py:119-132`. Dla różnych plików `a.pdf` (`ORIGINAL 1`) i `b.pdf` (`OTHER 2`) autor oczekiwał `FAIL`, ale `qa_validate.validate_bundle` zwrócił `PASS`.
- Pozostałe 7 testów zaliczono. W testach wystąpiły też liczne `ResourceWarning` z powodu niezamkniętych plików; jest to kwestia higieny testów, nie blokujący błąd funkcjonalny.

Wynik jest szczególnie istotny, ponieważ memo deklarowało, że skrypty **nie były uruchamiane przez autora**. Tutaj zostały wykonane na dostarczonym kodzie.

## B. Odtworzone problemy — priorytety i warunki odbioru

### GV5-01 [P0] Brak twardej więzi oryginał → PDF / obejście `doc_id`

**Kod:** `scripts/qa_validate.py:253-260, 287-315`. Testy: `foreign_pdf`, `foreign_image_pdf`, `source_files_bypass_sha`.

- `raw/a.pdf` zawiera `ORIGINAL 1`, wynikowy PDF i MD/JSON zawierają `OTHER 2`; **QA = PASS**. Drobna różnica widocznego tekstu nie przekracza progu średniej różnicy pikseli.
- Dla wejściowego PNG z napisem `ORIGINAL 1` i zupełnie obcego PDF z `PLT 304`, `--image-input` również daje **PASS**, ponieważ obrazu wejściowego nie porównuje się z bazą/wynikiem.
- Jeśli JSON zawiera niepuste `source.source_files`, kod **pomija sprawdzenie `doc_id == SHA-256(raw)` bez względu na rzeczywisty typ oryginału**. Fałszywy hash `ffff...` i nieprawdziwy wykaz plików uzyskały **PASS**.

**Poprawka:** wiązać rzeczywiste bajty każdego pliku raw, kolejność stron/klatek, faktyczny typ, manifest i zawartość/położenie obrazu w PDF, w dwóch niezależnych etapach wydania; źródłowy PDF powinien odpowiadać bazie bajtowo, jeżeli taki jest kontrakt. `source_files` nie może wyłączać weryfikacji. **Akceptacja:** wszystkie trzy powyższe przypadki kończą się `FAIL`, poprawny PDF oraz poprawna seria obrazów kończą się `PASS`.

### GV5-02 [P0] Regresja wyglądu dokumentu przechodzi QA

**Kod:** `qa_validate.py:287-315`, próg `mean_diff < 0.5`. Test `erase_visible_text`.

Na wydruku z widocznym `PLT 304` położyłem biały prostokąt zasłaniający **wyłącznie liczbę `304`**. Ekstrakcja tekstu PDF nadal zwraca `PLT 304`, a osadzone obrazy są niezmienione (w tym przykładzie nie było obrazu). Na lokalnym wycinku liczba ciemnych pikseli zmieniła się z **646 do 0**; średnia różnica całej strony przy 120 DPI to **0,04107**, więc **QA = PASS**.

**Poprawka:** dla PDF→PDF wymagaj niezmienionego wyglądu (dokładne rendery po normalizacji rozdzielczości, istotne lokalne różnice, kontrola widocznego tekstu i jego położenia, warstw i zasłaniania), nie tylko średniej z całej strony. **Akceptacja:** w teście `erase_visible_text` `FAIL` przy zachowaniu `PASS` dla rzeczywiście niezmienionego obrazu.

### GV5-03 [P0] Porównanie tekstu usuwa znaki krytyczne, powtórzenia i dopuszcza braki

**Kod:** `qa_validate.py:52-59, 332-350`. Testy: `lost_decimal_comma`, `duplicate_pdf_word`, `duplicate_json_word`.

- `_tokens` rozcina tekst przez `\w+`, co zrównuje `4,7` z `4.7`, `-5` z `5` i `>100` z `100`.
- Użycie `set()` usuwa krotność. PDF `PLT PLT 304` wobec JSON `PLT 304` → **PASS**; odwrotność z powieleniem w JSON również → **PASS**.
- Dodatkowo kod akceptuje do ok. 2% brakujących unikalnych tokenów i 5% nadmiaru; nie jest to „pełna zgodność” deklarowana w memo.

**Poprawka:** zachować znaki, wartości i wielokrotności na poziomie znormalizowanych porównawczo całych fragmentów/wierszy, nie setów; tolerancje raportować osobno, a nie zastępować nimi zgodność. **Akceptacja:** przecinek/kropka, minus, nierówności, druga kopia słowa i brak pojedynczego wyniku muszą powodować `FAIL`.

### GV5-04 [P0] Zamiana wartości między wierszami tabeli nadal przechodzi

**Kod:** `qa_validate.py:175-195, 404-412`. Testy: `swapped_table_values`, `flat_declared_table_no_newline`.

PDF: `PLT 304`, `HGB 14`. JSON `text` zawiera te same słowa, ale `table.rows` wiąże **`PLT → 14`, `HGB → 304`**; MD renderuje nieprawidłowe pary. Wszystkie tokeny są globalnie obecne, więc **QA = PASS**. Ponadto blok zadeklarowany jako `table` bez `table.rows` przechodzi, gdy jego `text` jest jedną linią, mimo że opisuje co najmniej dwa wiersze danych.

**Poprawka:** kanoniczna siatka tabeli z unikatowymi komórkami, geometrią każdej komórki i kontrolą rzeczywistego przypisania źródłowego słowa do komórki; `text` i MD muszą odpowiadać relacjom, nie zbirom wartości. Typ `table` ma bezwarunkowo wymagać struktury. **Akceptacja:** oba przypadki `FAIL`, prawidłowa tabela `PASS`.

### GV5-05 [P0] Markdown może dopisać findings lub usunąć chronione daty

**Kod:** `qa_validate.py:394-417`. Testy: `invented_md_claim`, `lost_print_timestamp`.

MD zawiera `PLT 304` oraz dopisaną nieistniejącą informację `PLT 999 - brak badania`: **QA = PASS**. Inny przypadek: PDF i JSON zawierają datę wydruku `PRINT 2025 09 17`, a MD ją pomija, pozostawiając zdanie `Brak daty wydruku`: **QA = PASS**. Kontrola MD wymaga jedynie wystąpienia *gdziekolwiek* tokenów z tabel i pojedynczego wspólnego tokenu w bloku podpisu/pieczęci; nie jest to grounding MD.

**Poprawka:** jawny ledger `include/omit/deduplicate` z blokami lub polami źródłowymi; kontrola wszystkich uwzględnionych fragmentów i **zakaz dodatkowych niezwiązanych twierdzeń** w MD; ochrona dat, autorów, podpisów, pieczęci, oświadczeń odbioru, numeracji, wyników. **Akceptacja:** oba przypadki `FAIL`, legalne pominięcie zidentyfikowanego boilerplate z LOG `PASS`.

### GV5-06 [P1] Bbox może być rozległy, ponownie użyty lub fikcyjny dla elementu graficznego

**Kod:** `qa_validate.py:351-387`, tolerancja `bbox_tol_norm=0.06`. Testy: `reused_bbox_wide`, `bogus_signature_location`.

Dwa osobne wystąpienia `ALPHA` przypisano dwóm nadmiernie dużym, znacząco nakładającym się bboxom z `IoU < 0.80`: **QA = PASS**, bez dowodu unikatowego powiązania z właściwym wystąpieniem. Nieistniejący w danym miejscu blok `signature` z opisem `podpis widoczny` i bboxem w rogu strony także przechodzi, jeśli treść opisu występuje w MD: **QA = PASS**.

**Poprawka:** unikatowe przypisanie źródłowych wystąpień słów i limity nadmiernego poszerzania bbox; oddzielna kontrola wizualnych elementów i lokalizacji beztekstowych przez MODEL/źródłowy obraz. **Akceptacja:** oba przypadki `FAIL` lub wymagają jawnego, źródłowego przeglądu, nie cichego `PASS`.

### GV5-07 [P0] LOG nie ma weryfikowanej niezmienności, a raport podpisów jest opcjonalny

**Kod:** `qa_validate.py:213-226, 418-425, 437-453`. Testy: `fake_log_changes`, `direct_qa_without_log_or_sig_report`.

Wystarczy umieścić wymagane **nagłówki** i dowolne `doc_id`, aby modyfikacja tabeli korekt OCR i fikcyjnego potwierdzenia człowieka przechodziła jako **PASS**. W `argparse` opcje `--log` i `--sig-report` są opcjonalne; wywołanie QA całkowicie bez obu plików też kończy się **PASS**. Nie sprawdza się deklarowanych hashów dokumentu/planów, rzeczywistych wyników QA, kompletności śladu poprawek i stanu odbioru.

**Poprawka:** deterministycznie odtwarzany rdzeń logu związany z hashami wszystkich artefaktów, planem, przeglądem i wynikami; podpisy źródłowe obowiązkowe w procesie (normalne `absent` dla braku podpisu), faktyczne wywołanie checkera przy każdym seal. **Akceptacja:** fake LOG i brak raportu kończą się `FAIL`.

### GV5-08 [P1] Raport może ogłosić „PODPIS WAŻNY” bez wyniku integralności

**Kod:** `check_signatures.py:102-149`. Test: `unsigned_math_valid_conclusion` (sam serializer, bez prawdziwej walidacji kryptograficznej).

Dla kontrolowanego statusu `intact=None`, `valid=None`, `coverage=ENTIRE_FILE`, `trusted=False` funkcja zwróciła `PODPIS WAZNY w zakresie sprawdzonym`. Kod rozstrzyga na podstawie `coverage`, jeśli `intact`/`valid` nie są dosłownie `False`. Jest to logicznie nieuprawniona konkluzja; **nie stwierdzam, że pyHanko faktycznie zwrócił taki status dla autentycznego podpisu**.

**Poprawka:** „ważny” tylko gdy `intact is True` i `valid is True`, z oddzielnym zaufaniem, pokryciem i niepewnościami; dokumentowy timestamp walidować właściwą ścieżką. **Akceptacja:** niewykonane/nieznane wyniki → `niezweryfikowany`, nie `ważny`.

### GV5-09 [P1] Stan `unresolved` kłóci się ze sprawdzaniem PDF

**Kod:** `SKILL.md` krok 2 i reguła „do OCR wyłącznie tekst widoczny”; `qa_validate.py:332-350`. Test: `unresolved_placeholder`.

JSON `ALPHA [nieczytelne]`, status `unresolved`; PDF zawiera prawidłowo tylko widoczne `ALPHA`, bez sztucznego słowa `nieczytelne`. QA daje `FAIL` za brak tokenu `nieczytelne`. Wpisanie znacznika do PDF z kolei narusza zasadę, aby nie umieszczać w warstwie OCR słów nieobecnych w źródle.

**Poprawka:** rozdzielić transkrypcję widocznego tekstu od operatorów niepewności, zachować status i bbox w JSON oraz informację w LOG, a w QA jawnie traktować placeholder jako opis, nie źródłowy token. **Akceptacja:** rozstrzygnięta nieczytelność z poprawną geometrią przechodzi; wymyślony tekst nie.

### GV5-10 [P2] Drobna pieczęć lub podpis może być klasyfikowany jako pusta strona

**Kod:** `prepare_media.py:84-88, 129-143, 194-205`. Test: `small_visible_mark_blank`.

Raster 1000 × 1000 z czytelnym małym czarnym znakiem został uznany przez `is_visually_blank` za `blank` wskutek progu `>=99.5%` bieli. W kontekście dokumentacji podpis/pieczęć może mieć znaczenie mimo niewielkiego zajętego obszaru.

**Poprawka:** odróżniać „prawie białą stronę” od „potwierdzonej pustej”; przy dowolnych spójnych elementach niebiałych wymusić ogląd/crop lub stan `unreadable/needs_review`, nie automatyczny `blank`.

### GV5-11 [P1] Komendy do serii obrazów i podziałów nie istnieją

**Kod:** `references/qa_checklist.md`, `SKILL.md` poleca `--raw-dir`, `--splits-dir`; `qa_validate.py:437-446` nie definiuje tych argumentów. `python scripts/qa_validate.py --help` pokazuje tylko `--orig`, `--pdf`, `--json`, `--md`, `--log`, `--sig-report`, `--image-input`. Test CLI z dodatkowymi flagami kończy się kodem 2 zanim ruszy QA.

**Poprawka:** implementować rzeczywisty manifest wielu plików i mapy `splits`, a następnie udokumentować/utrwalić wspólny interfejs CLI. **Akceptacja:** ukończony multi-TIFF/seria 2 obrazów i teczka z `splits/manifest.json` przechodzą kompletny przebieg QA.

### GV5-12 [P1] Brak deterministycznego generatora searchable PDF i pełnego testu E2E

W archiwum są trzy skrypty: `prepare_media.py`, `check_signatures.py`, `qa_validate.py`. **Nie ma skryptu budującego lub poprawiającego niewidoczną warstwę OCR**. Instrukcja zleca tę operację modelowi w hoście, więc nie da się niezależnie odtworzyć deklarowanego algorytmu `keep/patch/add`, ochrony natywnego tekstu i geometrii słów na podstawie udostępnionego kodu. Gemini sam przyznaje, że nie uruchomił realnej konwersji.

**Poprawka:** implementować reprodukowalny builder i testy `build → QA → bundle → seal` (co najmniej na dwustronicowym syntetycznym przykładzie, a odbiór końcowy również na dokumencie kontrolnym). Testy nie mogą tworzyć identycznych plików `orig=output` jako jedynego pozytywnego przypadku.

## C. Zgodność z memo Gemini — statusy

| Deklaracja | Co potwierdzono |
|---|---|
| 10 plików i kontrakt JSON 2.1.0 | Potwierdzono strukturę i nazwę schematu. Dane procesu są częściowo usunięte z JSON, ale nadal znajdują się tam techniczne `doc_id` i `contract_version`, co wymaga decyzji względem wcześniejszego zakazu metadanych. |
| Preflight 16-bit i alpha | Dostarczone testy tych przypadków przeszły; test I;16 pokazuje zachowanie kontrastu, **nie** dowodzi bezstratności (sam kod deklaruje skalowanie). |
| Obrót 0/90/180/270 | Cztery pozytywne przebiegi testu przeszły. Nie stanowią dowodu poprawności każdego CropBox i podpisu. |
| Poprawne JSON ↔ PDF ↔ MD | **Niepotwierdzone; odtworzono fałszywe PASS.** |
| Magic bytes i więź pochodzenia | Magic bytes są sprawdzane; **więź pochodzenia jest niekompletna**. |
| Visual Diff | Jest zaimplementowany, ale globalny próg przepuszcza zamaskowanie widocznego tekstu. |
| Walidacja signature/timestamp | Działa serializacja na sztucznym obiekcie statusu; brak sprawdzenia prawdziwego podpisu kryptograficznego w tym środowisku i błędny warunek werdyktu. |
| Niezmienny LOG i pełna ścieżka Drive | Niepotwierdzone; rdzeń można podmienić i pominąć w wywołaniu; Drive nie był wykonywany. |
| Pokrycie testami G3/G62 | Testy są obecne, lecz **suita nie przechodzi**; nie ma testów bramkujących część powyższych przypadków. |

## D. Priorytet wykonania dla autora

1. **P0:** Naprawić pochodzenie, pełną wierność obrazu, relacje tabel, dosłowną zgodność wartości i kontrolę MD/LOG. Wszystkie testy negatywne muszą faktycznie odrzucać bundle.
2. **P1:** Dodać wiarygodną geometrię cytatów i podpisów, osobny mechanizm obsługi `[nieczytelne]`, poprawny warunek konkluzji podpisu, wsparcie serii obrazów oraz generator searchable PDF.
3. **P2:** Nie klasyfikować drobnych pieczęci jako `blank`, dostosować ochronę boilerplate i zagregowany zapis metadanych technicznych do końcowego kontraktu.

**Ważna zasada odbiorowa:** MD jest wyłącznie narzędziem do wyszukiwania możliwych findings; nie wolno mu tworzyć ani gubić istotnych informacji. JSON ma służyć wstępnej lokalizacji i weryfikacji, PDF jest obrazem źródłowego dokumentu, a LOG przechowuje sprawdzalny przebieg. Przypisanie sprawstwa, prawdziwości pieczęci lub autentyczności dokumentu nie jest zadaniem konwertera.

## E. Reprodukcja i ograniczenia

- `python -m unittest discover -s tests -v` — oryginalna suita v5, **7 PASS/1 FAIL**; pełny output w `unittest.txt`.
- `python repro_extra.py` oraz `python repro_more.py` — niezależne przypadki syntetyczne; szczegółowe wyniki w `independent_results.json` i `independent_more_results.json`; źródłowe PDF-y i MD/JSON w `cases/`.
- Reproducery uruchamiają **faktyczne funkcje z archiwum Gemini**, nie ich zastępnik. Nie są atakiem na GitHub ani innymi danymi użytkownika.
- Nie wykonano pełnego OCR na rzeczywistym dokumencie, ponieważ w paczce brak deterministycznego generatora wynikowego PDF, a docelowy host Gemini nie jest tutaj dostępny. Nie uruchamiano rzeczywistej kryptografii pyHanko ani zapisu do Google Drive.
- Liczba fałszywych akceptacji w sztucznie skonstruowanych próbach nie stanowi zmierzonej skuteczności modelu na skanach. To dowód istnienia konkretnych luk logicznych w bramce QA.