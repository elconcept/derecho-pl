# Wykonane kontrole — MODEL Konwerter 0.2.0

## Wynik i zasada wykonania

**83/83 testy poprawionego kodu przeszły; 0 błędów, 0 niepowodzeń, 0 pominięć.** Wykonanie: 27 listopada 2026 r., Europe/Warsaw, 15,465 s. Wszystkie 17 ustaleń dostarczonego audytu przyjęto jako potwierdzone. **Nie uruchamiano ponownie wersji 0.1.0 ani archiwalnych skryptów odtwarzających jej błędy.** Testy służą odbiorowi zmian i ochronie poprawionej wersji.

Dowody: [VALIDATION.json](VALIDATION.json) zawiera środowisko i hashe rzeczywiście testowanych plików, [TEST_RESULTS.txt](TEST_RESULTS.txt) wynik każdego przypadku, [FORWARD_SMOKE.json](FORWARD_SMOKE.json) końcową kontrolę pełnego bundle, [MD_FACTS_CHECK.json](MD_FACTS_CHECK.json) porównanie zachowanych treści, a [MD_COMPACTNESS.json](MD_COMPACTNESS.json) pomiary znaków. Pełne rozliczenie audytu znajduje się w [AUDIT_REMEDIATION.md](AUDIT_REMEDIATION.md).

## Zestaw wykonawczy

Polecenie równoważne użytemu loaderowi i TextTestRunner biblioteki unittest:

```bash
python3 -B -m unittest discover -s tests -v
```

Kod wyjścia: **0**. Python 3.12.14, PyMuPDF 1.26.6, Pillow 13.0.0, pypdf 6.21.4, jsonschema 4.26.0, fonttools 4.61.1, cryptography 50.0.0.

| Grupa | Wynik | Zakres |
|---|---:|---|
| Zachowanie PDF i nowe poprawki PDF | 33/33 | Strumienie obrazów i masek, wygląd, widoczny tekst, adnotacje, Unicode, CropBox/obroty, wyszukiwanie, położenie zachowanych ukrytych znaków, pojedyncze słowa patch, rzeczywisty typ i więź obraz–baza, alpha, jawne odrzucenie wysokiej głębi. |
| Wcześniejsze kontrole treści dostosowane do kontraktu 2.0 | 12/12 | Przegląd, odszumianie, chronione daty/podpisy, strony, komórki, pełny skład ZIP i oryginał. Testowane na poprawionym kodzie. |
| Odbiór audytu i integracji plików | 22/22 | Niezależna zgodność text/lines/cells, oba etapy wydania, obca baza, fałszywy typ, rzeczywiste wymiary i wystąpienia, podpis/opis, raport związany z oryginałem, rdzeń LOG, deduplikacja, zwarty MD, obowiązkowa tabela i niepuste odpowiedzi. |
| Podpisy i raportowanie | 16/16 | Związanie raportu z hashem/typem/detekcją, wadliwi kandydaci, cztery rodzaje czasu, attempted/performed/completed, częściowe wyniki i brak opcjonalnego backendu. Kontrolowane odpowiedzi backendu są jawnie mockowane. |

W ramach kontroli tabel sprawdzono również zamianę wartości przy szerokich nakładających się bboxach oraz pozornie pustą komórkę, której słowo przypisano sąsiadowi. Te zabezpieczenia wynikły z przeglądu nowej integracji. Siatka jest sprawdzana na rzeczywistych obrysach przypisanych słów, a konflikt przynależności słowa do komórek jest blokowany. Nie wprowadzono globalnego zakazu nakładania osobnych bloków lub pieczęci.

## Pełna konwersja po poprawkach

Wykorzystano wcześniej zatwierdzoną transkrypcję syntetycznego dwustronicowego skanu, bez ponownego uruchamiania starego pipeline. Zmieniono kontrakt wejść na 2.0, wygenerowano rzeczywisty raport stanu podpisów oryginału i związano aktualne hashe. Wykonano poprawiony build, a następnie końcowe stage/seal po zamrożeniu helperów. Treść, plan OCR i źródłowe bbox nie wymagały zmiany.

Źródło jest jawnie fikcyjne: różne daty wydruku, lekarz A w treści, lekarz B na pieczątce, dwa różne NPWZ, wyniki laboratoryjne oraz rzeczywiście puste pola podpisu. Nie jest to prywatny dokument użytkownika ani pomiar dokładności OCR na nieznanym korpusie.

| Kontrola | Wynik |
|---|---:|
| Strony / bloki JSON / linie lub komórki OCR | 2 / 25 / 42 |
| Słowa jednoznacznie związane PDF → JSON | **144/144** |
| Tabela sprawdzona na faktycznych słowach | **1, 3 × 4, 12 komórek** |
| Znaki w warstwie / poza stroną | **1018 / 0** |
| Wyszukiwanie we właściwym regionie | **62/62** |
| Zgodność zatwierdzonej transkrypcji | **2/2 strony** |
| Pikselowo identyczne rendery przy 192 DPI | **2/2 strony** |
| Obrazy źródłowe | **2 × 2474 × 3500 px**, niezmienione strumienie i położenia |
| Różnica geometrii wobec wcześniej obejrzanych nakładek | **0,0 pt** |
| Więź oryginał–baza | **byte_identical_pdf** |
| Oryginał w raw / CRC ZIP | **Identyczny bajtowo / poprawne** |
| Raport podpisów i rdzeń LOG | **Obecne, sprawdzone w obu bramkach** |
| Podpis cyfrowy | **not_present; kryptografia prawidłowo pominięta** |
| Skład ZIP | **Dokładnie 5 wymaganych plików** |
| Zapis na Drive | **Nie wykonywano; delivery.events puste** |

Końcowy testowy ZIP ma 1 237 319 B. Hashe jego pięciu składników i czterech helperów zapisano w FORWARD_SMOKE. ZIP zawiera searchable PDF, MD, JSON, LOG i oryginał w raw; rendery i pliki robocze pozostają poza nim.

## Zwięzłość MD przy zachowaniu informacji

MD przykładu ma **1132 zamiast 1291 znaków Unicode**, czyli o **12,316% mniej**; rozmiar UTF-8 wynosi 1165 zamiast 1324 B. Sprawdzono wszystkie 20 uwzględnionych bloków i 14 pozycji checklisty: różne daty wydruku, osoby i role, obie pieczątki/NPWZ, puste pola, relacje wynik–jednostka–zakres, zalecenie i identyfikator pozostały na właściwych stronach. Kontakt i ankieta nadal pozostają w pełnym JSON/OCR, a nie w MD.

Oddzielny pomiar wykorzystał gotowy HTML 101 × 4 z audytu **wyłącznie jako dane**. Nowy renderer daje **2934 zamiast 6973 znaków**, około **57,9% mniej**, zachowując wszystkie komórki i ich kolejność. Końcowy newline wyłączono jednakowo z pomiaru renderów; długość pliku źródłowego jest osobno zapisana w JSON.

Dla 500 odsyłaczy i jawnie podanej w raporcie przykładowej długiej nazwy nowy format potrzebuje 4465 zamiast 41391 znaków, około **89,2% mniej**. To pomiar samych znaczników wraz z jednorazowym nagłówkiem, nie całego dokumentu. **Wszystkie te wartości oznaczają znaki, nie tokeny.**

## Pakiet i marketplace

Plugin pozostaje prywatny, ma jeden Skill i wymaganą istniejącą aplikację Google Drive. Wydanie 0.2.0 używa udokumentowanego pola `required: true`. Repozytorium derecho-pl umieszcza go pod `plugins/model-document-converter`, a katalog znajduje się w `.agents/plugins/marketplace.json`. Polityki workspace i połączenie konta Drive są odrębnymi ustawieniami.

Przed wydaniem wykonywane są: prywatny preflight pluginu, dwa deterministyczne pakowania, sprawdzenie świeżego rozpakowania, walidacja kompletnego marketplace i jego własne testy. Rejestracja prywatnej aktualizacji, utworzenie/push repozytorium oraz faktyczny import marketplace są osobnymi operacjami wykonywanymi po zapieczętowaniu plików. Ten raport nie stwierdza ich wykonania z samej obecności manifestu.

Publiczna publikacja w katalogu OpenAI/GPT Store nie była zamówiona. Nie wprowadzono fikcyjnych adresów polityk ani deklaracji publicznego zatwierdzenia.

## Ograniczenia jawne dla wersji 0.2.0

- PyHanko nie było zainstalowane: nie wykonano rzeczywistej walidacji kryptograficznej przez ten backend. Brak podpisu pozostaje normalnym pominięciem; obecny podpis przy brakującym backendzie ma jawne not_verified.
- Sam walidator raportu potwierdza jego strukturę i więź ze źródłem, a nie wykonanie dowolnego ręcznie wpisanego wyniku. Skill wymaga rzeczywistego check(source) przed zamknięciem review.
- Obrazy >8 bitów oraz tryby integer/float są odrzucane przed utworzeniem bazy. Nie obiecuje się ich bezstratnej konwersji ani automatycznego obcięcia do RGB.
- Patch działa na pojedynczych całych słowach. Geometria skośna/pionowa, niejednoznaczne zasoby i niemożliwe dopasowanie mogą wymagać dalszego wsparcia; pipeline zatrzymuje taki przypadek.
- Kontrole są mocniejsze od poprzedniego wydania, ale testy syntetyczne nie dowodzą nieomylności odczytu MODEL. Użytkownik może sprawdzić rzeczywiste dokumenty w kolejnym smoke teście.

