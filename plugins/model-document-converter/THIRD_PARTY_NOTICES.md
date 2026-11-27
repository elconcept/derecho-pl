# Pochodzenie i noty stron trzecich

## Materiały dostarczone przez użytkownika

Ten plugin wykorzystuje i przepisuje wiedzę z pięciu skilli autorstwa wskazanego w ich metadanych jako Wieslaw Mazur / MateMatic, a w części materiałów MateMatic Solutions. Zakres wykorzystania i identyfikatory archiwów opisuje [SOURCE_PROVENANCE.md](docs/SOURCE_PROVENANCE.md). Nowe instrukcje i helpery zmieniają backend odczytu, kontrakt wyjściowy, kontrolę jakości i dostawę; nie są niezmienionymi plikami źródłowymi.

| Materiał | Dostarczona informacja | Zachowana nota |
|---|---|---|
| `opendataloader-pdf` | Apache License 2.0; dostarczony plik licencji wskazuje Wieslaw Mazur / MateMatic Solutions | [opendataloader-pdf-LICENSE.txt](licenses/opendataloader-pdf-LICENSE.txt), kopia bez zmian |
| `doc-intel-llm-tier-pl` | MIT, Copyright (c) 2026 MateMatic (Wieslaw Mazur) | [doc-intel-llm-tier-pl-LICENSE.txt](licenses/doc-intel-llm-tier-pl-LICENSE.txt), kopia bez zmian |
| `akta-przeszukiwalne-pl` | MIT według metadanych; dostarczony LICENSE jest kopią noty warstwy LLM | [akta-przeszukiwalne-pl-LICENSE.txt](licenses/akta-przeszukiwalne-pl-LICENSE.txt), kopia bez zmian |
| `waliduj-podpis-pdf-pl` | MIT według metadanych; dostarczony LICENSE jest kopią noty warstwy LLM | [waliduj-podpis-pdf-pl-LICENSE.txt](licenses/waliduj-podpis-pdf-pl-LICENSE.txt), kopia bez zmian |
| `doc-intel-contract-pl` | Metadane deklarują MIT oraz Wieslaw Mazur / MateMatic; w archiwum nie było osobnego LICENSE | Zachowano tę deklarację pochodzenia; nie dorobiono nieotrzymanego pliku licencji |

Noty A/T/S zawierają akapit o contextgem i dawnym workflow lokalnym/EOG. W A i S opis zależności jest niezgodny z ich własnymi metadanymi i został rozpoznany jako kopia. Zachowane dokumenty licencyjne nie są poleceniem uruchomienia contextgem, anonimizacji ani dawnej bramki danych.

## Atrybucja przejętej wiedzy upstream

Źródło `doc-intel-contract-pl/SKILL.md` przypisuje `datalab-to/chandra` (kod Apache-2.0, bez wag modelu) adaptację promptu/kontraktu regionów, wykrywania powtórzeń generacji oraz przepisu renderu z AcroForm i dynamicznym DPI. Nowy plugin zachowuje pochodzenie przepisu i reguł jakości, nie dołącza ani nie uruchamia modelu Chandra, jego wag ani starego adaptera.

To samo źródło opisuje jako inspiracje, bez zależności runtime i bez kopiowania ich kodu: kształt typed blocks z Mistral OCR, zasady pokrycia stron i granic dokumentów z docjev, kontrolę pominiętej treści motywowaną anydoc oraz dowodowe powiązanie tekstu i dokumentacji z docling-graph. Pomysł maskowania inspirowany flintai-cli nie został przeniesiony do nowego workflow.

Poprzednie zależności OpenDataLoader, MarkItDown, contextgem, Ollama, LiteParse/Tesseract, Gaius i Chandra nie stają się przez te noty aktywnymi komponentami produktu. Informacje o używanych obecnie bibliotekach technicznych należy odczytywać z bieżącego helpera i jego środowiska, nie ze starych deklaracji.

## Font Unicode

Wydanie archiwalne pluginu wykorzystuje DejaVuSans.ttf do osadzania tekstu Unicode, w tym polskich znaków. Dystrybucja źródłowa GitHub korzysta z tego samego fontu dostarczanego niezależnie przez zaufany pakiet systemowy. Helper prepare_font.py sprawdza SHA-256 względem wersji testowanej. Odpowiednia nota fontu znajduje się w [DejaVu.txt](licenses/DejaVu.txt). Font nie jest modelem OCR.

## Zakres oświadczenia

Powyższe pochodzenie wynika z dostarczonych plików i jawnie wskazanych składników. Nie jest stwierdzeniem przeprowadzenia pełnej niezależnej analizy prawnej upstreamów ani publicznego zatwierdzenia pluginu. Produkt przygotowano prywatnie; nie twierdzi się, że został zgłoszony, zaakceptowany lub opublikowany w katalogu publicznym.
