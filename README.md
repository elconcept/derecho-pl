# derecho-pl

Marketplace pluginów do pracy z dokumentami w ChatGPT i Codex.

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
