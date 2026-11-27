# MODEL Konwerter 0.2.0

Prywatny plugin: jeden Skill model-ocr, hostowy Python i widzenie MODEL, istniejąca aplikacja Google Drive. Nie ma własnego serwera ani pośredniego silnika OCR.

## Zadanie i granice

Użytkownik konwertuje własny PDF lub obraz do sprawdzonego PDF/MD/JSON/LOG/raw i ZIP. Autoryzowana mutacja dotyczy wyłącznie kopii pochodnej oraz wskazanego folderu Drive. Oryginały i udostępnienie pozostają chronione. Read/list/search/grep służą rozpoznaniu; write/patch/shell/python wykonują zleconą transformację i walidację. Nie są uprawnieniami nadawanymi przez manifest.

Wymaganie jednego Skilla ma pierwszeństwo przed domyślnym dodawaniem osobnych skilli host-workspace-operator i sandbox-python-executor. Ich zasady dowodu wykonania, odczytu przed zmianą i ochrony źródła zostały włączone do model-ocr.

## Formaty i instalacja

Kanoniczny manifest to Agent Plugins 1.0 w plugin.json, ze zgodną nakładką .codex-plugin/plugin.json. Aplikację Google Drive powiązano z rzeczywistym identyfikatorem uzyskanym z metadanych istniejącego pluginu. Brak własnych kluczy/API i fikcyjnych zależności na narzędzia hosta.

To pakiet prywatny do smoke testu, nie publikacja w publicznym katalogu. Nie wymyślono stron wsparcia, polityk ani zweryfikowanego publicznego wydawcy. Starszy walidator Autopilot 0.7.0 sprawdza publiczne URL także dla powiązanej aplikacji; te warunki publicznej dystrybucji nie są deklarowanym celem wydania.

## Rozpoznawanie żądania

Bezpośrednie: popraw OCR, searchable PDF, konwersja skanu. Pośrednie: przygotuj dokumentację do analizy masowej z odwołaniami do stron. Negatywne: diagnoza lub terapia, wydawanie opinii prawnej, fałszowanie dokumentu, składanie pisma, budowanie indeksu całych akt. W tych przypadkach sam konwerter nie dopisuje analizy lub nowych danych do transkrypcji.

## Znak

Kartka z zachowaną strukturą i znacznikiem kontroli przedstawia zadanie: odczytać dokument i sprawdzić jego odwzorowanie. Warianty jasny/ciemny mają identyczną geometrię; kompaktowy SVG działa bez fontu, linków i zewnętrznych zasobów.

## Dokumentacja formatu sprawdzona przy budowie

- https://developers.openai.com/plugins/build/plugins
- https://developers.openai.com/plugins/deploy/submission-errors
- https://pymupdf.readthedocs.io/en/latest/page.html
- https://pymupdf.readthedocs.io/en/latest/document.html

Aktualne wykonanie i jego granice: SMOKE_TEST.md. Śledzenie wszystkich źródeł: SELF_EVALUATION.md.
