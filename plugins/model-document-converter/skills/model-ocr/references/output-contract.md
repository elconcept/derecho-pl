# Kontrakt treści, review i finalnego bundle — 0.2.0

## 1. Oddziel treść od operacji

Roboczo prowadź `inventory.json`, `document.json`, `layer-plan.json`,
`review.json`, raport podpisów, raporty QA i PNG. Finalny katalog zawiera tylko:

- `<stem>_searchable.pdf`;
- `<stem>.md`;
- `<stem>.json`;
- `LOG.md`;
- `raw/<oryginalna_nazwa_z_rozszerzeniem>`.

Publiczny JSON jest pełną reprezentacją źródła, także nagłówków i stopek
pomijanych w MD. Zawiera tekst, opisy źródłowe, strony, role i geometrię.
Nie zawiera `schema_version`, `source.sha256`, engine, confidence, czasów
przetwarzania, uzasadnień ani decyzji czyszczenia. Wersja kontraktu i hashe
należą do roboczego review i LOG. Żaden plik roboczy nie jest dodatkowym
składnikiem bundle ani finalnym załącznikiem.

Nie wstawiaj danych z pamięci, kontekstu sprawy ani późniejszej analizy.
Podejrzenie użytkownika wyznacza potrzebę zachowania dowodów, ale nie staje
się transkrypcją dokumentu.

## 2. Źródło, strony i geometria

Przykład struktury; tekst i liczby są ilustracją, nie domyślnymi danymi:

```json
{
  "source": {
    "filename": "dokument.pdf",
    "kind": "pdf",
    "page_count": 1
  },
  "coordinate_system": "normalized-displayed-cropbox-top-left-xyxy",
  "pages": [{
    "page_number": 1,
    "width_pt": 595,
    "height_pt": 842,
    "page_kind": "text",
    "blocks": [{
      "id": "p001-b001",
      "order": 1,
      "type": "paragraph",
      "bbox": [0.1, 0.2, 0.8, 0.23],
      "text": "Data wydruku: 2026-11-27 08:31",
      "evidence_roles": ["print_time"],
      "lines": [{
        "text": "Data wydruku: 2026-11-27 08:31",
        "bbox": [0.1, 0.2, 0.8, 0.23]
      }]
    }]
  }]
}
```

Obowiązuje [document.schema.json](document.schema.json). Strony to fizyczne
strony/klatki oryginału, dokładnie 1…N. `blank` wymaga obejrzenia i pustej listy
bloków; `image_only` wymaga opisanej grafiki nawet bez słów do OCR. Nieblankowa
strona nie może mieć pustej reprezentacji. `order` wyznacza logiczną kolejność
bloków na stronie. Prefiks ID musi wskazywać tę samą stronę.

Każdy bbox zawiera cztery skończone liczby: `0 <= x0 < x1 <= 1`,
`0 <= y0 < y1 <= 1`. Wymiary odpowiadają rzeczywistemu wyświetlanemu CropBox,
nie domyślnemu A4. Obrót/offsety i przeliczenie na punkty nieobróconej strony
planu PDF pochodzą z inventory. Linie i komórki muszą mieścić się w swoim bloku.

`text` zawiera czytelne słowa źródła. `visual_description` opisuje widoczny stan,
np. „Pole podpisu lekarza: puste”. Czytelne nazwisko/pieczęć pozostają także
w `text`; nie powielaj tych samych słów w opisie. Typy `signature`,
`signature_field`, `stamp`, `handwriting`, `figure`, `logo` wymagają niepustego
opisu. Każdy blok musi mieć niepusty tekst lub opis, a `include` musi coś
wyemitować. `evidence_roles` opisują funkcję informacji, nie pewność ani QA.

Wszystkie obecne reprezentacje tekstu bloku są sprawdzane niezależnie:
`text`, połączone `lines` oraz połączone teksty komórek. Muszą być zgodne po
normalizacji wyłącznie odstępów/NFC, także przy `validate` bez planu.
Nie stosuj casefold, usuwania diakrytyków, zamiany `$` na `§` ani scalania cyfr.

## 3. Obowiązkowa struktura tabel

Blok `type: "table"` **musi** mieć `table: {rows, columns, cells}`.
Komórka ma zerowe indeksy `row`/`column`, `text`, `bbox`; opcjonalnie
`rowspan`, `colspan`, `header` i źródłowy `visual_description`. Ujmij pozycje
puste i scalone: occupancy pokrywa całe `rows × columns` bez nakładania.
Nie wymyślaj nagłówka dla tabeli bez nagłówka.

`block.text` jest połączeniem tekstów komórek w kolejności wiersz/kolumna.
Jeżeli występują `lines`, również muszą zachować tę treść. Komórki są
kanoniczną strukturą renderowania; obecność poprawnych linii nie usprawiedliwia
innej wartości w komórce. Puste komórki mają pusty tekst; opis może oddawać
widoczny stan pola. Opisy nie są dodawane do OCR.

Proste tabele bez scaleń i z nagłówkami zgodnymi z GFM są zapisywane jako GFM.
Brak nagłówka źródłowego zachowuje pusty wiersz nagłówkowy formatu GFM.
HTML jest stosowany dla scaleń lub układu komórek nagłówkowych, którego GFM
nie odwzorowuje. Nie zamieniaj tabeli w płaski worek słów. Stan nieczytelnej
struktury rozstrzygnij z użytkownikiem przed wydaniem; nie zgaduj relacji.

Listy zachowują numerację i hierarchię, checkboxy stan `[x]`/`[ ]`, a indeksy
górne/dolne wierną postać. Formatowanie nie zmienia wartości ani jednostki.

## 4. Zwięzły Markdown i przypisanie do stron

Domyślny `review.md_profile` to `compact`. Nazwa źródła występuje raz,
następnie liczba stron i krótkie odsyłacze:

```markdown
# dokument.pdf

Strony: 2

[s. 1]

Treść z pierwszej fizycznej strony.

[s. 2]

Treść z drugiej fizycznej strony.
```

Nowsze polecenie użytkownika wprost zastępuje wcześniejszy obowiązek pełnego
tagu przy każdej stronie. `md_profile: "legacy_pages"` pozostaje opcją i emituje
`==== <original_filename> (Page x/y) ====`. Nie ustawiaj go domyślnie.

Domyślnie bloki zachowują kolejność stron i `order`. Opcjonalne `review.md_order`
to dokładna permutacja **wszystkich i tylko uwzględnionych** ID bloków:
umożliwia reorganizację analityczną bez zmiany źródłowej strony, tekstu ani JSON.
Przy każdej zmianie strony źródłowej renderer ponawia `[s. x]`; ten sam numer
może wystąpić ponownie. Nie dopisuj ID do każdego akapitu ani nowych wniosków.
Każda strona bez uwzględnionych bloków nadal otrzymuje odsyłacz; tylko naprawdę
pusta strona otrzymuje `[Pusta strona.]`. Przy reorganizacji takie strony są
dopisane po blokach. Nie określaj strony jako pustej po samym odszumieniu.

## 5. Roboczy ledger przeglądu

`review.json` trafia do LOG; nie jest publicznym JSON treści.

| Pole | Wymaganie |
|---|---|
| `source_sha256` | SHA-256 rzeczywistych oryginalnych bajtów |
| `document_sha256` | Kanoniczny hash aktualnego `document.json` |
| `layer_plan_sha256` | Kanoniczny hash aktualnego planu; wymagany dla etapów z planem |
| `signature_report` | Pełny obiekt zwrócony przez `check_signatures.check(source)` lub CLI; bez ręcznej redukcji |
| `complete`, `unresolved_questions` | `true` i `[]` wyłącznie po faktycznym zakończeniu kontroli |
| `page_checks` | Kolejno 1…N; `page`, `image_reviewed`, `transcription_verified`, `geometry_verified`; trzy kontrole muszą być `true` |
| `blocks` | Dokładnie jeden wpis na każde ID, bez brakujących/dodatkowych bloków |
| `md_profile`, `md_order` | Opcjonalne ustawienia widoku opisane wyżej |
| `actions`, `decisions` | Zwięzły zapis rzeczywistych działań i rozstrzygnięć |

Wpis bloku ma `status` i `md_action`. Statusy to `verified`, `user_verified`,
`source_illegible_accepted`. Dwa ostatnie wymagają `question` i `answer` jako
ciągów niepustych po `strip()`. Flaga, liczba i białe znaki nie są odpowiedzią.
Zaakceptowana nieczytelność pozostaje opisana jako cecha źródła.

Dyspozycje MD:

- `include`: pełny tekst i opis bloku trafiają do MD; brak emisji jest błędem.
- `omit_boilerplate`: odrębny rutynowy kontakt/administracja placówki, ankieta,
  instrukcja nośnika lub czysto dekoracyjne logo; wymagany niepusty `reason`.
- `deduplicate_furniture`: identyczny `header`/`footer`/`logo` z `duplicate_of`
  wskazującym wcześniejszy **uwzględniony** blok i z niepustym `reason`.
  Oba końce relacji muszą być niechronionymi elementami formy, a ich tekst
  i opis muszą być identyczne. Wynik, podpis lub akapit nie może być celem.

Nie pomijaj chronionych typów ani ról, w tym `document_status`; ochrona obejmuje
także `visual_description`, linie i komórki. Minimalna tożsamość placówki
i wszystkie istotne warianty pozostają. Rozdziel mieszany nagłówek kontaktowy
od daty wydruku, autora, wyniku czy statusu przed czyszczeniem. Szczegóły
klasyfikacji są w [medical-evidence.md](medical-evidence.md).

Kanoniczne hashe JSON uzyskaj po ostatecznej korekcie:

```sh
python scripts/assemble_bundle.py hash work/document.json
python scripts/assemble_bundle.py hash work/layer-plan.json
```

Hash używa `sort_keys`, UTF-8 i zapisu bez zbędnych odstępów. Zmiana treści
lub planu unieważnia zależny przegląd; powtórz dotknięte nią kontrole.

## 6. Wspólna bramka stage i seal

Oba etapy uruchamiają `verify_bundle_inputs`, a w nim:

1. Walidację treści, review, planu, nazw i hashy aktualnych plików.
2. `verify_source_base`: rzeczywisty typ z bajtów; PDF-baza identyczna bajtowo
   z oryginałem albo niezależne sprawdzenie wszystkich klatek, próbek, masek,
   orientacji, wymiarów i położenia oryginalnego obrazu w bazie. Inventory jest
   sprawdzany dodatkowo, nie zastępuje tej więzi.
3. `validate_report`: raport podpisów zgodny z hashem, nazwą, typem i aktualną
   detekcją oryginału. `validate` sprawdza wcześniej jego kompletną strukturę.
   Kontrola kryptograficzna pozostaje warunkowa i jest wykonywana przez checker,
   nie ponownie przez te bramki. `not_present`/`skipped` i obrazowe
   `not_applicable` są normalne; `not_verified` zachowuje rzeczywistą przyczynę.
4. PDF QA źródłowej bazy i searchable, wraz z geometrią zachowanego OCR.
5. `verify_document_geometry`: wymiary wyświetlanego CropBox zgodne do 0,01 pt;
   przypisanie jeden do jednego każdego wystąpienia słowa PDF do JSON, z
   tolerancją zawierania 2 pt. Wszystkie reprezentacje jednego bloku odnoszą
   się do tego samego zbioru wystąpień. Sprawdzana jest również kolejność
   komórek względem ich położeń. Nie ma ogólnego zakazu nakładania pieczęci;
   nie wolno dwukrotnie użyć jednego wystąpienia do dwóch odczytów.

`expected_text` planu obejmuje wszystkie widoczne słowa strony, także
boilerplate. Kolejność technicznej ekstrakcji może różnić się od logicznej;
kontrola obejmuje pełne fragmenty, krotność i geometrię. Opisy grafiki ani
pustego podpisu nie wchodzą do `expected_text` lub OCR.

## 7. Finalizacja i niezmienny rdzeń LOG

Poniższe ścieżki są przykładami; dopasuj je do rzeczywistych plików hosta:

```sh
python scripts/check_signatures.py input/dokument.pdf --output work/signatures.json
python scripts/assemble_bundle.py validate --document work/document.json --review work/review.json --plan work/layer-plan.json
python scripts/assemble_bundle.py stage --source input/dokument.pdf --base-pdf input/dokument.pdf --searchable work/searchable.pdf --document work/document.json --review work/review.json --plan work/layer-plan.json --output-dir output/dokument
python scripts/assemble_bundle.py record-delivery --bundle-dir output/dokument --receipt work/drive-receipt.json
python scripts/assemble_bundle.py seal --bundle-dir output/dokument --source input/dokument.pdf --base-pdf input/dokument.pdf --document work/document.json --review work/review.json --plan work/layer-plan.json --output-zip output/dokument_bundle.zip
```

Przed `validate` umieść pełny obiekt z `signatures.json` w `review.signature_report`.
Dla obrazu użyj `image-base.pdf` z `prepare` i przekaż
`--inventory work/inventory.json` **zarówno do stage, jak i seal**.
`record-delivery` wykonaj dopiero po faktycznych operacjach opisanych w
[google-drive.md](google-drive.md), nie jako fikcyjny krok przykładu.

`stage` generuje rdzeń LOG z review, kontrolami, wersją kontraktu, hashami
i rozmiarami aktualnych artefaktów. `seal` odtwarza ten rdzeń i wymaga równości,
sprawdza MD/JSON i bajty raw, po czym tworzy i kontroluje ZIP. Nie edytuj LOG
ręcznie, nie zastępuj rdzenia streszczeniem. Potwierdzenia dostawy trafiają
wyłącznie do ustrukturyzowanej sekcji przez `record-delivery`; nie mogą zmienić
review/QA. Hashe/rozmiary podanych w potwierdzeniu artefaktów muszą być aktualne.
Nie wpisuj hasha LOG do niego samego ani hasha ZIP do jego własnego wnętrza.

## 8. Granice dowodu

`validate` bez planu sprawdza treść i review; z planem dodatkowo ich zgodność
z planem. Żaden wariant nie zastępuje etapów pracujących na rzeczywistych
plikach. Kontrola geometrii wiąże JSON z faktycznym tekstem PDF, ale nie
rozstrzyga sama, co jest widoczne w obrazie ani czy opis grafiki jest trafny.
Obowiązują drugi odczyt wszystkich stron i pytania o realne niepewności.

Poprawny schemat, wpis `verified`, przeszukiwanie PDF lub zielony test
syntetyczny nie dowodzą nieomylności MODEL. Raport podpisów musi pochodzić
z rzeczywistego wykonania checkera; jego walidacja strukturalna nie stanowi
poświadczenia autorstwa dowolnych ręcznie podanych wyników kryptografii.

### Dodatkowe zabezpieczenie relacji tabeli

Siatka jest sprawdzana zarówno na zadeklarowanych prostokątach, jak i na obrysach rzeczywistych słów przypisanych do komórek. Szeroki bbox nie może uzasadniać zamiany wartości między wierszami. Komórka zadeklarowana jako pusta nie może obejmować słowa tej tabeli przypisanego innej komórce. Kontrola dotyczy komórek tabeli; osobne pieczęcie i bloki mogą się nakładać.
