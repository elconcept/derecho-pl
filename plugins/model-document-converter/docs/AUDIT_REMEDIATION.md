# Rozliczenie przyjętego audytu — wydanie 0.2.0

## Podstawa i zakres

Użytkownik przyjął jako potwierdzone wszystkie **17 ustaleń G62-01…G62-17**
z przekazanego audytu 0.1.0 (`audyt_gpt62_010/findings.json` i towarzyszące
raporty). Nie uruchamiano ponownie baseline ani dawnych reprodukcji w celu
ponownego dowodzenia tych ustaleń. Audyt wejściowy jest materiałem źródłowym,
nie skryptem do wykonania podczas używania pluginu.

Poniższa macierz opisuje zmianę kontraktu i zabezpieczenia obecne w kodzie
0.2.0. **Nie jest raportem wykonania testów.** Wyniki nowych kontroli wydania,
smoke, pakowania, instalacji i dostawy są odrębnie dokumentowane w
[SMOKE_TEST.md](SMOKE_TEST.md) oraz dowodach wykonania. Nie przenosimy liczby
testów ani statusu starszego wydania jako dowodu działania nowej wersji.

Klasyfikacja: **D** poprawka wady; **A** świadoma adaptacja zachowania;
**N** nowy obowiązkowy kontrakt/bramka; **R** celowo wycofany wariant.
Wszystkie wiersze zachowują źródłowy priorytet audytu. Status wykonawczy musi
pochodzić z raportu wydania, nie z samej kolumny „zmiana”.

## Macierz 17 ustaleń

| ID / priorytet | Przyjęty problem | Klasyfikacja i zmiana 0.2.0 | Ślad implementacji / kontraktu | Kryterium kontroli nowej wersji |
|---|---|---|---|---|
| G62-01 / P0 | Poprawne text/lines mogły ukryć błędne cells, więc MD zmieniało wartość tabeli. | **D:** każda obecna reprezentacja jest kontrolowana niezależnie; komórki są kanoniczną strukturą renderowania. Ich tekst i geometria muszą odpowiadać temu samemu źródłu. | `assemble_bundle.py`: `content_chunks`, `validate_content`, `table_markdown`; `content_geometry.py`; output-contract §3/6 | Konflikt wartości, jednostki albo przypisania komórki musi zatrzymać walidację i oba etapy wydania; poprawna tabela zachowuje relacje. |
| G62-02 / P0 | Raw i treść mogły pochodzić z innych dokumentów; deklaracja image obchodziła więź PDF-bazy. | **D/N:** wspólne `verify_bundle_inputs` w stage/seal sprawdza rzeczywisty typ z bajtów oraz `verify_source_base`. PDF-baza jest identyczna z oryginałem; obraz-baza jest sprawdzana względem rzeczywistych klatek/próbek/masek. Inventory jest kontrolą dodatkową. | `assemble_bundle.py`: `verify_bundle_inputs`, `stage`, `seal`; `pdf_pipeline.py`: `_actual_source_kind`, `verify_source_base` | Obca baza, fałszywe kind lub nieaktualny inventory nie mogą przejść żadnej bramki. Poprawne obsługiwane obrazy wieloklatkowe zachowują wszystkie strony. |
| G62-03 / P1 | JSON przyjmował fałszywe wymiary/bbox i dwa wystąpienia w jednym regionie. | **D/N:** wymiary odpowiadają faktycznemu wyświetlanemu CropBox; globalne przypisanie jeden do jednego wiąże słowa PDF z blokami/liniami/komórkami i sprawdza siatkę tabeli. | `content_geometry.py`: `assign`, `verify_grid`, `verify_document_geometry`; output-contract §2/6 | Błędne wymiary, region przeciwnego rogu i wielokrotne użycie jednego trafienia są odrzucane. Obrót/CropBox i rzeczywiste nakładanie elementów pozostają obsługiwane w granicach helpera. |
| G62-04 / P1 | Dopasowanie całej linii zachowywało obrys, lecz przesuwało jej słowa. | **D/R:** patch obejmuje pojedyncze całe słowa/tokeny. Nie akceptuje wnętrza słowa ani wspólnego przeskalowania wielowyrazowej linii. Zachowuje źródłowy bbox edytowanego słowa i chroni sąsiednie. | `pdf_pipeline.py`: `_source_selection`, `_planned_edits`; SKILL §5; content-fidelity | Poprawka krótszego/dłuższego tokenu nie przesuwa sąsiednich słów; odrzucona wielowyrazowa operacja nie jest obchodzona innym trybem bez nowego przeglądu. |
| G62-05 / P1 | Keep pomijało geometrię zachowanego niewidocznego OCR bez opcjonalnych search checks. | **D/N:** obowiązkowa kontrola zachowanych niewidocznych znaków/słów dla keep i nienaprawianej części patch. | `pdf_pipeline.py`: `_retained_hidden_geometry`, `qa`; SKILL §6 | Przesunięta warstwa jest wykrywana również bez search_checks; poprawny keep i lokalna naprawa zachowują resztę geometrii. |
| G62-06 / P1 | Konwersja TIFF I;16 do RGB obcinała poziomy i błędnie deklarowała bezstratność. | **D/A/R:** nieobsługiwane głębie >8 bitów i tryby integer/float są jawnie odrzucane przed zapisem bazy. Nie deklarujemy odzyskania wysokiej głębi ani bezstratnego obcięcia. | `pdf_pipeline.py`: `_image_source_frames`, `_image_base`; retained-knowledge; SELF C13/A24 | Nie powstaje fałszywa biała baza ani deklaracja lossless dla nieobsługiwanego źródła; raw pozostaje nienaruszony. |
| G62-07 / P2 | Bezpośrednie odrzucenie alpha mogło dać jednolicie czarny podgląd. | **D/A:** podgląd jest renderem zweryfikowanej bazy PDF do RGB na białym tle. Zachowuje cel natywnej/minimalnej 1536 px rozdzielczości roboczej. Dawne RGB/LANCZOS pozostaje jako jawnie zaadaptowana wiedza źródłowa. | `pdf_pipeline.py`: `_image_base`; SKILL §3; retained-knowledge; SELF C13 | Kontrast i półprzezroczystość są zgodne z bazą, maska/próbki źródła nie są zastępowane podglądem. |
| G62-08 / P1 | Include podpisu lub grafiki bez tekstu/opisu mogło nie wyemitować informacji. | **D/N:** każdy blok ma treść lub opis; typy wizualne wymagają niepustego visual_description. Każde include musi zwrócić niepusty Markdown. Komórki mogą mieć źródłowy opis stanu. | `assemble_bundle.py`: `VISUAL_TYPES`, `validate_content`, `block_markdown`; schema; medical-evidence | Zaobserwowany ślad podpisu i rzeczywiście puste pole emitują odrębne opisy z bbox; brak tekstu i opisu jest odrzucany. |
| G62-09 / P1 | Raport podpisów mógł być pominięty albo dotyczyć obcego hasha. | **D/N:** pełny `review.signature_report` pochodzi z `check(source)`; validate wymaga kompletnej struktury, stage/seal sprawdzają hash, nazwę, faktyczny typ i ponowną detekcję oryginału. | `check_signatures.py`: `check`, `assert_report_structure`, `validate_report`; `assemble_bundle.py`: `validate_content`, `verify_bundle_inputs` | Brak/obcy/niespójny raport jest blokadą. Rzeczywiste `not_verified` zachowuje powód; poprawny brak podpisu lub obraz normalnie pomija kryptografię. |
| G62-10 / P1 | Wypełniony uszkodzony kandydat /Sig stawał się not_present. | **D:** detekcja odróżnia puste pole od wypełnionego kandydata z wadliwym ByteRange; zachowuje malformed/unknown i przyczynę bez oceny fałszerstwa. | `pdf_pipeline.py`: `detect_signatures`; `check_signatures.py`: `check`, `assert_report_structure`; SKILL §2 | Brak/krótki ByteRange przy wypełnionej strukturze nie daje zwykłego braku; naprawdę puste pole nadal nie jest wadą. |
| G62-11 / P1 | Seal przyjmowało dowolny niepusty LOG po usunięciu ledger/QA/hashów. | **D/N:** stage tworzy deterministyczny rdzeń; seal odtwarza go z aktualnego review/QA/artefaktów i porównuje. Wyłącznie ustrukturyzowane zdarzenia record-delivery mogą dopisać dostawę. | `assemble_bundle.py`: `log_core`, `parse_log`, `record_delivery`, `seal`; google-drive; output-contract §7 | Zastąpienie rdzenia albo nieaktualny hash/rozmiar artefaktu w receipt jest wykrywane; prawidłowe potwierdzenie dostawy nie wymaga samoreferencyjnego hasha LOG/ZIP. |
| G62-12 / P2 | Deduplikacja mogła wskazać chroniony wynik; opis statusu dokumentu nie był chroniony. | **D/N:** oba końce muszą być niechronionymi header/footer/logo, z wcześniejszym uwzględnionym celem. Ochrona obejmuje opisy/linie/komórki i rolę document_status. Mieszane bloki wymagają podziału. | `assemble_bundle.py`: `is_protected`, `validate_content`; schema; medical-evidence | Wynik/podpis/akapit nie jest celem usuwanej stopki. Rutynowy kontakt może zniknąć z MD, lecz status i każde istotne wystąpienie pozostają. |
| G62-13 / P2 | Content timestamp był pomijany przy serializacji czasu. | **D:** czas deklarowany i znaczniki treści, podpisu oraz dokumentu są raportowane osobno; brak jednego rodzaju nie dowodzi braku pozostałych. | `check_signatures.py`: `_optional_timestamp`, `_status_record`, `_timestamp_structure`; retained-knowledge | Każdy rodzaj czasu i jego stan są oddzielne; niezweryfikowany czas/zaufanie nie staje się potwierdzonym. |
| G62-14 / P2 | Flaga performed mogła być true po błędzie przed wykonaniem obliczeń. | **D:** rozdzielono attempted/completed/performed, liczniki i wyniki per podpis; wyjątek przed wynikiem nie oznacza ukończonej kontroli. | `check_signatures.py`: `check`, `_summarize`, `assert_report_structure`; SKILL §2 | Nieobsługiwany algorytm/błąd zachowuje niewykonany zakres, a częściowe wyniki innych podpisów pozostają widoczne. |
| G62-15 / P2 | MD zużywało zbędny kontekst; polityki boilerplate i metadanych były zbyt ogólne. | **A/D/R:** compact jest domyślny: nazwa raz, krótkie strony, permutacja md_order bez ID po każdym akapicie; legacy_pages opcjonalny. GFM dla prostych tabel. Rutynowe NIP/REGON, ankiety i instrukcje nośnika mają jawne role/reguły. Wersja/hash opuszczają publiczny JSON i pozostają w LOG. | `assemble_bundle.py`: `markdown`, `table_markdown`, `SAFE_ROLES`, `is_protected`; schema; output-contract; medical-evidence | Porównanie formatu nie może zmieniać wartości, jednostek, negacji ani relacji. Ankieta jest usuwalna mimo słowa pacjent; daty/status/autorstwo pozostają. Nie deklarujemy nowego pomiaru oszczędności bez wykonania. |
| G62-16 / P2 | Kontrakt pozwalał tabeli pozostać płaskim tekstem. | **D/N:** schema wymaga table dla type=table, a walidator wymaga pokrycia wszystkich komórek, ich spójnego tekstu oraz geometrii. | `document.schema.json`: warunek table; `assemble_bundle.py`: `validate_content`; `content_geometry.py`: `verify_grid`; output-contract §3 | Wielowierszowa tabela bez struktury nie przechodzi; puste/scalone komórki, nagłówki i jednostki zachowują relacje. |
| G62-17 / P3 | Białe znaki zamykały Q&A; validate bez planu pomijało zgodność text/lines. | **D:** question/answer muszą być ciągami niepustymi po strip; content_chunks zawsze sprawdza text/lines/cells. Wynik validate określa węższy zakres bez plikowego QA. | `assemble_bundle.py`: `nonempty`, `validate_content`, `content_chunks`; output-contract §5/8 | Białe znaki i niewłaściwe typy odpowiedzi są odrzucane; konflikt reprezentacji jest blokadą także bez planu. |

Nazwy plików implementacji w tabeli odnoszą się do
`skills/model-ocr/scripts/`; schema i referencje są w
`skills/model-ocr/references/`. Ślad funkcji jest stabilniejszym odniesieniem
niż numery linii zmieniające się w czasie wydania.

## Zachowana wiedza i świadome zmiany

Nadal obowiązuje [95-elementowa mapa źródeł](SELF_EVALUATION.md): jeden Skill,
odczyt MODEL, dynamiczne DPI, pełne strony, odrębna kontrola transkrypcji
i lokalizacji, oryginał w raw, obrazy źródłowego PDF bez rekompresji, wszystkie
daty/autorstwo/pieczęcie/podpisy, brak anonimizacji i indeksu akt, pytania przed
finalizacją oraz Drive/ZIP. Wzorce prawne pozostają wiedzą referencyjną,
bez dopisywania zarzutów i findings do transkrypcji.

Najnowszy wybór użytkownika jawnie zmienia format MD: długi tag przestaje być
domyślny; source page pozostaje przypisaniem każdego bloku. Reorganizacja
nie przenosi bloków do innych stron JSON ani nie zmienia PDF. Usunięcie hasha
i wersji z publicznego JSON nie usuwa ich z kontroli/LOG. Algorytm bezpośredniego
RGB/LANCZOS podglądu zmieniono świadomie na render PDF zgodny z alpha, przy
zachowaniu celu minimalnej wielkości. Nieobsługiwany high-bit jest zgłaszany,
zamiast otrzymać błędną deklarację bezstratności.

## Ograniczenia, których naprawa nie znosi

- Zgodność słów/bbox z wynikowym PDF nie jest automatycznym odczytem obrazu.
  MODEL nadal weryfikuje wszystkie źródłowe regiony i rozstrzyga realne
  niepewności z użytkownikiem. Opisy grafiki i semantyczna klasyfikacja
  mieszanego boilerplate wymagają oceny źródła; regex nie dowodzi ich trafności.
- Raport podpisów pochodzi z wykonanego checkera. `validate_report` ponownie
  wiąże go ze źródłem i detekcją, ale nie powtarza kryptografii ani nie
  uwierzytelnia autorstwa dowolnego ręcznego raportu. Test serializacji/mock
  nie jest walidacją prawdziwego podpisu. Status kwalifikowany pozostaje
  nieoceniony bez rzeczywistego procesu i źródeł zaufania.
- Nie twierdzimy, że każda głębia/animacja/transformacja obrazu jest obsługiwana.
  Jawne odrzucenie nieobsługiwanego źródła jest wynikiem preflight, nie
  zakończoną konwersją. Obsługę dodatkowych trybów trzeba potwierdzić osobno.
- Strukturalny receipt nie dowodzi zapisu w Drive. Potwierdzenie opiera się
  na rzeczywistym wyniku aplikacji; lokalny ZIP, instalacja prywatna, import
  marketplace i publiczne zatwierdzenie są odrębnymi zdarzeniami.

Ta macierz nie dopisuje wyników do końcowych raportów smoke. Stan tych
raportów i wykonanych testów należy odczytać z ich faktycznie zapisanych dowodów.

## Domknięcie relacji komórek podczas przeglądu poprawek

Niezależny przegląd nowego kodu rozszerzył G62-01/G62-16 o dwa konkretne warunki: siatka musi być zgodna z obrysami rzeczywiście przypisanych słów PDF, a komórka oznaczona jako pusta nie może zawierać słowa tabeli przypisanego sąsiedniej komórce. Oba zabezpieczenia są w `content_geometry.verify_grid` / `verify_cell_membership`; nowe testy sprawdzają poprawioną wersję. Nie są ponownym wykonaniem reprodukcji starego wydania.
