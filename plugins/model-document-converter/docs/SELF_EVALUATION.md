# Samoocena scalenia wiedzy i wymagań — 0.2.0

## Co ta samoocena stwierdza

Pięć źródeł rozliczono regułami, a nie samymi nazwami skilli. Powstał jeden workflow konwersji MODEL. Wiedza o typach, stronach, geometrii, cytatach, polskiej typografii, tabelach, niepewności i podpisach pozostaje w instrukcjach i referencjach. Wiedza o konceptach prawnych oraz granicach dokumentów została zachowana referencyjnie; nie dopisuje wniosków do transkrypcji.

Mapa obejmuje dotychczasowe **95 reguł** (O01–O06, C01–C26, T01–T15, A01–A25, S01–S11, U01–U12). Przyjęty przez użytkownika audyt G62-01…G62-17 rozliczono dodatkowo w [AUDIT_REMEDIATION.md](AUDIT_REMEDIATION.md), bez ponownego odtwarzania baseline 0.1.0. Zmiany 0.2.0 aktualizują poniższe dyspozycje, a nie usuwają śladu wcześniejszych wymagań.

Nowsza decyzja użytkownika ma pierwszeństwo nad pierwotnym żądaniem pełnych tagów stron: domyślnie MD podaje nazwę raz i `[s. x]`, dopuszcza kontrolowaną reorganizację, a `legacy_pages` zachowuje stary format opcjonalnie. Wersja kontraktu i hash źródła przeniesiono z publicznego JSON do review/LOG; to zmiana miejsca zapisu, bez usunięcia kontroli integralności.

**Dyspozycja reguły nie jest wynikiem testu.** Poniższe tabele rozliczają zachowanie wiedzy i projektową zmianę zachowania. Wykonanie helperów, wynik walidacji, instalacja oraz zapis na Drive wymagają osobnych dowodów w [SMOKE_TEST.md](SMOKE_TEST.md). Nie deklaruje się uniwersalnej gwarancji 100% poprawnego OCR ani wykonania testu na dokumentacji medycznej użytkownika bez faktycznego przetworzenia takiego pliku.

Legenda: **K** zachowane; **A** dostosowane; **R** świadomie usunięte/wyłączone z tego workflow; **D** naprawiana wada źródła lub wcześniejszego wydania; **N** nowe wymaganie; **U** wykonanie lub zdolność niepotwierdzona. Kilka oznaczeń w wierszu oznacza różne aspekty tej samej reguły. Źródła O/C/T/A/S i ich hashe definiuje [SOURCE_PROVENANCE.md](SOURCE_PROVENANCE.md).

Miejsca docelowe: **CF** = [content-fidelity.md](../skills/model-ocr/references/content-fidelity.md); **MED** = [medical-evidence.md](../skills/model-ocr/references/medical-evidence.md); **RK** = [retained-knowledge.md](../skills/model-ocr/references/retained-knowledge.md); **SC** = [document.schema.json](../skills/model-ocr/references/document.schema.json); **SMOKE** = [SMOKE_TEST.md](SMOKE_TEST.md). Główne wykonanie opisuje [SKILL.md](../skills/model-ocr/SKILL.md).

## OpenDataLoader — O

| ID | Status | Reguła i dyspozycja | Ślad źródłowy | Miejsce docelowe |
|---|---|---|---|---|
| O01 | K/A | Kolejność czytania, kolumny, nagłówki i pełna struktura JSON pozostają; odczytu dokonuje MODEL. | O:SKILL.md:3,23–27,59–65 | CF; SC |
| O02 | K/A | Tabele wielostronicowe, wzory i opisy obrazów zachowane bez silnika enrich. | O:SKILL.md:45–48,59–65 | CF; RK |
| O03 | K/A | Kontrola ukrytego tekstu poprzez porównanie z obrazem; stara warstwa nie jest źródłem prawdy. | O:SKILL.md:48 | CF |
| O04 | A/R | Obsidian Vault/frontmatter i ścieżki osoby zastąpiono Drive `Konwerter/<nazwa>/`; bez pytania do innego użytkownika o batch >10. | O:SKILL.md:67–86 | SKILL; CF |
| O05 | K/D | Oryginały nienaruszone; wznowienie wymaga hasha, wersji/parametrów i walidacji całego bundle, nie samego istniejącego MD. | O:SKILL.md:82–86 | CF; RK |
| O06 | R | Usunięto Java/OpenDataLoader/MarkItDown jako silniki OCR i stare benchmarki jako obietnice MODEL; usunięto kancelaryjne reguły anonimizacji. | O:SKILL.md:12–20,50–65,88–112 | RK; notices |

## Kontrakt dokumentu — C

| ID | Status | Reguła i dyspozycja | Ślad źródłowy | Miejsce docelowe |
|---|---|---|---|---|
| C01 | K/A | Jeden kontrakt źródła, stron, ID, tekstu i geometrii; wersjonowanie w schemacie/LOG, bez `schema_version` w publicznym JSON 0.2.0. | C:SKILL.md:130–157; scripts/contract.py:18–46,108–128 | SC; CF; output-contract |
| C02 | K/A | Zachowano 11 typów bazowych; jawnie dodano `signature_field`, `handwriting`, `logo`. | C:scripts/contract.py:18–21; references/prompt_vlm_ocr_pl.md:38–44 | SC; RK |
| C03 | K/A | Jeden publiczny układ współrzędnych znormalizowanych: displayed CropBox, początek lewy górny, xyxy. | C:SKILL.md:156; references/prompt_vlm_ocr_pl.md:29–36 | SC; CF |
| C04 | K/D | Zakaz zgadywania bbox; 0.2.0 wiąże wymiary z faktycznym CropBox oraz każde wystąpienie słowa z geometrią, bez powtórnego użycia jednego trafienia. | C:scripts/adapters/pdf_inspector.py:16–19,48–58 | CF; content_geometry; G62-03 |
| C05 | K/A | Odczyt i lokalizacja to niezależne kontrole, bez fikcyjnych confidence. Stan procesu pozostaje poza JSON treści. | C:SKILL.md:159–176; scripts/contract.py:49–105 | CF; SC |
| C06 | K | Pusty wynik ekstrakcji nie oznacza sukcesu; każdy oryginalny numer strony musi być reprezentowany. | C:scripts/contract.py:65–86 | CF |
| C07 | K/D | Mianownik z oryginału; pełny, uporządkowany zbiór stron, bez luk i duplikatów. | C:SKILL.md:263–269,294–296; scripts/split_packet.py:266–310 | CF; SMOKE |
| C08 | K/D | Rozdzielono pusty skan, ilustrację, nieczytelny tekst i awarię ekstrakcji. | C:scripts/adapters/liteparse.py:7–12,84–94 | CF; SC |
| C09 | K | Obejmuje każdą stronę PDF mieszanego; native text wymaga sprawdzenia na obrazie. | C:SKILL.md:238–256; scripts/routing_gate.py:124–160 | CF |
| C10 | K/A | Kontrola złych mapowań znaków, garbled text, kolejności kolumn i braków warstwy. | C:scripts/pdfi_extract.py:8–26; adapters/pdf_inspector.py:110–118,164–183 | CF; SMOKE |
| C11 | K/A | Wygląd pól i adnotacji w renderze; raw nienaruszony; ewentualny flatten tylko kopii roboczej. | C:references/render_skanu_pl.md:7–17,27–37 | RK; CF |
| C12 | K/N | Zachowana formuła DPI z minimum 192 i celem 1024 na krótszym boku; dodana eskalacja cropów/DPI. | C:references/render_skanu_pl.md:19–21,32–37 | RK; SKILL |
| C13 | K/A/D | Zachowano źródłową wiedzę RGB/LANCZOS i cel 1536 px. Bieżący podgląd renderuje przygotowany PDF RGB na bieli, bez bezpośredniej konwersji/LANCZOS; świadoma zmiana dla zgodności alpha. Raw/orientacja/klatki pozostają; high-bit/float odrzucane przed bazą. | C:references/render_skanu_pl.md:22–23 | RK; CF; G62-06/07 |
| C14 | K | Kolejność czytania z układu, nie naiwne sortowanie y/x. | C:references/prompt_vlm_ocr_pl.md:29–36 | CF; SC |
| C15 | K/D | Struktura tabel wymagana: komórki, scalenia i nagłówki; każda obecna reprezentacja text/lines/cells kontrolowana. GFM dla prostych tabel, HTML dla koniecznych relacji. Listy/checkboxy/typografia zachowane. | C:references/prompt_vlm_ocr_pl.md:46–51; adapters/vlm_html.py:108–110,127–140 | CF; SC; G62-01/15/16 |
| C16 | K | Tylko treść widoczna; błędy autora zachowane, błędy OCR poprawiane z obrazu. | C:references/prompt_vlm_ocr_pl.md:53–61 | CF |
| C17 | K/A/D | Pieczęć/podpis/pismo odręczne jako treść i region; niepusty opis obowiązkowy, odczyt słów odrębny. `include` nie może niczego nie wyemitować. | C:references/prompt_vlm_ocr_pl.md:41–44,59–61; scripts/signature.py:1–13 | CF; MED; SC; G62-08 |
| C18 | K/A/D | Ponowne oglądanie, potem konkretne pytanie przed bundle; question/answer są niepustymi ciągami po strip. Brak obowiązku pytania o wszystko dlatego, że confidence=null. | C:references/prompt_vlm_ocr_pl.md:53–70 | CF; SKILL; G62-17 |
| C19 | K/A | Kontrola ucięć i modelowych powtórzeń; naturalne powtórzenia dokumentu pozostają. | C:scripts/degeneracja.py:1–49; normalize.py:116–126 | RK; CF |
| C20 | K/A/D | Tożsamość z oryginalnych bajtów; raw porównany hashem. W 0.2.0 hash w review/LOG, poza publicznym JSON; oba etapy potwierdzają też rzeczywisty typ i więź raw→base. | C:scripts/contract.py:44–46,108–128; normalize.py:63–64,143–147 | CF; output-contract; G62-02/15 |
| C21 | K/A | Normalizacja typografii służy porównaniu z mapą offsetów, nie modyfikacji źródła. | C:SKILL.md:210–227; scripts/evidence.py:147–243 | RK; CF |
| C22 | K/A | Zachowana wiedza o sile cytatu, wielu trafieniach i dopasowaniu między blokami; brak indeksu/findings. | C:SKILL.md:178–202; evidence.py:20–52,267–329 | RK; SC |
| C23 | K/A/D | Nagłówki/stopki mogą zawierać dane chronione, także status w opisie grafiki. MD odszumiony, OCR/JSON pełne; oba końce deduplikacji muszą być niechronioną formą. | C:scripts/liteparse_extract.py:17–19,55–57,81–84 | CF; MED; G62-12 |
| C24 | K | Dokumentacja, schemat i helpery muszą zgadzać się; testy mają sprawdzać realne ryzyka. | C:SKILL.md:361–374; tests/test_dokumentacja_zakotwiczona.py:63–222 | SELF; SMOKE |
| C25 | K | UTF-8, Unicode/diakrytyki, CRLF/LF i granice stron zachowane. | C:scripts/normalize.py:39–43,156–158; tests/test_encoding_crlf.py:21–39 | CF; RK; SMOKE |
| C26 | K/A/R | Praca partiami i jawne limity; bez cichego obcięcia. Nie rozszerzono zakresu na DOCX/OOXML. | C:scripts/routing_gate.py:63–74,175–245; liteparse_extract.py:13–16 | RK; SKILL |

Dodatkowe wady C rozliczono jako **D**: zbyt luźny schemat bbox → dokładnie cztery skończone współrzędne, zakres/kolejność i per-page geometria; `exit 0` przy zdegradowanej zawartości → osobna bramka kompletności; „pierwsze trafienie” → zakaz pozornej unikalności; regex MediaBox → odczyt prawdziwego CropBox/obrotu; wizualny podpis → osobna detekcja PDF. Dowody: `C:contract/contract.schema.json:75–110`, `scripts/normalize.py:149–158`, `scripts/evidence.py:262–264,284–295`, `scripts/pdfi_extract.py:40–60`, `scripts/signature.py:17–36`. Miejsca docelowe: CF, RK, SC, SMOKE.

## LLM tier — T

| ID | Status | Reguła i dyspozycja | Ślad źródłowy | Miejsce docelowe |
|---|---|---|---|---|
| T01 | K/A | Oddzielenie struktury, transkrypcji, konceptów i sprawdzania cytatu. | T:SKILL.md:39–47 | RK; CF |
| T02 | K/A | Każdy odczyt ma podstawę na stronie i w regionie; referencja zdaniowa/akapitowa zachowana jako zasada. | T:SKILL.md:5–9,97–111 | CF; SC |
| T03 | K/D | Wygenerowanie refs nie zastępuje niezależnego sprawdzenia obrazu. | T:SKILL.md:110–115; references/wzorce_konceptow_prawnych.md:58 | CF; RK |
| T04 | K/D | `grounded` oznaczało tylko obecność refs; nie zamienia się tego w fikcyjny procent. | T:scripts/ekstrakcja_llm.py:110–119 | CF |
| T05 | A | Niepewny odczyt wymaga czynnej bramki przed finalizacją, nie flagi na później. | T:SKILL.md:113–115,157–159 | CF; SKILL |
| T06 | K/A | Precyzyjne pola kotwiczone precyzyjnie; szersza kategoria nie zastępuje słów źródłowych. | T:references/wzorce_konceptow_prawnych.md:55 | RK; CF |
| T07 | K/A | Wiedza string/numeric/boolean/date zachowana; źródłowego formatu dat/kwot nie zastępuje się znormalizowaną wartością. | T:SKILL.md:80–95 | RK |
| T08 | A | Uzasadnienia/komentarze procesu przeniesione do LOG, poza MD/JSON. | T:references/wzorce_konceptow_prawnych.md:56–57; scripts/ekstrakcja_llm.py:218–233 | CF |
| T09 | K/A | Pełny zestaw wskazówek umowa/wyrok/pismo zachowany referencyjnie. | T:references/wzorce_konceptow_prawnych.md:7–50 | RK |
| T10 | K/A | Dzielenie dużej pracy na partie zachowane, bez backendowego ograniczenia do słabego modelu lokalnego. | T:references/wzorce_konceptow_prawnych.md:57 | RK |
| T11 | R | contextgem/Ollama/LiteLLM/API-base i klucze silnika zastąpione aktualnym MODEL. | T:SKILL.md:49–78; scripts/ekstrakcja_llm.py:124–141 | RK; SKILL |
| T12 | R | Usunięto pre-model anonimizację, cloud-allow i firmową lokalność/EOG. | T:SKILL.md:49–55,147–155 | RK |
| T13 | A/R | Nie składa się pisma; autoryzowany zapis Drive nie przejmuje kancelaryjnej bramki wysyłki. | T:SKILL.md:153–163 | SKILL |
| T14 | R | Dawne TXT/DOCX jako wejście warstwy konceptowej nie rozszerza zakresu PDF/obrazy. | T:scripts/ekstrakcja_llm.py:150–153,180–206 | RK |
| T15 | K/A | Zachowano pochodzenie/noty; dawna zależność nie jest aktywnym runtime. | T:LICENSE:1–23 | THIRD_PARTY_NOTICES |

## Akta — A

| ID | Status | Reguła i dyspozycja | Ślad źródłowy | Miejsce docelowe |
|---|---|---|---|---|
| A01 | K/N | Nienaruszony oryginał, SHA-256, nowy jawny folder raw. | A:SKILL.md:52; scripts/akta.py:147–152 | CF |
| A02 | A | Pierwotny tag nazwa/Page x/y zastąpiony najnowszym poleceniem: nazwa raz + `[s. x]`; `legacy_pages` opcjonalny. Reorganizacja MD zachowuje przypisanie każdego bloku. | A:scripts/akta.py:203–210; nowsza decyzja użytkownika | CF; SKILL; G62-15 |
| A03 | K/A/D | Liczba stron i brak page_errors nie wystarczają; JSON/PDF mają dokładne 1…N. MD pokrywa każdą stronę, także przy powrocie odsyłacza po reorganizacji. | A:SKILL.md:69–77; tests/test_akta.py:88–104 | CF; output-contract; SMOKE |
| A04 | K/A | Zachowano lekcję cichego limitu 1000; brak dowolnej deklaracji nieograniczonego kontekstu. | A:scripts/liteparse_extract.py:13–18,48,57–59 | RK |
| A05 | K/A/D | Obraz bez tekstu wymaga obejrzenia; nieczytelność rozstrzygana przed zakończeniem. | A:scripts/akta.py:191–200; tests/test_akta.py:80–85 | CF |
| A06 | A | Stałe 300 DPI zastąpione formułą z C i adaptacyjną eskalacją. | A:scripts/liteparse_extract.py:22–23,48–59 | RK |
| A07 | K/A | Nie usunąć sygnatury ze wszystkich stron przez odszumienie. | A:scripts/liteparse_extract.py:19–21,83–95 | CF; MED |
| A08 | K/D | Residual znaków nie dowodzi poprawności; pełne porównanie bloków i globalne jednoznaczne przypisanie wystąpień do regionów strony. | A:scripts/liteparse_extract.py:116–120 | CF; content_geometry; SMOKE |
| A09 | K/A | Rodzaj i geometria bloków/fragmentów, wymiary stron; jawne przeliczenia. | A:scripts/liteparse_extract.py:74–95 | SC; CF |
| A10 | K | Markery list i relacje komórek zachowane. | A:scripts/liteparse_extract.py:108–113 | CF; SC |
| A11 | A/D | Naprawa `$`/`§`, `l/I/1` tylko po obejrzeniu; prawdziwa waluta zachowana. | A:scripts/akta.py:117–144,188–190 | CF; RK |
| A12 | K/A | Język źródła, bez tłumaczenia; dokument mieszany nie podlega jednej regule walut. | A:SKILL.md:47–50; tests/test_akta.py:176–191,225–233 | CF; RK |
| A13 | K/D | Wznowienia z hashem, wersją i walidacją, bez zaufania do samego `KOMPLET`. | A:scripts/akta.py:170–180,248–266 | RK |
| A14 | K/A | Ochrona przed kolizją nazw przeniesiona do katalogów Drive/bundle. | A:scripts/akta.py:213–218,245–247 | SKILL |
| A15 | K/A | Równość bajtów i tekstu to różne rzeczy; nie usuwa się stron ani różnic wizualnych. | A:scripts/akta.py:155–157,239–243,267–271 | RK; CF |
| A16 | A | Porównanie cytatu z oryginałem realizowane w pipeline, nie dopiero po oddaniu użytkownikowi. | A:SKILL.md:74 | CF |
| A17 | A/D | Raport działań/stanu zastąpiony LOG; deterministyczny rdzeń weryfikowany przez seal, dostawa tylko przez record-delivery. MD/JSON wolne od procesu. | A:scripts/akta.py:290–316 | CF; SKILL; G62-11 |
| A18 | D | Poprawna warstwa native text nie stanowi wady/uwagi sama z siebie. | A:scripts/akta.py:291–294,310–312 | CF |
| A19 | A | Zwięzły postęp; finalnie tylko ZIP bundle i link Drive, bez renderów/plików pośrednich. Pytania nadal pokazują potrzebny kontekst. | A:SKILL.md:78; scripts/akta.py:274–286 | SKILL |
| A20 | R | Indeks FTS5, szukaj.py, stemming/folding jako etap akt wyłączone na żądanie. | A:SKILL.md:55–61; scripts/szukaj.py:1–68 | RK |
| A21 | K/A | Preflight realnych możliwości renderu/zapisu/walidacji i zasobów; bez pozornego wykonania. | A:scripts/akta.py:400–455 | SKILL; SMOKE |
| A22 | A/R | Dawna diagnostyka Smart App Control usunięta; brak automatycznego wyłączania zabezpieczeń. | A:scripts/akta.py:387–397 | SKILL |
| A23 | R | Brak pobierania tessdata i uruchamiania LiteParse; nie przeniesiono starych szybkości/CER jako obietnic MODEL. | A:SKILL.md:36–50,83–88 | RK |
| A24 | N/A/D | PDF i jawnie obsługiwane obrazy/klatki z mapowaniem; nieobsługiwane high-bit/float i transformacje nie są cicho konwertowane. | A:SKILL.md:93; U1 | CF; SKILL; G62-06/07 |
| A25 | R | Usunięto anonimizację, redakcję i blanket gate wspólnej kancelaryjnej wtyczki. | A:SKILL.md:101–125 | RK |

## Podpisy — S

| ID | Status | Reguła i dyspozycja | Ślad źródłowy | Miejsce docelowe |
|---|---|---|---|---|
| S01 | K/A/D | Podpisy wykrywa struktura PDF; puste pole/obraz podpisu odrębne. Wypełniony kandydat z wadliwym ByteRange nie staje się not_present. | S:waliduj_podpis.py:109–114; C:scripts/signature.py:17–57 | RK; MED; G62-10 |
| S02 | K/N | Badanie na oryginale przed przekształceniem; kopia raw; pochodna nie dziedziczy podpisanych bajtów. | S:SKILL.md:39–48 | RK; CF |
| S03 | K | Walidacja jest odczytowa; plugin niczego nie podpisuje. | S:SKILL.md:39–42; waliduj_podpis.py:4–8,201 | RK |
| S04 | K/D | Integralność, zakres rewizji i późniejsze zmiany rozdzielone; nie każda późniejsza rewizja to nadużycie. | S:waliduj_podpis.py:70–84,156–169 | RK |
| S05 | K/A/D | Pełny signature_report z check(source), certyfikaty/czasy/modyfikacje w LOG; powiązanie raportu z aktualnym oryginałem wymagane w obu bramkach. | S:waliduj_podpis.py:29–57,135–173 | RK; output-contract; G62-09 |
| S06 | K/D | Czas deklarowany, content timestamp, signature timestamp i document timestamp oraz ich walidacja są odrębne. Brak jednego nie oznacza braku pozostałych. | S:waliduj_podpis.py:145–154 | RK; G62-13 |
| S07 | K/U | Zaufanie/kwalifikowany status wymagają rzeczywistego narzędzia i źródeł; brak takiej integracji nie jest dowodem nieważności. | S:SKILL.md:98–106; waliduj_podpis.py:104–107,175–200 | RK; SMOKE |
| S08 | A/D | Brak podpisu = normalne pominięcie kryptografii; obraz = nie dotyczy; nieustalona detekcja nie jest brakiem. Pełny raport stanu jest wymagany dla każdego wejścia, bez wymuszania kryptografii. | S:SKILL.md:80–83,114–116; waliduj_podpis.py:216–241 | RK; MED; G62-09/10 |
| S09 | R/A | Usunięto ścieżki/firmowe gates; helper kryptograficzny pozostaje technicznie odrębny od silnika OCR. | S:SKILL.md:28–32,50–75,150–164 | RK |
| S10 | D | Nie przekształcać unknown w invalid ani ukrywać dalszych podpisów. Attempted/completed/performed i wyniki częściowe rozdzielone; błąd przed obliczeniami nie potwierdza ich wykonania. | S:waliduj_podpis.py:70–74,90–92,109–192 | RK; SMOKE; G62-14 |
| S11 | K/A | Serializacja zwykłych wartości; historyczne testy źródła nie są dowodem bieżącej weryfikacji. | S:waliduj_podpis.py:119–125; SKILL.md:118–136 | RK; SMOKE |

## Nowe wymagania i regresje użytkownika

| ID | Status | Wymaganie | Miejsce docelowe / kryterium |
|---|---|---|---|
| U01 | N | Jeden Skill MODEL; narzędzia tylko techniczne; nowe odczyty i ocena obrazu wykonywane przez MODEL. | SKILL; CF |
| U02 | N | Pełny bundle: raw, searchable PDF, MD, typed bbox JSON i LOG; ZIP oraz Drive. | SKILL; assembler; SMOKE |
| U03 | N | PDF bazą pochodnej; źródłowe obrazy bez zmiany rozdzielczości i rekompresji. | CF; test strumieni i wymiarów obrazów |
| U04 | N/A/D | Zakaz wieloliniowego insert_text; patch tylko całych pojedynczych słów z oryginalną geometrią, skany z liniami/słowami. Ochrona zachowanego OCR w keep/patch bez opcjonalnych search checks. | CF; G62-04/05; test pozycji i braku przepełnienia |
| U05 | N | Textbox tylko rc≥0 z dopasowanym fontem; sprawdzenie Unicode i pozycji. | CF; SMOKE |
| U06 | N | Zero znaków poza stroną, tolerancja 2 pt; wyszukiwanie na właściwej stronie i w właściwym bbox. | CF; SMOKE |
| U07 | N/D | 100% bloków per strona, każde wystąpienie i wszystkie text/lines/cells porównane z warstwą; zero starego sprzecznego lub podwójnego OCR. | CF; assembler/content_geometry; G62-01/03/16/17 |
| U08 | N/A/D | Kontakty/bannery/ankiety oraz rutynowe dane administracyjne/instrukcje nośnika odszumione w MD, pełne w OCR/JSON. Samo słowo pacjent nie blokuje ankiety; osoby/daty/status/istotne warianty chronione; mieszane bloki rozdzielone. | MED; SC evidence_roles; G62-12/15 |
| U09 | N | Wszystkie ważne daty, autorzy, pieczęcie, podpisy, PESEL/PWZ/NPWZ, identyfikatory i dane lab zachowane. | MED; SC; SMOKE |
| U10 | N | Puste pole podpisu opisane tylko w rzeczywistym miejscu; różne nazwiska zachowane w miejscu; brak modelowych oskarżeń. | MED; CF |
| U11 | N/D | Optymalizacja fontów/deflate nie ma prawa zmienić źródłowych strumieni obrazów; końcowy zapis musi potwierdzić ten niezmiennik. | CF; SMOKE |
| U12 | N | Odpowiedź końcowa nie załącza plików pojedynczych ani PNG; pytania o niepewność przed finalnym ZIP. | SKILL; CF |

Własne sprawdzenie wykonawcze helpera ujawniło dodatkową pułapkę: `deflate=True` może skompresować wcześniej nieskompresowany strumień obrazu mimo `deflate_images=False`. Wymaganie zachowania oryginalnych strumieni ma pierwszeństwo przed samym zestawem flag. Implementacja powinna optymalizować fonty, odtworzyć dokładne źródłowe strumienie/filtry obrazów i zapisać wynik bez ponownej kompresji; ostateczny dowód stanowi test inwariantu, nie opis flag. Szczegółowe wykonanie i wynik wpisuje się do SMOKE.

## Świadome zmiany zakresu — nie ukryta utrata wiedzy

- **Format MD i publiczny JSON w 0.2.0:** najnowsze polecenie zastępuje obowiązkowe długie tagi krótkimi odsyłaczami, dopuszcza permutację bloków z zachowaniem stron i stosuje GFM tam, gdzie wystarcza. Wersja/hash przechodzą do LOG; kontrola pochodzenia jest dodatkowo wzmacniana. Dawny format MD pozostaje opcjonalny.
- **Podgląd i zakres obrazów:** źródłowa reguła RGB/LANCZOS pozostaje zapisana jako wiedza. Wykonanie 0.2.0 używa renderu bazy PDF na bieli dla zgodnego alpha, zachowuje cel minimum 1536 px i nie zmienia próbek bazy. High-bit/float są jawnie nieobsługiwane zamiast pozornie bezstratnego obcinania.
- **Backend i anonimizacja:** usunięte na wyraźne polecenie. Nie przeniesiono również bannerów „zero LLM/zero cloud”, które przeczyłyby nowemu workflow.
- **Indeks/search akt:** wyłączone na wyraźne polecenie jako inny etap. Zachowano stronę, plik, bbox i dokładny tekst potrzebne przyszłej analizie.
- **Automatyczne dzielenie teczki na osobne pliki:** niewykonywane w bundle dla jednego wejścia. Wiedza o granicach, kategoriach i mylących nagłówkach pozostaje w RK.
- **Inferowane koncepty i porada prawna:** wzorce zachowane w RK; nie powstaje dodatkowy raport ryzyk, teza orzeczenia ani streszczenie jako transkrypcja.
- **DOCX/OOXML:** nie są deklarowanym wejściem nowego produktu. Zachowano ogólną zasadę pełności i jawnych błędów, bez starych backendowych ścieżek.
- **Historyczne liczby jakości i wydajności:** pozostają informacją o źródłach, nie obietnicą nowego MODEL.
- **Licencje i pochodzenie:** zachowane dostarczone noty; wskazano brak osobnego LICENSE dla C i kopiowany opis contextgem w A/S. Nie przypisano nowych zależności na podstawie tego błędu.
- **Publiczny katalog pluginów:** nie jest celem prywatnego produktu. Walidator publicznej dystrybucji może zgłaszać wymagania publicznych URL; nie fabrykuje się takich danych, aby uzyskać zielony wynik. Prywatny pakiet sprawdza się według aktualnego kontraktu.

## Rzeczy, których nie wolno oznaczyć jako dowiedzione samą instrukcją

Do odrębnej walidacji należą: zgodność wszystkich ścieżek z manifestami, wykonane testy PDF/JSON/MD, geometrii i strumieni, deterministyczność ZIP, kontrola czystego rozpakowania, rzeczywista instalacja oraz odczyt/zapis/weryfikacja w Google Drive. Status tych czynności znajduje się wyłącznie w SMOKE i dowodach wykonania.

Kryptograficzna walidacja prawdziwego podpisanego dokumentu, ocena kwalifikowanego statusu podpisu, przetestowanie prywatnej dokumentacji medycznej użytkownika i uniwersalna dokładność OCR pozostają **U**, jeśli brak konkretnych wejść/narzędzi i zapisanych wyników. Nie należy usuwać tego rozróżnienia tylko dlatego, że schemat, instrukcja lub syntetyczny test przeszły walidację.
