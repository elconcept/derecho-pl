# Źródła i pochodzenie reguł

Scalanie obejmuje pięć archiwów przekazanych przez użytkownika. Identyfikatory O/C/T/A/S w samoocenie odnoszą się do poniższych korzeni **wewnątrz oryginalnych archiwów**; nie są ścieżkami instalacyjnymi pluginu. Odwołanie `C:references/render_skanu_pl.md:19–23` oznacza te wiersze w tym pliku źródłowym. Pełny spis 71 plików użytkowych oraz ich SHA-256 jest w [source-manifest.json](source-manifest.json). Nie dołączono metadanych systemu macOS.

| ID | Archiwum i korzeń | SHA-256 archiwum |
|---|---|---|
| O | `opendataloader-pdf.zip` → `opendataloader-pdf/` | `7fb7e0d10f41f5af8a9b7598aaff01f15cef125c046b31bdbaa5e98011798a47` |
| C | `doc-intel-contract-pl.zip` → `doc-intel-contract-pl/` | `0ba3fde557881fb9edda2b993b78b0c2cdfa603a020f149f8a575ac1c59196de` |
| T | `doc-intel-llm-tier-pl.zip` → `doc-intel-llm-tier-pl/` | `83c584d9be8bb3903664fe267d3a85b64f77a712f7847be4980ccb000e9411a2` |
| A | `akta-przeszukiwalne-pl.zip` → `akta-przeszukiwalne-pl/` | `1795f1fb78d969d7152667e3ad9eaa731e1d38fe8498ca07ba4917d7c56e6130` |
| S | `waliduj-podpis-pdf-pl.zip` → `waliduj-podpis-pdf-pl/` | `9511b43e4e503c8088468faae88a28ff2f5d5db0e6c4b39438922fe2e123443a` |

## Charakter wykorzystania

Nowy produkt scala instrukcje i reguły jakości w jeden Skill `model-ocr`. Zastępuje rozpoznawanie tekstu przez wcześniejsze silniki wzrokowym odczytem MODEL. Helpery techniczne obsługują pliki, geometrię, zapis, walidację i dostawę. Nie są kopią dawnych wrapperów OCR.

Zachowano reguły wierności, lokalizacji, typów, tabel, cytatów, kompletności i warunkowej walidacji podpisów. Dostosowano bramkę niepewności, wyjścia, format tagów, log i miejsce dostawy. Usunięto anonimizację, kancelaryjne bramki danych, wymagania starszych backendów, indeks i wyszukiwarkę akt. Wzorce konceptów prawnych i rozpoznawania granic dokumentów zachowano jako wiedzę referencyjną, bez generowania findings.

## Nowe wymagania użytkownika

`U1` oznacza polecenie scalenia: MODEL, PDF/obrazy, dynamiczne rendery, poprawna niewidoczna warstwa, wierny MD, typed bbox JSON, pytania przed zakończeniem, LOG, `raw/`, Drive `Konwerter/<nazwa>/` oraz ZIP jako jedyny załącznik bundle.

`U2` oznacza doprecyzowanie medyczne: odszumienie instytucjonalnego boilerplate z MD, zachowanie wszystkich istotnych dat, autorstwa, podpisów, pieczęci, identyfikatorów i wyników badań oraz neutralny opis faktycznie pustych pól. Usunięcia dotyczą wyłącznie MD, z pełną treścią w OCR/JSON i dyspozycją w LOG.

`U3` oznacza zgłoszony smoke test z wcześniejszej próby Gemini: utrata źródłowej rozdzielczości obrazów, ponad siedmiokrotny wzrost PDF, tekst/znaki poza stroną, brak wyszukiwania i przesunięcia danych identyfikacyjnych. Wartości tego zgłoszenia nie są wynikiem uruchomienia obecnego pluginu. Dokładne zabezpieczenia i kryteria są w [SMOKE_TEST.md](SMOKE_TEST.md).

## Granica dowodów

Audyt źródeł był statyczny. Dawnych skryptów i testów nie uruchamiano. Inwentaryzacja 229 funkcji `test_*` w paczce C nie oznacza 229 wykonanych ani zaliczonych testów. Stare benchmarki OCR i historyczne testy podpisów są twierdzeniami dokumentacji źródłowej, a nie pomiarami MODEL.

Własnym porównaniem potwierdzono, że kopia ekstraktora w A odpowiada ekstraktorowi C po odjęciu dwóch wierszy nagłówka oraz że dostarczone licencje A/T/S są identyczne bajtowo. Skopiowane pliki licencji zweryfikowano przez porównanie bajtów. Wyniki testów nowego produktu są odrębną częścią [SMOKE_TEST.md](SMOKE_TEST.md); niewykonanych operacji nie wolno oznaczać jako wykonane.

## Zmiana względem źródeł

Instrukcje, referencje, kontrakt danych i helpery nowego produktu zostały przepisane/scalone. Nie przedstawia się ich jako niezmienionego wydania któregokolwiek autora źródłowego. Informacje o autorach, licencjach i upstreamowych inspiracjach są w [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md). Pozostawienie oryginalnego tekstu not licencyjnych nie przywraca starych instrukcji operacyjnych jako reguł działania.
