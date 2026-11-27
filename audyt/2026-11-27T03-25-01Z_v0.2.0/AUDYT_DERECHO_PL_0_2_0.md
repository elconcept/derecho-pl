# Audyt aktualizacji MODEL Konwerter 0.2.0 — derecho-pl

**Repo:** https://github.com/elconcept/derecho-pl  
**Utrwalony commit:** `18f6fffc8bc1a82677ebe9b88dc1d60fdf7fa096` (2026-11-27)  
**Przedmiot:** `plugins/model-document-converter/` — aktualizacja w stosunku do przekazanej wcześniej wersji 0.1.0.  
**Zakres:** weryfikacja zamknięcia 17 wcześniejszych uwag, niezależne próby geometrii cytatów, ryzyka ubytku informacji w Markdown, weryfikacja dokumentacji wydania i struktury pluginu. **Nie zmieniano repozytorium.**

## 1. Ocena wykonawcza

**Wersja 0.2.0 rzeczywiście naprawia w kodzie oba wcześniejsze blokery P0 (G62-01 i G62-02) oraz wprowadza wiele pozostałych zabezpieczeń.** Rozliczenie nie opiera się wyłącznie na zapewnieniach autora: sprawdziłem treść kodu udostępnionego przez plugin GitHub, zgodność 11 hashy z manifestem testowym oraz niezależnie wykonałem dokładną wersję modułu `content_geometry.py` z tego commita.

**Pozostają luki wymagające reakcji przed poleganiem na bboxach JSON jako pewnej lokalizacji cytatu:**

1. Dwa odległe wystąpienia tego samego słowa mogą mieć w JSON dwa bboxy obejmujące całą stronę, a walidator nadal przyjmuje mapowanie jako jednoznaczne.
2. Bbox odręcznego podpisu może znajdować się w przeciwnym rogu strony, a walidator tekstowo-geometryczny nadal zgłosi sukces, jeśli opis wizualny nie ma tekstu OCR.
3. Filtr MD pozostaje zależny od poprawnego oznaczenia semantycznego. Niektóre istotne dane medyczne i potwierdzenia odbioru nie są niezależnie chronione przed pominięciem po błędnej klasyfikacji jako boilerplate.

Powyższe nie dowodzą, że model w praktyce koniecznie źle oznaczy te elementy. Dowodzą, że **automatyczny odbiór nie wykryje określonych błędów nawet przy poprawnych plikach pozostałych formatów**. W zastosowaniu do przeglądu dokumentacji medycznej ma to znaczenie, bo MD jest warstwą wyszukiwania, JSON — lokalizacji i weryfikacji, a PDF — kopią źródła.

## 2. Co faktycznie zweryfikowano

- **GitHub:** przez połączoną aplikację odczytano HEAD i pliki z `main`, przypięto commit, zweryfikowano strukturę 0.2.0 i konkretne funkcje implementacji.
- **Spójność raportu autora:** SHA-256 **11/11** plików kodu, schematu i testów na commicie odpowiadają dokładnie wpisom w `docs/VALIDATION.json`. To wiąże deklarowany raport z aktualnymi plikami, ale nie dowodzi samodzielnie przejścia testów.
- **Autorskie testy:** repozytorium zawiera 83 przypadki `unittest`, a `docs/TEST_RESULTS.txt` i `docs/VALIDATION.json` deklarują **83/83 PASS** w środowisku autora. **Nie uruchomiłem niezależnie całej suity 0.2.0:** w lokalnym kontenerze brak dostępu sieciowego do sklonowania repozytorium. Nie nazywam 83/83 moim wynikiem wykonania.
- **Niezależne wykonanie:** `content_geometry.py` 0.2.0 został odtworzony bajtowo; SHA-256 modułu uruchomionego lokalnie = `919a6de43ca4902f7bf3127087a393766274899954feb1ad9a87dbc975ff18a3`, identyczny z manifestem i GitHub. Próby przeprowadzono z PyMuPDF 1.26.7.
- **Dodatkowe próby:** pełnostronicowe bboxy, błędnie położony graficzny podpis, zachowanie logicznego odczytu dwóch kolumn oraz odizolowane reguły dopuszczające pominięcia w MD. Wszystkie testowe PDF-y zawierają **wyłącznie dane syntetyczne**.
- **Nie wykonano:** pełnej konwersji aktualnym 0.2.0 na dokumentacji pacjenta, walidacji rzeczywistego podpisu kryptograficznego, importu przez marketplace, dostawy do Google Drive i pomiaru jakości OCR MODEL.

## 3. Odtworzone luki i zalecenia

### DPL-01 / P1 — zbyt szeroki bbox tekstu przechodzi jako lokalizacja cytatu

**Ślad kodu:** [`content_geometry.py` linie 31–39, 59–101, 147–205](https://github.com/elconcept/derecho-pl/blob/18f6fffc8bc1a82677ebe9b88dc1d60fdf7fa096/plugins/model-document-converter/skills/model-ocr/scripts/content_geometry.py#L31-L205); [`assemble_bundle.py` linie 83–87](https://github.com/elconcept/derecho-pl/blob/18f6fffc8bc1a82677ebe9b88dc1d60fdf7fa096/plugins/model-document-converter/skills/model-ocr/scripts/assemble_bundle.py#L83-L87).

**Próba:** na stronie 600 × 800 pt znajdują się dwa identyczne słowa `PLT`, jedno u góry po lewej, drugie u dołu po prawej. W JSON dwa bloki mają tekst `PLT`, lecz każdy bbox = `[0,0,1,1]`. Dokładny, aktualny helper akceptuje oba bloki (`unique_occurrences: true`). Wariant z dwoma precyzyjnymi bboxami również przechodzi. Wariant z dwoma błędnymi bboxami tylko w górnej połowie jest prawidłowo odrzucany.

**Dlaczego to ważne:** algorytm gwarantuje przypisanie unikalnego słowa z PDF, ale **nie gwarantuje użytecznej precyzji bboxa**, który potem trafia do JSON. Przy wielokrotnych frazach bbox pełnej strony nie identyfikuje cytowanego miejsca; `mapping_sha256` w raporcie nie jest publiczną mapą PDF→blok.

**Poprawka:** dla krótkich jednostek i pojedynczych słów sprawdzać odległość krawędzi bboxa od faktycznej obwiedni przypisanych słów oraz maksymalny współczynnik rozwinięcia powierzchni; gdy blok jest długi, wymagać bboxów linii lub mniejszych podbloków. Powtórzenia na różnych częściach strony powinny mieć odrębne regiony. Nie stosować jednego globalnego limitu wielkości do całostronicowych akapitów bez alternatywnej struktury linii.

**Test odbiorowy:** dwa dalekie słowa `PLT` z dwiema pełnostronicowymi ramkami odrzucone; dwie ciasne i różne ramki przyjęte; prawidłowy wielowierszowy akapit może przejść z liniami.

### DPL-02 / P1 — bbox treści czysto graficznej nie jest weryfikowany

**Ślad kodu:** [`content_geometry.py` linie 43–56 i 147–205](https://github.com/elconcept/derecho-pl/blob/18f6fffc8bc1a82677ebe9b88dc1d60fdf7fa096/plugins/model-document-converter/skills/model-ocr/scripts/content_geometry.py#L43-L205).

**Próba:** w PDF czarny znak przypominający podpis znajduje się po lewej stronie, ale blok JSON typu `signature` ma `text=""`, `visual_description="Widoczny podpis odręczny"` oraz bbox w prawym dolnym rogu. Dokładny helper zwraca `ok: true`, `words: 0`, `unique_occurrences: true`, identycznie jak dla poprawnego bboxa.

**Przyczyna:** żądania mapowania powstają wyłącznie z `part["text"]`; opis wizualny nie tworzy żądania, a analiza nie sprawdza zawartości obrazu wewnątrz bboxa. To ograniczenie trzeba jasno odróżnić od kontroli rzeczywistej geometrii tekstu.

**Poprawka:** dla podpisów, pieczęci, skreśleń, pustych pól i grafik istotnych dowodowo wymagać oddzielnego potwierdzenia regionu na renderze źródłowym (np. crop + referencja obrazu + jawny zapis kontroli), a w raporcie rozróżniać `text_geometry_verified` i `visual_geometry_human_verified`. Nie raportować samego `unique_occurrences` jako dowodu położenia podpisu.

**Test odbiorowy:** błędnie umiejscowiony graficzny podpis nie otrzymuje automatycznego pozytywnego statusu lokalizacji; prawidłowe oznaczenie po potwierdzeniu jest zachowane.

### DPL-03 / P1 — pominięcie ważnych danych w MD po błędnym przypisaniu roli

**Ślad kodu:** [`assemble_bundle.py` linie 25–43, 99–106 i 214–221](https://github.com/elconcept/derecho-pl/blob/18f6fffc8bc1a82677ebe9b88dc1d60fdf7fa096/plugins/model-document-converter/skills/model-ocr/scripts/assemble_bundle.py#L25-L43).

**Próba izolowana na dokładnych warunkach kodu:** następujące treści nie uruchamiają filtra `PROTECTED_TEXT` i mogą zostać pominięte, **jeśli MODEL omyłkowo przydzieli im wskazaną dozwoloną rolę**:

| Przykładowa treść | Błędnie przypisana rola | Obecna logika |
|---|---|---|
| `WBC (KRWINKI BIAŁE): 8,5 (G/L)` | `survey_invitation` | `omit_boilerplate` dopuszczalne |
| `GLUKOZA: 5,8 (mmol/L)` | `facility_contact` | `omit_boilerplate` dopuszczalne |
| `Otrzymałam/em 2 egzemplarze Karty informacyjnej z leczenia szpitalnego.` | `routine_media_instructions` | `omit_boilerplate` dopuszczalne |
| `Otrzymałam/em oryginały dokumentacji zewnętrznej` | `facility_administration` | `omit_boilerplate` dopuszczalne |

Dla kontrpróby `Data wydruku: 2025-09-17 12:17` jest prawidłowo chroniona niezależnie od błędnej roli (regex daty i wydruku). **To nie jest demonstracja fałszywego OCR**: to warunek awarii warstwy semantycznej/odszumiającej. JSON i PDF nadal zawierają pełną treść, ale MD może utracić potencjalny finding.

**Poprawka:** po złej klasyfikacji nie wolno wycinać wyników z liczbami/jednostkami, kodów badań, oświadczeń o dokumentacji, statusów, odmów i zastrzeżeń. Używać niezależnych reguł ochrony plus obowiązkowego rozdzielenia mieszanych bloków; dla niejednoznacznych przypadków zachować w MD i flagować do przeglądu. Rozszerzyć testy o oświadczenia odbioru z dokumentu 5WSK.

**Test odbiorowy:** opisane błędne przypisania ról nie usuwają treści; czysta ankieta i ogólny telefon szpitala nadal są możliwe do pominięcia.

### DPL-04 / P2 — rygor identycznej kolejności PyMuPDF `sort=True` odrzuca poprawne dwie kolumny

**Ślad kodu:** [`pdf_pipeline.py` linie 1203–1217](https://github.com/elconcept/derecho-pl/blob/18f6fffc8bc1a82677ebe9b88dc1d60fdf7fa096/plugins/model-document-converter/skills/model-ocr/scripts/pdf_pipeline.py#L1203-L1217).

**Próba:** w syntetycznym PDF cztery krótkie wiersze stanowią dwie kolumny. Naturalna kolejność czytania: `LEFT_ROW_1 LEFT_ROW_2 RIGHT_ROW_1 RIGHT_ROW_2`. PyMuPDF 1.26.7 z `sort=True` zwraca `LEFT_ROW_1 RIGHT_ROW_1 LEFT_ROW_2 RIGHT_ROW_2`. Niezależny `content_geometry.py` akceptuje dwa poprawnie zlokalizowane bloki kolumn, natomiast test dosłownej zgodności `normalized_text(actual) == expected_text` z QA jest fałszywy. To wykazana niezgodność **dwóch warunków**, nie wykonanie pełnej procedury `qa()` 0.2.0.

**Poprawka:** odróżnić kompletność treści i jej geometrię od arbitralnej kolejności strumienia ekstrakcji. Dopuścić zweryfikowany porządek kolumnowy w kontrakcie albo porównywać fragmenty/bboxy indywidualnie. Zakaz cichej permutacji wartości w tabelach musi pozostać.

**Test odbiorowy:** legalne dwukolumnowe bloki lekarzy przechodzą QA, mimo że `sort=True` interleawuje ich linie; zmienione słowo lub wartość nadal jest blokowane.

### DPL-05 / P3 — encje HTML w GFM zwiększają szum surowego Markdown

**Ślad kodu:** [`assemble_bundle.py` linia 263](https://github.com/elconcept/derecho-pl/blob/18f6fffc8bc1a82677ebe9b88dc1d60fdf7fa096/plugins/model-document-converter/skills/model-ocr/scripts/assemble_bundle.py#L252-L270).

W prostych komórkach użyto `html.escape`. Tekst laboratoryjny `[< 0,1]` przechodzi do surowego MD jako `[&lt; 0,1]`; `D-dimer & INR` jako `D-dimer &amp; INR`. Renderer Markdown może pokazać znak poprawnie, ale analizujący surowy plik LLM widzi dodatkowe tokeny. Zalecam zachowywanie dosłownych operatorów i ampersandów, o ile standardowa tabela GFM nie wymaga ich ucieczki; bezwzględnie uciekać jedynie znaki zakłócające separator komórek oraz backslash. Przetestować dokładność cytatów i parsowanie tabel.

### DPL-06 / P2 — ograniczenia dystrybucji i niezależności testów

- Źródłowe GitHub **nie zawiera** wymaganej binarnej czcionki `DejaVuSans.ttf`. `prepare_font.py` wymaga dokładnego hasha i przeszukuje wyłącznie kilka typowych ścieżek systemów Linux lub jawnie wskazany plik/env. Na Linux używanym w tym audycie wskazany systemowy font ma właściwy SHA-256, ale zwykły Mac/Windows bez tego zasobu może zablokować uruchomienie. Dołączyć sprawdzony sposób provisioningu wieloplatformowego, bez nieautoryzowanego pobierania fontów i bez umieszczania fontów w raporcie.
- W drzewie tego commita nie ma `.github/workflows`; testy 83/83 istnieją jako zapis wyniku autora, nie jako automatycznie publikowany status CI. Zalecam GitHub Actions z tym samym test suite i bez danych pacjentów, a także dołączenie odtwarzalnego syntetycznego smoke bundle.
- Nie ma pomiaru rzeczywistej skuteczności odczytu MODEL na setkach stron ani testu wydajności dwukrotnego stage/seal i renderów. Nie należy z tego wywodzić limitu prędkości ani gwarancji jakości; dodać benchmark na zróżnicowanym korpusie, z liczbą tokenów (nie tylko znaków), pamięcią, czasem i pokryciem stron.

## 4. Status wcześniejszych 17 ustaleń

**Definicje:** `wdrożone` = zabezpieczenie jest w aktualnym kodzie i ma testy autora; **nie oznacza** pełnego niezależnego zatwierdzenia. `częściowo` = naprawiono pierwotny kontrprzykład, lecz wskazano pokrewne ryzyko aktualnego zachowania.

| ID | Ocena 0.2.0 | Podstawa |
|---|---|---|
| G62-01 (P0) | **wdrożone** | `content_chunks` weryfikuje wszystkie reprezentacje; siatka i relacje komórek sprawdzane na słowach PDF |
| G62-02 (P0) | **wdrożone** | `verify_bundle_inputs` wywoływane w stage/seal, rzeczywisty typ, związanie oryginał→baza i raw |
| G62-03 (P1) | **częściowo** | jest mapowanie unikatowych słów; nadal przechodzą całostronicowe bboxy i nieweryfikowane wizualne regiony (DPL-01/02) |
| G62-04 (P1) | wdrożone | patch ograniczony do całych słów; odmowa wielowyrazowej poprawki |
| G62-05 (P1) | wdrożone | obowiązkowe `_retained_hidden_geometry` w QA |
| G62-06 (P1) | wdrożone przez odrzucenie wariantu | wysokie głębie obrazów są jawnie nieobsługiwane zamiast obcinane |
| G62-07 (P2) | wdrożone | podgląd renderowany z bazy PDF; zachowanie alpha |
| G62-08 (P1) | **częściowo** | opis elementu wizualnego wymagany; jego bbox nie ma samodzielnego testu wizualnego (DPL-02) |
| G62-09 (P1) | wdrożone | raport podpisów wymagany i wiązany z oryginałem; kryptografia nie jest powtarzana przy seal |
| G62-10 (P1) | wdrożone | wypełniony malformed /Sig odróżniony od braku podpisu |
| G62-11 (P1) | wdrożone | deterministyczny rdzeń LOG odtwarzany w seal |
| G62-12 (P2) | **częściowo** | ochrona celu deduplikacji poprawiona, ale błędna klasyfikacja do bezpiecznej roli może usunąć wartości (DPL-03) |
| G62-13 (P2) | wdrożone | oddzielne typy znaczników czasu |
| G62-14 (P2) | wdrożone | attempted/performed/completed wyliczane z konkretnych wyników |
| G62-15 (P2) | **częściowo** | compact i GFM wdrożone; pozostałe ryzyko pomijania i encji HTML (DPL-03/05) |
| G62-16 (P2) | wdrożone | wymaganie struktury tabeli i zgodności tekstu, komórek, układu |
| G62-17 (P3) | wdrożone | niepuste odpowiedzi; walidacja text/lines/cells bez planu |

## 5. Minimalny zestaw testów do v0.2.1

1. `test_repeated_text_with_fullpage_boxes_rejected` — DPL-01; kontrola precyzji regionu, nie tylko unikatowości dopasowania.
2. `test_visual_signature_wrong_bbox_not_auto_verified` — DPL-02; test rozdziału OCR i weryfikacji wizualnej.
3. `test_mislabeled_lab_result_or_receipt_cannot_be_omitted` — DPL-03; ochronić wartości i oświadczenia nawet przy błędnej roli.
4. `test_two_column_natural_reading_order` — DPL-04; zweryfikowane kolumny nie mogą powodować fałszywego FAIL przy poprawnym obrazie i tekście.
5. `test_gfm_source_operators_are_plaintext_searchable` — DPL-05; cytat `< 0,1` nie wymaga HTML-entitizacji w surowym MD.
6. Integracyjny smoke na rzeczywistym układzie z dokumentu 5WSK (bez publikowania prywatnej treści w publicznym repo): różne stopki z datą wydruku, nadruki i pieczęć różnych lekarzy, puste pola, wyniki panelu podzielone na dwie strony, powtarzające się słowa, brak deduplikacji istotnych oświadczeń; porównanie MD→JSON→PDF.
7. Automatyczna suita w CI z niezmiennym artefaktem syntetycznego PDF/MD/JSON/LOG i publikowanym raportem dla tego samego commita.

## 6. Reprodukcja

Dołączone w ZIP skrypty są reprodukcjami **wyłącznie syntetycznymi**. `current/content_geometry.py` jest bajtową kopią pliku z audytowanego commita (SHA-256 potwierdzony). Uruchom z PyMuPDF (`fitz`) dostępnym w środowisku:

```bash
python probe_visual_bbox.py
python probe_oversized_bbox.py
python probe_column_gate.py
python probe_md_roles.py
```

`probe_column_gate.py` obrazuje warunek kolejności z obecnego `qa()` na wyniku PyMuPDF; **nie jest wywołaniem całej funkcji `qa()` aktualnego pluginu**. `probe_md_roles.py` odtwarza gałąź ochrony/odszumiania, **nie całe stage/seal**. Tylko dwa pierwsze używają bezpośrednio dokładnego, aktualnego `content_geometry.verify_document_geometry`.

## 7. Decyzja dla autora

**0.2.0 jest wyraźnym postępem i naprawia deklarowane pierwotne P0 na poziomie kodu.** Nie zamyka jednak w pełni ryzyka G62-03 i części skutków G62-08/G62-12: dodatni wynik walidacji geometrii nie wystarcza do pewnej lokalizacji cytatów graficznych ani do odrzucenia ogromnych bboxów. Dla zastosowania, w którym MD służy do wyszukiwania findings, JSON do wstępnej weryfikacji, a PDF do oceny obrazu, rekomenduję **testy i korekty DPL-01–03 przed uznaniem walidacji za wystarczającą do automatycznego odbioru**. DPL-04–06 można rozliczyć w następnej iteracji, z osobnymi testami.

Nie wykonano w tym audycie oceny istnienia przestępstwa ani autentyczności dokumentacji szpitala. Ustalenia dotyczą wyłącznie narzędzia i jego zabezpieczeń.
