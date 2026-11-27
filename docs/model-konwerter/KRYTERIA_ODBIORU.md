# MODEL Konwerter — kryteria odbioru i instrukcja niezależnego audytu

**Wersja:** 1.0, 2026-11-27.  
**Kontrakt oceniany:** [ZALOZENIA.md](ZALOZENIA.md), R01–R45.  
**Status tego dokumentu:** plan weryfikacji, bez nowych wyników wykonania.

Kryteria określają oczekiwany wynik niezależnie od implementacji. Nie należy używać tego samego błędnego OCR lub wygenerowanego JSON jako jedynego wzorca dla wszystkich pozostałych plików. Wzorzec treści i lokalizacji musi odwoływać się do rzeczywistego źródła.

Potwierdzone ustalenia wcześniejszych audytów przyjmujemy jako materiał wejściowy. **Ten dokument nie zleca ponownego odtwarzania identycznych błędów starej wersji.** Po poprawce sprawdza się nowy kod względem odpowiadającego kryterium, zachowując dowód badanego commita.

## 1. Jak oznaczać dowody

| Rodzaj | Co potwierdza | Czego sam nie dowodzi |
|---|---|---|
| **D — przegląd dokumentacji/kodu** | Obecność reguły, deklarowany zakres, zgodność ścieżek i parametrów. | Wykonania, prawidłowego OCR lub dostawy. |
| **E — wykonanie deterministyczne** | Zachowanie uruchomionego helpera na określonych plikach, zapisane wyniki i inwarianty. | Trafności odczytu obrazu przez MODEL i semantycznej decyzji o pominięciu. |
| **V — weryfikacja źródła wizualnego** | Treść, położenie i relacje widoczne w konkretnych stronach/cropach; realny odczyt MODEL. | Poprawności kryptografii ani zapisu w usłudze. |
| **H — rzeczywista odpowiedź użytkownika** | Rozstrzygnięcie konkretnego niepewnego regionu albo akceptację nieczytelności. | Poprawności innych regionów i prawdziwości modelowej deklaracji bez odpowiedzi. |
| **I — integracja w docelowym hoście/usłudze** | Rzeczywisty import, dostęp do narzędzi, upload, odczyt zwrotny i dostarczenie pliku. | Uniwersalnej zgodności innych hostów i wersji. |

Test może wymagać kilku rodzajów dowodu. Test ze spreparowaną odpowiedzią backendu sprawdza serializację, nie rzeczywistą kryptografię. Test z gotowym planem transkrypcji sprawdza składanie, nie nowy odczyt MODEL. Równy hash wiąże artefakty, ale nie potwierdza sam poprawnej treści.

## 2. Macierz wymagań

Kxx odpowiada Rxx w specyfikacji. Wynik każdego wiersza należy dopisać w **nowym raporcie audytu**, nie w tej macierzy.

| Kryterium | Sprawdzenie i oczekiwany wynik | Dowód | Powiązanie |
|---|---|---|---|
| **K01 / R01** | Jedno wejście prowadzi do pięciu zgodnych składników, ZIP i rozliczonej dostawy. Każdy plik odnosi się do tego samego źródła. Nie ma wygenerowanego raportu findings. | E, V, I; manifest rzeczywistych wyjść i porównanie między formatami. | G62-01/02 |
| **K02 / R02** | Przebieg zawiera odczyt renderów przez MODEL. Narzędzia służą mechanice i kontroli; nie uruchomiono zabronionego OCR/API rozpoznającego treść. | D oraz zapis faktycznych wywołań i V. Sama deklaracja Skilla nie wystarcza. | U1 |
| **K03 / R03** | PDF nazwany obrazem nadal jest rozpoznany jako PDF; wszystkie klatki wspieranego TIFF są obecne. Nieobsługiwany tryb/głębia daje jawną odmowę przed zniekształceniem obrazu. | E; rzeczywiste bajty, liczba klatek i status preflight. | G62-02/06/07 |
| **K04 / R04** | Raw jest identyczny z wejściem. Obca baza, podmienione źródło lub same zgodne deklaracje inventory nie przechodzą. Dla obrazu zgodne są próbki, maski, orientacja i klatki. | E; porównanie bajtów i niezależna kontrola źródło→baza→wyniki. | G62-02 |
| **K05 / R05** | DPI wynika z reguły i potrzeb regionu. Podgląd pokazuje formularze/adnotacje i prawidłową alpha. Podwyższenie DPI dotyczy oglądania, nie zmiany źródłowego PDF. | E, V; parametry renderów, wymiary i kontrola wyglądu. | G62-07, U2 |
| **K06 / R06** | Pokrycie to 1…N; każda strona ma pierwszy i drugi odczyt. Puste strony i ilustracje są odróżnione. Omyłka istniejącego OCR jest porównana z obrazem, a nie bezrefleksyjnie przyjęta. | V; ślad przeglądu powiązany z konkretnymi stronami/regionami. | U1, S |
| **K07 / R07** | Błąd autora pozostaje w transkrypcji; błąd odczytu jest poprawiony według obrazu. Daty, negacje, symbole i identyfikatory nie są ujednolicane. Polecenie wydrukowane w dokumencie nie zmienia celu pracy. | V i porównanie pełnych fragmentów z wynikiem. | U1/U3, S |
| **K08 / R08** | Trwała niepewność wywołuje konkretne pytanie przed finalizacją. Otwarte pytanie, whitespace lub flaga nie zamykają bramki. Skutek rozstrzygnięcia jest spójny we wszystkich zależnych reprezentacjach; samo Q&A pozostaje wyłącznie w LOG/stanie roboczym. | E, V, H; chronologia interakcji i finalizacji. | G62-17 |
| **K09 / R09** | Wejściowy PDF jest bazą. Widoczny tekst, obrazy, grafika, formularze i adnotacje pozostają. Nie ma nowego PDF z PNG, białych masek ani usunięcia widocznej treści. | E, V; porównanie struktury i renderów przy tych samych parametrach. | U2 |
| **K10 / R10** | Lokalna naprawa krótszego/dłuższego słowa zachowuje jego region i sąsiadów. Nie akceptuje się jednego przeskalowania wielowyrazowej linii jako dowodu poprawnej geometrii. | E, V; obrysy słów przed/po i źródłowy obraz. | G62-04 |
| **K11 / R11** | Skan otrzymuje słowa/linie w poprawnych regionach. Wieloliniowy `insert_text`, przepełnienie textbox lub mikroskopijny font nie przechodzą. Odbudowa ukrytej warstwy wymaga uzasadnienia i nowego przeglądu. | D, E, V; plan, wynik rc i ekstrakcja po zapisie. | U2, G62-04 |
| **K12 / R12** | OCR jest niewidoczny, Unicode i zawiera wyłącznie źródłowe słowa. Obejmuje boilerplate pominięty w MD. Opisy grafiki nie pojawiają się jako wymyślone słowa OCR; brak starych błędnych duplikatów. | E, V; tekst, widoczność i krotność wystąpień. | U1/U2 |
| **K13 / R13** | Po otwarciu zapisanego wyniku: zero znaków poza stroną z tolerancją 2 pt i pełna ekstrakcja ograniczona do strony. Kontrola obejmuje obrót 90°/270° i niezerowy CropBox. | E; zapis wyniku QA i standardowego odczytu. | U2 |
| **K14 / R14** | `keep` z OCR przesuniętym względem obrazu nie może zostać uznany za poprawny tylko dlatego, że zachowano wejściowe współrzędne. W patch zachowane są pozostałe słowa; wyszukiwanie trafia we właściwe wystąpienie. | E i V obowiązkowo; opcjonalne search checks nie zwalniają z bramki. | G62-04/05 |
| **K15 / R15** | Wymiary, strumienie, zawartość, maski i położenia źródłowych obrazów są zgodne. Podmiana obrazu tej samej wielkości lub przesunięcie nie przechodzą. Przyrost rozmiaru nie wynika z rekompresji. | E; porównanie obrazów/obiektów i renderów, rozliczenie rozmiaru. | U2 |
| **K16 / R16** | Bezpośrednie `seal` sprawdza ten sam zestaw rzeczywistych zależności co `stage`. Zmiana pliku po stage, brak raportu lub niespójny LOG blokują wydanie. `validate` opisuje swój węższy zakres. | E; wynik obu ścieżek na zmienionych artefaktach poprawionej wersji. | G62-02/09/11/17 |
| **K17 / R17** | Wszystkie strony i regiony są obecne w JSON; ID/typ/kolejność są jednoznaczne. Strona z samą ilustracją ma opis, a zwykłe kontakty pominięte w MD nadal mają treść i bbox. | E, V; porównanie pełnego inventory źródła z JSON. | G62-08/16 |
| **K18 / R18** | Wymiary JSON odpowiadają wyświetlanemu CropBox; nie przechodzi 1×2 pt dla strony 600×800 pt. Bbox i przeliczenia działają przy obrocie/offsetach. | E; wzorcowa geometria i odtworzone regiony. | G62-03 |
| **K19 / R19** | Dwa odległe `PLT` z dwiema ramkami całej strony są odrzucone. Dwa ciasne, odrębne regiony przechodzą. Prawidłowy długi blok z liniami przechodzi. | E, V; porównanie z niezależnymi obrysami i przypisaniem wystąpień. | G62-03, DPL-01 |
| **K20 / R20** | Podpis narysowany po lewej z bboxem w przeciwległym rogu nie otrzymuje statusu poprawnej lokalizacji. Tekstowe `words: 0` nie daje pozytywnego wyniku kontroli grafiki. Poprawny region ma osobny ślad wizualnego przeglądu. | V; crop z kontekstem i powiązanie strona/ID/bbox w LOG; H tylko gdy rzeczywiście potrzebne. | G62-08, DPL-02 |
| **K21 / R21** | Tabela bez struktury, konflikt `PLT 304`/`PLT 999`, zamienione wiersze, puste komórki zasłaniające cudze słowa i niespójne lines/cells są blokowane, także bez planu. Poprawne puste/scalone komórki przechodzą. | E, V; pełna macierz komórek, geometria i wszystkie obecne reprezentacje. | G62-01/16/17 |
| **K22 / R22** | Poprawne kolumny w kolejności LEFT1, LEFT2, RIGHT1, RIGHT2 nie są odrzucone wyłącznie przez przeplatanie ekstraktora. Zmieniona wartość lub przypisanie komórki nadal blokuje odbiór. | E, V; porównanie logicznych fragmentów, krotności i bboxów. | DPL-04 |
| **K23 / R23** | MD nie dopisuje ani nie parafrazuje faktów. Każde zdanie/wartość ma oparcie w źródle; pominięcia ograniczają się do dozwolonej formy. Nie ma własnej diagnozy, zarzutu ani streszczenia. | V; niezależne porównanie treści MD→JSON→źródło. | U3 |
| **K24 / R24** | Wszystkie chronione dane pozostają: daty z rolami, osoby/PWZ, wyniki, statusy, ślady podpisów i oświadczenia. Błędna rola boilerplate nie usuwa WBC, glukozy, odbioru 2 egzemplarzy lub zwrotu oryginałów. | E, V; przypadki mieszane i kontrola semantyczna na obrazie. | G62-08/12/15, DPL-03 |
| **K25 / R25** | Zwykły telefon/ankieta mogą zniknąć z MD, ale pozostają w JSON/PDF. Mieszany blok dzieli się przed pominięciem. Termin wizyty, zalecany kontakt i wariant podmiotu pozostają. | V i ledger pominięć w LOG powiązany z blokami. | G62-12/15, DPL-03 |
| **K26 / R26** | Deduplikacja nie usuwa wyników, dat, podpisów i oświadczeń. Nie można użyć chronionego faktu jako celu duplikatu stopki. Rzeczywiście identyczna, niechroniona forma może zostać skrócona. | E, V; kontrola obu końców każdej relacji. | G62-12 |
| **K27 / R27** | Bez osobnego wyboru profilu każda fizyczna strona rozpoczyna się dokładnym tagiem `==== <original_filename> (Page x/y) ====`. Liczba i kolejność stron są pełne. Compact wymaga utrwalonego wyboru użytkownika. | E; porównanie literalnych znaczników; H/decyzja wejściowa dla wariantu. | U1; rozbieżność DEC-01 |
| **K28 / R28** | Prosta tabela używa GFM, konieczne scalenia zachowują relacje. Surowe `< 0,1` i `D-dimer & INR` są czytelne bez zbędnych encji. Separator `\|` i backslash nie uszkadzają komórek. | E, V; surowy MD i sparsowana struktura, nie tylko render. | G62-15, DPL-05 |
| **K29 / R29** | MD/JSON są wolne od informacji procesu. JSON zachowuje tylko niezbędną identyfikację treści/geometrię. Hash, wersja schematu, QA i Q&A znajdują się w LOG/stanie roboczym. | E, D; kontrola kluczy, składni i treści opisów. | G62-15 |
| **K30 / R30** | Unsigned PDF normalnie pomija kryptografię; obraz daje N/A. Puste pole nie staje się podpisem. Wypełniony uszkodzony `/Sig` pozostaje kandydatem, błąd detekcji stanem nieustalonym. | E; rzeczywiste struktury źródeł i wynik detekcji. | G62-10 |
| **K31 / R31** | Istniejący podpis bada się na raw. Rozdzielone są integralność, zaufanie, rewizje i ograniczenia. Brak backendu nie daje valid/invalid. Searchable nie jest przedstawiany jako podpisany przez autora raw. | E z rzeczywistym podpisem; osobny wynik niewykonanego zakresu. Mock daje tylko dowód testu serializacji. | G62-09/13/14 |
| **K32 / R32** | Raport obcego źródła lub bez związania hashem jest blokowany. Czas deklarowany i trzy rodzaje timestampu są osobne. Błąd przed obliczeniami nie daje completed/performed; pozostałe podpisy nie znikają. | E; raport wykonania, wykryte podpisy i wynik sprawdzenia związania. | G62-09/13/14 |
| **K33 / R33** | Podmiana LOG na dowolny tekst lub zmiana hashy/QA jest wykrywana. Rdzeń odpowiada aktualnym plikom; prawidłowy receipt nie wymaga cyklicznego hasha LOG/ZIP. | E; rekonstrukcja rdzenia i porównanie z wydanym LOG. | G62-11 |
| **K34 / R34** | W bundle jest dokładnie searchable PDF, MD, JSON, LOG oraz raw z oryginałem. Brak renderów, planu, review i dodatkowego indeksu; nazwy są jednoznaczne. | E; lista faktycznych ścieżek i powiązanie ze źródłem. | U1/U4 |
| **K35 / R35** | ZIP ma zatwierdzoną zawartość, poprawne ścieżki i integralność. Rozpakowane pliki są identyczne z wydanym bundle; nie zawiera plików pośrednich lub siebie samego. | E; odczyt archiwum, lista i hashe. | U1 |
| **K36 / R36** | Rzeczywisty zapis do root/Konwerter/stem/raw i plików głównych jest potwierdzony. Kolizja nie nadpisuje innego źródła, a uprawnienia nie są zmieniane. Receipts odnoszą się do aktualnych bajtów. | I; wyniki Drive, rodzice/ID/nazwy/rozmiary, checksumy lub odczyt zwrotny. | U1, G62-11 |
| **K37 / R37** | Odpowiedź zawiera jeden ZIP i sprawdzony link do katalogu, bez pojedynczych artefaktów. Nieudany upload jest opisany jako niedokończona dostawa, nawet gdy lokalny ZIP jest poprawny. | I; rzeczywista odpowiedź i stan usługi. | U1 |
| **K38 / R38** | Praca partiami nie gubi stron. Wznowienie po innym źródle/zmianie treści odrzuca nieaktualny stan lub ponawia zależne kontrole. Korekta użytkownika nie zostawia starszego MD/JSON/PDF. | E, V; ledger pokrycia, hashe i zależności korekty. | S |
| **K39 / R39** | Każda istotna reguła źródłowa ma pochodzenie, decyzję i miejsce docelowe. Po wyłączeniu backendu/anonimizacji/indeksu inne kroki nie znikają bez uzasadnienia. Jest jeden główny Skill. | D; porównanie źródeł z mapą i faktycznymi instrukcjami. Liczba 95 nie zastępuje porównania. | U1, S |
| **K40 / R40** | Nie wykonano anonimizacji, dawnego OCR, indeksowania akt ani generowania własnych findings. Wyłączenie tych funkcji nie usuwa chronionej treści dokumentu. | D, E, V; przebieg i lista wyjść. | U1/U3 |
| **K41 / R41** | Na deklarowanym środowisku zależności/font są dostępne udokumentowaną drogą. Brak zasobu daje konkretną blokadę, bez cichej podmiany lub obietnicy nieweryfikowanej platformy. | E, I; środowisko, wersje i uruchomienie od czystego stanu. | DPL-06 |
| **K42 / R42** | Raport rozdziela wynik autora, niezależne wykonanie, statyczny przegląd i brak testu. Wskazuje commit i dane. Nie utożsamia znaków z tokenami, mocka z kryptografią ani helpera z jakością MODEL. | D; sprawdzalne odniesienia do faktycznych dowodów. | DPL-06 |
| **K43 / R43** | Publiczny commit zawiera wyłącznie potrzebne źródła produktu i bezpieczne materiały. Syntetyczne przykłady są oznaczone; dokumenty użytkownika nie zostały publikowane w ramach samego zapisu specyfikacji. | D; zakres zmian i zawartość materiałów. | U4, granica publikacji |
| **K44 / R44** | Raport pokrywa R01–R45, przy każdym wyniku podaje zakres/dowód. Niewykonany test pozostaje NOT_TESTED; N/A ma konkretną przyczynę. Przyjęte audyty są odróżnione od nowych wyników. | D; kompletność i spójność raportu. | U3/U4 |
| **K45 / R45** | Manifest marketplace rozwiązuje ścieżkę istniejącego pluginu; komponenty są zgodne. Osobno udokumentowano rzeczywisty import/uruchomienie hosta, jeżeli wykonano. Sam repozytoryjny JSON nie daje statusu import PASS. | D, E dla struktury; I dla importu i wykonania. | U4, DPL-06 |

## 3. Minimalne grupy przypadków dla nowego wydania

Grupy są planem kontroli przyszłej poprawionej wersji, nie poleceniem powtarzania baseline 0.1.0 lub wykonanych prób A2.

| Grupa | Wymagane odmiany | Kryteria |
|---|---|---|
| Źródła | PDF native, czysty skan, istniejący OCR poprawny/błędny, strona mieszana, PNG/JPG, alpha i obsługiwany wieloklatkowy TIFF; jawnie nieobsługiwany obraz wysokiej głębi. | K03–K06, K09–K16 |
| Geometria | Obrót 90°/270°, CropBox z offsetem, powtórzona fraza, dwa nadmiernie szerokie bboxy, krótki i długi blok, tekst w dwóch kolumnach. | K13–K14, K18–K22 |
| Treść chroniona | Różne daty z rolami, różne osoby w nagłówku i pieczęci, puste pole podpisu, odręczny dopisek, status, wyniki i oświadczenia odbioru. | K07–K08, K17, K20, K23–K26 |
| Tabele | Puste/scalone komórki, nagłówki, jednostki/zakresy, symbole `<`, `≥`, `µ`, separator `\|`, konflikt text/lines/cells, szeroki bbox i przypisanie do złego wiersza. | K21–K22, K28 |
| Fałszywa klasyfikacja | WBC/glukoza/oświadczenie odbioru błędnie oznaczone jako ankieta/kontakt/instrukcja nośnika oraz rzeczywista nieszkodliwa ankieta. | K24–K26 |
| Podpisy | Unsigned PDF, obraz, puste pole, malformed kandydat, obecny podpis z rzeczywistą walidacją, brak backendu i wyniki częściowe. | K30–K32 |
| Finalizacja | Obca baza, podmiana artefaktu po stage, bezpośrednie seal, LOG zastąpiony tekstem, nieaktualny receipt, kolizja Drive, przerwanie i wznowienie. | K04, K16, K33–K38 |
| Host | Czyste deklarowane środowisko, rzeczywisty odczyt MODEL, import marketplace oraz pełny zapis/odczyt Drive. | K02, K06, K36–K37, K41–K45 |

### Geometria: co musi być mierzalne

- Granice strony: **2 pt** tolerancji z R13; zero znaków poza dopuszczonym obszarem.
- Wymiary strony JSON: obecny kontrakt helpera stosuje **0,01 pt** względem wyświetlanego CropBox. W raporcie podać faktyczne wartości i macierz, nie tylko `PASS`.
- Lokalizacja krótkiego tekstu: porównać z niezależnie wyznaczoną obwiednią słów, z uwzględnieniem konkretnego wystąpienia. W syntetycznych próbach z dokładnie znaną geometrią kryterium odbioru tej specyfikacji dopuszcza maksymalnie **2 pt nadmiaru na każdej krawędzi** krótkiego regionu tekstowego. To techniczne doprecyzowanie próby, nie cytat pierwotnego polecenia ani globalny limit wielkości akapitu.
- Długi blok: jego obwiednia może obejmować odstępy wewnętrzne. Precyzję należy potwierdzić na liniach/podblokach; poprawny wielowierszowy akapit nie odpada jedynie za powierzchnię całego bloku.
- Grafika/puste pole: dodatni test słów nie wystarcza. Potrzebny jest oddzielny wizualny dowód regionu na źródłowym obrazie. Nie wolno nadawać statusu `human_verified` na podstawie samej deklaracji MODEL.

Nie wolno zwiększać tolerancji po obejrzeniu nieudanego wyniku wyłącznie w celu uzyskania PASS. Zmiana metody lub progu wymaga jawnego uzasadnienia i ponownej oceny kryterium.

## 4. Format raportu niezależnego audytu

Nowy raport należy zapisać w osobnym katalogu `audyt/<data-czas>_<wersja-lub-commit>/`, zachowując wcześniejsze raporty. Raport powinien zawierać:

1. Repozytorium, dokładny commit, wersję specyfikacji i artefakt/zakres oceniany. Jeśli plugin instalowany w ChatGPT różni się od GitHub, podać oba źródła i zakres porównania.
2. Środowisko, wersje narzędzi, identyfikację wejść oraz informację, czy były syntetyczne. Dane prywatne nie są potrzebne w publicznym raporcie.
3. Macierz K01–K45 z wynikiem i odnośnikiem do dowodu. Jeżeli jeden wiersz obejmuje kilka sposobów kontroli, rozdzielić podwyniki.
4. Przyjęte wcześniejsze ustalenia, nowe wykonania, przegląd statyczny i zakres niewykonany jako odrębne informacje.
5. Dla błędu: wymaganie, obserwację, oczekiwany wynik, wpływ oraz minimalny warunek zamknięcia. Rzeczywiste dane nie są warunkiem publicznej reprodukcji.
6. Werdykt ograniczony do sprawdzonego zakresu. Liczba testów sama nie daje pełnego odbioru.

| Wynik | Znaczenie |
|---|---|
| `PASS` | Wymaganie sprawdzone odpowiednim dowodem dla wskazanej wersji i wejścia. |
| `FAIL` | Konkretny dowód naruszenia wymagania albo fałszywego odrzucenia poprawnego przypadku. |
| `NOT_TESTED` | Brak wykonania/dowodu; brak potwierdzenia nie jest PASS. |
| `BLOCKED` | Kontrola nie mogła zostać ukończona z podanego konkretnego powodu. |
| `N/A` | Warunek rzeczywiście nie dotyczy wejścia, np. kryptografia dla unsigned PDF; potrzebna przyczyna i dowód detekcji. |

Przykładowy pusty wiersz raportu, nie wynik testu:

```text
K20 / R20 | NOT_TESTED | commit: ... | wejście: ...
Potrzebny dowód: osobny przegląd źródłowego regionu podpisu.
Zakres: nie utożsamiać pozytywnej geometrii tekstu z położeniem grafiki.
```

## 5. Warunek odbioru i zmiany zakresu

Pełny odbiór wymaga dowodów dla wszystkich mających zastosowanie wymagań. Otwarte ustalenie naruszające treść, lokalizację, pochodzenie albo bramkę finalizacji nie może zostać zamknięte samą zmianą dokumentacji. Pozytywny odbiór helperów nie zastępuje V/H/I.

Zalecenia rozwojowe DPL-06 — CI, wieloplatformowe przygotowanie zależności i rozległy benchmark — rozlicza się osobno. Brak benchmarku blokuje odpowiednie twierdzenia o jakości/wydajności; nie dowodzi sam w sobie błędu odczytu konkretnej strony. Szczegółowy stan dotychczasowych dowodów i rozbieżności opisuje [STAN_I_DECYZJE.md](STAN_I_DECYZJE.md).
