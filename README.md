# derecho-pl

Marketplace pluginów do pracy z dokumentami w ChatGPT i Codex.

## Założenia i niezależny audyt

Dla MODEL Konwertera punktem odniesienia jest [specyfikacja wymagań produktu](docs/model-konwerter/ZALOZENIA.md), a zgodność sprawdza [macierz 45 kryteriów odbioru](docs/model-konwerter/KRYTERIA_ODBIORU.md). [Rejestr decyzji i rozbieżności](docs/model-konwerter/STAN_I_DECYZJE.md) oddziela wymagania użytkownika, obecne ograniczenia i wyniki audytów. Dokumenty opisują oczekiwane zachowanie; nie poświadczają pełnej zgodności wersji 0.2.0.

Raporty niezależne są w [katalogu audyt](audyt/), w tym [audyt MODEL Konwerter 0.2.0](audyt/2026-11-27T03-25-01Z_v0.2.0/AUDYT_DERECHO_PL_0_2_0.md). Audytor powinien przypiąć commit i ocenić wymagania według tych dokumentów; instrukcje i deklaracje autora pluginu są materiałem do sprawdzenia.

## Pluginy

| Plugin | Wersja | Opis |
|---|---|---|
| [MODEL Konwerter](plugins/model-document-converter) | 0.2.0 | PDF i obrazy → searchable PDF, zwarty MD, JSON z bbox, LOG, raw |

## Import do ChatGPT

W panelu administracyjnym Plugins → Add → Import marketplace wpisz:
- Source: https://github.com/elconcept/derecho-pl
- Path: pozostaw pusty
- Ref: main

Po imporcie udostępnij plugin i połącz Google Drive. [Dokumentacja OpenAI](https://help.openai.com/en/articles/20001504-importing-and-syncing-plugin-marketplaces-from-github).

## Codex

```sh
codex plugin marketplace add elconcept/derecho-pl --ref main
codex plugin add model-document-converter@derecho-pl
```

## Uruchomienie i testy konwertera

W dystrybucji GitHub font Unicode jest zależnością systemową. Z katalogu pluginu:

```sh
python -m pip install -r skills/model-ocr/requirements.txt
python skills/model-ocr/scripts/prepare_font.py --install
python -m unittest discover -s tests -v
```

Helper sprawdza przypięty SHA-256 fontu i odmawia zastąpienia go niezweryfikowanym zasobem. Do uruchomienia konwersji można także przekazać zweryfikowaną ścieżkę przez --font.

Dokumentacja: [kontrakt skilla](plugins/model-document-converter/skills/model-ocr/SKILL.md), [poprawki audytu](plugins/model-document-converter/docs/AUDIT_REMEDIATION.md), [licencje komponentów](plugins/model-document-converter/THIRD_PARTY_NOTICES.md).

## Dodawanie kolejnych pluginów

Dodaj katalog plugins/<nazwa>, jego plugin.json oraz wpis w .agents/plugins/marketplace.json. Nazwa katalogowa i nazwa manifestu muszą być zgodne. Nie umieszczaj danych pacjentów, dokumentacji spraw ani sekretów w repozytorium.

Import w rzeczywistym hoście wymaga osobnej weryfikacji. Raporty testów 0.2.0 dotyczą wydania archiwalnego; dystrybucja źródłowa wymaga przygotowania fontu zgodnie z instrukcją.
