# Wiedza zachowana z pięciu źródeł

Ten plik przechowuje użyteczne reguły z istniejących skilli. Nie przywraca ich dawnych backendów, anonimizacji, ograniczeń kancelaryjnych ani indeksu akt. Szczegółowe rozliczenie jest w [SELF_EVALUATION.md](../../../docs/SELF_EVALUATION.md), a źródła i hashe w [SOURCE_PROVENANCE.md](../../../docs/SOURCE_PROVENANCE.md). Świadome zmiany 0.2.0 i 17 przyjętych ustaleń audytu rozlicza [AUDIT_REMEDIATION.md](../../../docs/AUDIT_REMEDIATION.md).

## Typy i struktura

Zachowana bazowa taksonomia bloków: `title`, `paragraph`, `table`, `list`, `equation`, `signature`, `stamp`, `figure`, `header`, `footer`, `unknown`. Dodatkowe typy lub podtypy obrazu, logo, odręcznego dopisku albo pustego pola określa bieżący schemat; nie należy zgadywać niewspieranej nazwy.

Każdy blok ma powiązanie z konkretną stroną i sprawdzonym regionem. Odczyt i bbox weryfikuje się niezależnie. Tabela musi mieć jawną strukturę komórek, nagłówków, wierszy, kolumn i scaleń; lista zachowuje markery i hierarchię; formularz wartości i stany pól wyboru. W 0.2.0 wszystkie obecne reprezentacje text/lines/cells są sprawdzane, także bez planu. Globalne przypisanie słów do bbox rozróżnia powtórzenia i nie wykorzystuje jednego wystąpienia dwa razy. Taksonomia struktury nie jest listą wniosków prawnych.

## Renderowanie do odczytu

Zachowana formuła bazowa dla PDF:

`dpi = max((1024 / min(page_width_pt, page_height_pt)) * 72, 192)`

Skala renderu wynosi `dpi / 72`. Źródłowy przepis dla obrazów przewidywał RGB i LANCZOS, gdy krótszy bok miał mniej niż 1536 pikseli. **Świadoma adaptacja 0.2.0:** zachowano cel minimalnej wielkości podglądu, natomiast bieżący helper renderuje zweryfikowaną bazę PDF do RGB na białym tle w rozdzielczości natywnej lub powiększonej do tego minimum. To zastępuje bezpośrednie `convert("RGB")`/LANCZOS i zapewnia zgodną reprezentację alpha; dawny algorytm nie jest obietnicą runtime. Surowy obraz i piksele bazy pozostają zachowane. Powiększenie nie odzyskuje nieistniejących szczegółów. Dla małego druku obowiązuje dobór wyższego DPI/cropów i ponowny odczyt.

Przygotowanie odrzuca nieobsługiwane obrazy >8 bitów na próbkę, integer/float oraz nieobsługiwane przekształcenia CMYK, zanim zapisze bazę. Nie nazywa obcięcia zakresu próbek konwersją bezstratną. Wspólna kontrola `stage`/`seal` odtwarza więź z rzeczywistymi klatkami, próbkami, maską i orientacją; dwa deklarowane hashe nie wystarczają.

Render musi zawierać widoczne formularze i adnotacje. Jeżeli konieczne jest spłaszczenie wyglądu pól, wykonaj je wyłącznie na roboczej kopii do oglądania. Podpisy cyfrowe bada się, jeśli występują, na oryginalnych bajtach przed przekształceniem. PDF wyjściowy zachowuje bazę oryginalnego PDF i jego obrazy; render nie jest materiałem do odbudowy PDF.

## Porównywanie cytatów i typografii

Źródłowy mechanizm dopasowania uwzględniał różnice wielkości liter, polskie znaki i NFD/NFC, NBSP, rodziny cudzysłowów i myślników, miękki dywiz, znaki zerowej szerokości, BOM, wielokropek, przeniesienia wyrazów oraz `ß/ẞ`. Są to tolerancje **porównania**, nie polecenie zmiany tekstu źródłowego. Każda normalizacja musi zachować mapowanie do zakresu oryginalnych znaków.

W przyszłym odnajdywaniu cytatów trzeba rozróżnić dopasowanie dosłowne, typograficznie znormalizowane, przechodzące przez bloki i treść wyprowadzoną. Licz wszystkie możliwe wystąpienia, również kilka w jednym akapicie. Pierwsze znalezione dopasowanie nie jest dowodem unikalnej lokalizacji. Ten konwerter dostarcza źródłowe teksty, strony i bbox; nie tworzy indeksu akt ani findings.

Nie przenoś automatycznej zamiany `$` na `§`, `l/I` na `1`, apostrofów na cudzysłowy albo każdego myślnika na `-` do transkrypcji. Sprawdź obraz. Nie używaj porównania samych multizbiorów liter/cyfr jako dowodu 100% wierności.

## Kategorie i granice dokumentów w jednym PDF

Źródła rozpoznawały: wyrok, uzasadnienie, postanowienie, uchwałę, zarządzenie, protokół rozprawy, akt oskarżenia, apelację/środek odwoławczy, pozew/wniosek, opinię biegłego, pełnomocnictwo, notatkę urzędową i kategorię inną.

Zachowaj tę wiedzę do rozumienia nagłówków, kolejności i powtórzeń. Sąsiednie dokumenty tego samego rodzaju mogą być odrębne; samo słowo „UZASADNIENIE” w wyroku nie tworzy nowego dokumentu. Powtarzany nagłówek ani przywołana w treści sygnatura nie oznaczają granicy. Nie dziel automatycznie pliku na osobne eksporty ani nie zmieniaj fizycznej numeracji stron.

## Koncepty prawne jako wiedza referencyjna

| Dokument | Zachowane wskazówki rozpoznawania | Co z nich wynika dla transkrypcji |
|---|---|---|
| Umowa | Strony i formy prawne, przedmiot, wynagrodzenie i jego obliczanie, termin płatności wraz ze zdarzeniem początkowym, kara i stawka, wypowiedzenie, poufność, sąd/arbitraż, prawo właściwe | Dokładnie zachowaj liczby, warunki, negacje i powiązania zdań; nie wyliczaj terminów ani ryzyk. |
| Orzeczenie | Sygnatura, sąd, sentencja, powołana podstawa prawna, teza/holding | Odróżnij sentencję od uzasadnienia. Tezę zapisz tylko wtedy, gdy jest w źródle; nie generuj własnej. |
| Pismo procesowe | Rodzaj pisma, petitum, zarzuty, WPS, wzmianki o terminie/prekluzji | Zachowaj strukturę żądań i zarzutów, bez ich streszczenia lub uzupełniania. |

Poprzedni skill używał typów konceptów string/numeric/boolean/date i odniesień do zdań dla precyzyjnych wartości, akapitów dla szerokich kategorii. Ta wiedza pomaga unikać błędnego grupowania treści. Nie wolno zastąpić dosłownej daty/kwoty typowaną wartością, która usuwa oryginalny format, walutę, zakres lub warunek. Uzasadnienia interpretacji nie należą do MD/JSON konwersji.

## Jakość i niepewność

- Obserwacja bardzo słabego tokena może być ważniejsza niż wysoka średnia jakości akapitu. Dawny 10. percentyl i backendowe progi nie są skalibrowanym confidence MODEL.
- Brak referencji źródłowej jest problemem do rozwiązania; sama obecność referencji jeszcze nie dowodzi zgodności. Ponownie sprawdź właściwy region, a nie tekst z innego przebiegu modelu.
- Wykrywaj pominięte końce stron, powtórzone wygenerowane ogony, urwane bloki i niewłaściwą kolejność. Naturalne powtórzenie widoczne w dokumencie nie jest degeneracją modelu.
- Długie dokumenty przetwarzaj partiami z jawnym stanem pokrycia. Limity narzędzia lub kontekstu nie pozwalają ogłosić kompletnego wyniku z części stron.
- Zachowuj UTF-8, polskie znaki, granice stron oraz poprawne JSON. Różnice CRLF/LF nie mogą scalać stron ani usuwać pustych akapitów mających znaczenie strukturalne.
- Granica strony pozostaje źródłowym odniesieniem także w nowym widoku MD: nazwa raz, `[s. x]`, opcjonalna permutacja uwzględnionych bloków. Nowsza decyzja użytkownika zastępuje obowiązkowe długie tagi; `legacy_pages` zachowuje poprzedni format jako opcję. JSON i PDF nie zmieniają fizycznej kolejności.
- Zwięzły MD używa GFM dla prostych tabel i HTML tylko dla koniecznych relacji. Oba końce deduplikacji muszą być niechronionymi elementami formy. Status dokumentu, daty, podpisy i istotne warianty są chronione także w opisach grafiki; mieszane regiony trzeba rozdzielić.
- Wznowienie wymaga zgodnego hash źródła, wersji reguł/parametrów i poprawnych wyników; sam plik MD lub napis „komplet” nie wystarczą. Korekta użytkownika unieważnia zależne wyniki, dopóki nie przejdą kontroli ponownie.
- Równość tekstu nie dowodzi równości podpisów, pieczęci, adnotacji i obrazów. Nie usuwaj stron ani oryginałów na podstawie tekstowego hasha.
- Zachowany OCR wymaga kontroli geometrii w `keep` i poza naprawą `patch`, także bez opcjonalnych search checks. `patch` obejmuje pojedyncze całe słowa; dopasowanie obrysu wielowyrazowej linii może przesunąć jej słowa i nie jest dowodem poprawnej lokalizacji.

Hash oryginału, wersja kontraktu, QA, pytania/odpowiedzi i decyzje pozostają w review oraz deterministycznym rdzeniu LOG. Usunięcie `schema_version` i `source.sha256` z publicznego JSON w 0.2.0 nie usuwa kontroli integralności. `seal` porównuje rdzeń z aktualnymi plikami; dopiski dostawy są osobnymi ustrukturyzowanymi zdarzeniami, nie ręczną redakcją LOG.

## Podpisy: rozdzielona ścieżka dowodowa

Rzeczywistą obecność podpisu cyfrowego ustala struktura PDF, nie render, pieczęć, tekst „podpisano” ani wygląd kreski. Puste pole podpisu nie jest osadzonym podpisem. Wypełniony kandydat z wadliwym/brakującym ByteRange pozostaje `malformed` albo `unknown`, nigdy zwykłym brakiem. Niepowodzenie detekcji to stan nieustalony. Dla obrazu walidacja osadzonego podpisu PDF nie ma zastosowania; dla poprawnie sprawdzonego PDF bez podpisu etap jest pomijany normalnie. Każde wejście otrzymuje jednak pełny raport stanu z `check(source)` w `review.signature_report`; obie bramki wydania wiążą go z oryginalnymi bajtami i detekcją.

Jeżeli podpis jest obecny, badanie techniczne dotyczy oryginalnych bajtów. Rozróżnij integralność valid/invalid/unknown, zakres podpisanej rewizji, późniejsze zmiany, zaufanie do certyfikatu i powody nieweryfikacji. Wystąpienie późniejszej rewizji nie dowodzi samo w sobie niedopuszczalnej modyfikacji. Błąd jednego podpisu nie powinien ukrywać pozostałych.

Dane podmiotu/wystawcy/serii certyfikatu, deklarowany czas podpisania, znaczniki treści, podpisu i dokumentu oraz wyniki/ograniczenia badania należą do LOG. Brak jednego rodzaju czasu nie dowodzi braku pozostałych. Deklarowany czas nie jest automatycznie zaufanym timestampem. Próba walidacji, jej ukończenie i zakres częściowy są osobne, także per podpis; wyjątek przed obliczeniami nie daje completed/performed. Brak zaufania może mieć różne przyczyny; nie zgaduj jednej. Nie deklaruj statusu podpisu kwalifikowanego bez faktycznie przeprowadzonego badania wymagającego odpowiednich źródeł zaufania. MODEL sam nie wykonuje kryptografii.

Operacja jest odczytowa, niczego nie podpisuje. Searchable PDF jest pochodną i nie odziedzicza twierdzenia, że jego nowe bajty podpisał autor oryginału. Walidator niedostępny oznacza jawnie niewykonany zakres sprawdzenia w LOG, a nie wadę dokumentu.

## Co zastąpiono lub wyłączono

Nie uruchamiaj dawnych ścieżek OpenDataLoader, MarkItDown, LiteParse/Tesseract, Chandra/Gaius, contextgem/Ollama ani innych silników odczytu. Biblioteka renderująca/zapisująca PDF oraz techniczny walidator podpisu nie są silnikami OCR.

Usunięto maskowanie, anonimizację i kancelaryjne bramki wysyłki; pozostaje wierność źródła oraz pytania o faktycznie niepewny odczyt. Nie ma indeksu FTS5, wyszukiwarki akt, chronologii ani raportu prawnych findings. Wzorce konceptów i granic dokumentów pozostają powyżej jako zachowana wiedza. Nie deklaruj obsługi DOCX/OOXML na podstawie starego CLI — bieżący zakres wejścia to PDF i obsługiwane obrazy.
