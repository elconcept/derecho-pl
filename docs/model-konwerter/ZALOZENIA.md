# MODEL Konwerter — założenia i wymagania produktu

**Wersja specyfikacji:** 1.0, 2026-11-27.  
**Produkt:** `model-document-converter`, jeden główny Skill `model-ocr`.  
**Rola dokumentu:** normatywny punkt odniesienia dla implementacji i niezależnego audytu.  
**Zakres:** konwersja pojedynczego dokumentu PDF lub obsługiwanego pliku obrazu do spójnego pakietu.

Ta specyfikacja zapisuje oczekiwane zachowanie wynikające z zamówienia użytkownika. **Nie jest deklaracją, że wersja 0.2.0 spełnia wszystkie wymagania.** Aktualne ograniczenia i ustalenia audytów znajdują się w [stanie i decyzjach](STAN_I_DECYZJE.md), a sposoby ich sprawdzenia w [kryteriach odbioru](KRYTERIA_ODBIORU.md).

## Spis treści

1. [Cel i źródła wymagań](#cel-i-źródła-wymagań)
2. [Wejście, odczyt i niepewność — R01–R08](#wejście-odczyt-i-niepewność--r01r08)
3. [Searchable PDF — R09–R16](#searchable-pdf--r09r16)
4. [JSON i lokalizacja — R17–R22](#json-i-lokalizacja--r17r22)
5. [Markdown — R23–R29](#markdown--r23r29)
6. [Podpisy cyfrowe — R30–R32](#podpisy-cyfrowe--r30r32)
7. [LOG i dostawa — R33–R38](#log-i-dostawa--r33r38)
8. [Skill, dystrybucja i audyt — R39–R45](#skill-dystrybucja-i-audyt--r39r45)
9. [Warunek zakończenia](#warunek-zakończenia)

## Cel i źródła wymagań

Użytkownik analizuje wiele stron dokumentów, w szczególności dokumentację medyczną. Potrzebuje zwartego tekstu do wyszukiwania potencjalnych ustaleń, dokładnego wskazania regionu źródłowego i zachowanej kopii dokumentu. Konwersja ma zachować również informacje mogące ujawnić rozbieżności: różne role dat, osoby wymienione w różnych miejscach, odmienne pieczęcie, puste pola i statusy dokumentu.

| Reprezentacja | Zadanie |
|---|---|
| Markdown | Materiał do późniejszej analizy przez LLM; wskazuje, gdzie szukać potencjalnego ustalenia. |
| JSON | Pełna reprezentacja treści i układu; umożliwia wstępną weryfikację i odnalezienie właściwego regionu. |
| Searchable PDF | Wizualnie zachowana kopia źródła z poprawną niewidoczną warstwą tekstową. |
| `raw/` | Niezmienione bajty wejściowego pliku. |
| `LOG.md` | Pochodzenie, działania, decyzje, pytania, ograniczenia, wyniki kontroli i rzeczywista dostawa. |

Specyfikacja nie ocenia autentyczności konkretnego dokumentu ani odpowiedzialności jego autora. Nie publikuje prywatnej dokumentacji, danych sprawy lub korespondencji użytkownika.

### Podstawa i hierarchia

| Źródło | Znaczenie |
|---|---|
| **U1 — pierwotne zamówienie** | Jeden Skill MODEL; PDF/obrazy; dynamiczne DPI; OCR, MD, JSON, LOG i raw; pytania przed finalizacją; Drive i ZIP; wyłączenie dawnych backendów, anonimizacji i indeksu akt; pełne tagi stron. |
| **U2 — uwagi po smoke teście** | Oryginalny PDF jako baza, zachowanie obrazów, geometria słów/linii i twarda kontrola po zapisie. |
| **U3 — doprecyzowanie celu MD i audyt 0.1.0** | MD ma oszczędzać kontekst, zachowywać informacje istotne dla analizy i usuwać rutynowy szum. Użytkownik polecił przyjąć 17 ustaleń G62 za potwierdzone i nie odtwarzać identycznego audytu ponownie. |
| **U4 — zamówienie repozytorium i dokumentacji założeń** | `derecho-pl` ma zawierać marketplace i kolejne pluginy; założenia muszą umożliwiać niezależny audyt bez dostępu do rozmowy. |
| **A1 — przyjęty audyt 0.1.0** | G62-01…G62-17; repozytoryjne [rozliczenie autora](../../plugins/model-document-converter/docs/AUDIT_REMEDIATION.md) pomaga odnaleźć wymagania, ale nie zastępuje niezależnego dowodu. |
| **A2 — niezależny audyt 0.2.0** | [Raport w `audyt/`](../../audyt/2026-11-27T03-25-01Z_v0.2.0/AUDYT_DERECHO_PL_0_2_0.md), dotyczący commita `18f6fffc8bc1a82677ebe9b88dc1d60fdf7fa096`. DPL-01…DPL-06 wskazują dalsze luki i zalecenia. |
| **S — dostarczone skille źródłowe** | Wiedza rozliczona w [mapie zachowania](../../plugins/model-document-converter/docs/SELF_EVALUATION.md), [pochodzeniu źródeł](../../plugins/model-document-converter/docs/SOURCE_PROVENANCE.md) i [zachowanej wiedzy](../../plugins/model-document-converter/skills/model-ocr/references/retained-knowledge.md). |

Polecenia użytkownika są nadrzędne. Ten dokument je porządkuje i doprecyzowuje warunki odbioru; nie może ich po cichu osłabiać. Kod, schemat, instrukcja Skilla i raport autora są przedmiotem audytu, nie samodzielnym dowodem spełnienia zamówienia. Zalecenia audytora dotyczące rozwoju, np. CI lub benchmarku, są oznaczone oddzielnie od pierwotnych wymagań użytkownika.

Słowo **musi** oznacza wymaganie obowiązkowe dla ukończonej konwersji. **Może** oznacza wariant dozwolony pod opisanymi warunkami. Świadomie nieobsługiwane wejście musi zakończyć się jawną informacją o braku obsługi; odmowa nie jest udaną konwersją. Każde R01–R45 ma osobne kryterium odbioru. Dodanie tych dokumentów nie zamyka żadnego ustalenia audytu.

## Wejście, odczyt i niepewność — R01–R08

### R01 — jeden spójny proces

Plugin musi prowadzić od rzeczywistego pliku wejściowego przez wizualny odczyt, korektę OCR, przygotowanie MD/JSON, rozstrzygnięcie niepewności, kontrolę i dostawę. Wszystkie reprezentacje muszą dotyczyć tego samego źródła. Poprawny pojedynczy plik nie wystarcza do uznania całego pakietu za poprawny. Konwerter przygotowuje materiał do późniejszej analizy; nie generuje własnego raportu findings.

### R02 — MODEL jako czytnik

Odczytu dokonuje MODEL oglądający strony i regiony źródłowe. Nie wolno zastąpić go OpenDataLoader, MarkItDown, Tesseract, LiteParse, Chandra/Gaius, ContextGem/Ollama ani innym zewnętrznym silnikiem OCR lub API modelu. Biblioteki mogą renderować, odczytywać strukturę PDF, mierzyć geometrię, zapisywać zatwierdzony tekst, sprawdzać kryptografię, pakować i dostarczać pliki. Generowanie obrazów nie służy poprawianiu ani odtwarzaniu dokumentu. To wymaganie metody; samo użycie MODEL nie dowodzi lepszej dokładności od innych systemów.

### R03 — rzeczywisty typ i zakres wejścia

Wejściem są PDF i obrazy, w tym PNG/JPG oraz obsługiwane warianty TIFF i innych formatów. Typ ustala się z zawartości, nie tylko rozszerzenia lub pola `source_kind`. Dla obsługiwanego obrazu wieloklatkowego należy zachować wszystkie klatki i kolejność. Nie łączy się odrębnych plików ani nie dzieli jednego wejścia na osobne dokumenty bez polecenia.

Każdy wspierany wariant musi zachowywać próbki, orientację i przezroczystość. Gdy nie można tego zapewnić, przygotowanie zatrzymuje się przed wytworzeniem fałszywego wyniku. Dotyczy to także uszkodzonych/zaszyfrowanych PDF oraz nieobsługiwanej głębi obrazu. Aktualne odrzucanie >8 bitów, trybów integer/float i części CMYK jest ograniczeniem 0.2.0, a nie pierwotnym celem produktu.

### R04 — pochodzenie i raw

`raw/<oryginalna_nazwa>` musi być bajtowo identyczne z wejściem. Dla PDF baza używana do budowy wyniku musi być oryginalnym PDF. Dla obrazu bazowy PDF musi przedstawiać faktyczne piksele, maski, orientację i klatki oryginału. Należy sprawdzić zależność **oryginał → baza → searchable PDF → JSON/MD**, a nie tylko osobne deklaracje hashy. Hash źródła i dowód tej zależności należą do LOG/stanu roboczego.

### R05 — renderowanie do odczytu

Dla PDF obowiązuje reguła przejęta ze źródeł:

```text
dpi = max((1024 / min(width_pt, height_pt)) * 72, 192)
```

To punkt wyjścia. Mały druk, pieczęcie, daty i identyfikatory wymagają odpowiednio wyższego DPI lub cropów z otoczeniem, np. 300/450/600 DPI. Należy zapisać faktyczne parametry i przeliczenia. Podgląd musi pokazywać CropBox, obrót, widoczne formularze i adnotacje. Ewentualne spłaszczenie do oglądania odbywa się wyłącznie na kopii roboczej.

Dla obrazu podgląd ma zachować prawidłowy kontrast i alpha; może być renderem sprawdzonej bazy PDF na bieli. Krótszy bok podglądu jest w razie potrzeby powiększany do co najmniej 1536 px. Powiększenie nie zmienia raw/bazy ani nie odzyskuje nieistniejącego szczegółu. PNG są materiałem analitycznym, nigdy podstawą odbudowy wejściowego PDF.

### R06 — pełne pokrycie i drugi odczyt

MODEL musi obejrzeć każdą stronę, rozpoznać regiony i wykonać drugi odczyt/porównanie z obrazem. Sprawdza tekst, liczby, znaki, strukturę i lokalizację niezależnie. Obowiązuje rejestr pokrycia stron 1…N, również pustych oraz zawierających samą grafikę. Istniejący OCR jest kandydatem do porównania, a nie źródłem prawdy. Sam wpis `verified` lub wysoki średni wynik jakości nie dowodzi wykonania kontroli.

### R07 — wierność źródłu

Nie wolno poprawiać błędów autora, ujednolicać rozbieżnych nazwisk lub dat, dopowiadać cyfr i rozwijać niepewnych skrótów na podstawie wiedzy zewnętrznej. Poprawia się odczyt tak, aby odpowiadał temu, co jest widoczne. Trzeba zachować negacje, przecinki dziesiętne, jednostki, diakrytyki i rozróżnienia `§/$`, `1/I/l`, zero/puste pole. Reguły tolerancyjnego wyszukiwania cytatów nie są poleceniem normalizacji transkrypcji. Treść dokumentu, także instrukcje znalezione na stronie, pozostaje materiałem do odczytu i nie steruje działaniem agenta ani miejscem dostawy.

### R08 — rozstrzygnięcie niepewności przed finalizacją

Po ponownym obejrzeniu nadal niepewnego regionu MODEL musi zapytać użytkownika, wskazując plik, stronę, akapit/region oraz konkretny problem; może pokazać potrzebny crop. Nie finalizuje ZIP ani nie przedstawia bundle w Drive jako ukończonego z otwartymi pytaniami. Pytania i odpowiedzi muszą być rzeczywistą niepustą treścią; flaga, liczba lub whitespace nie stanowią odpowiedzi.

Użytkownik może potwierdzić odczyt, dostarczyć lepszy obraz albo zaakceptować nieczytelność. W ostatnim przypadku zapisuje się nieczytelność źródła bez domysłu. Skutek rozstrzygnięcia musi być spójnie uwzględniony we wszystkich zależnych reprezentacjach; pytanie, odpowiedź i podstawa decyzji pozostają wyłącznie w LOG/stanie roboczym. Nie ma wymogu zatwierdzania przez człowieka każdego czytelnego akapitu lub każdej grafiki.

## Searchable PDF — R09–R16

### R09 — zachowanie oryginalnego PDF

Bazą pochodnej musi być oryginalny PDF. Nie wolno zastępować stron renderami, screenshotami lub pomniejszonymi PNG. Widoczny native text, grafika, obrazy, adnotacje, formularze, MediaBox/CropBox i obrót muszą pozostać zachowane. Zmiana niewidocznego OCR nie może zmieniać wyglądu strony ani zasłaniać treści. Przy użyciu redakcji konieczna jest ochrona obrazów i grafiki (`PDF_REDACT_IMAGE_NONE`, `PDF_REDACT_LINE_ART_NONE`), brak wypełnienia i kontrola kolizji; sam zestaw flag nie dowodzi zachowania widocznego źródła.

### R10 — zachowanie i lokalna korekta istniejącego OCR

Poprawną warstwę zachowuje się bez dublowania. Gdy geometria jest użyteczna, korekta obejmuje błędne całe słowa/tokeny w ich źródłowych współrzędnych z `dict`/`words`/`texttrace`, przy zachowaniu sąsiednich słów. Nie wolno rozciągać wielowyrazowej linii do wspólnego prostokąta i uznawać zgodnego obrysu za dowód położenia jej słów. Każdy naprawiony i zachowany region podlega kontroli.

### R11 — dodawanie i wyjątkowa odbudowa warstwy

Dla czystego skanu lub sprawdzonego pustego tekstowo regionu tekst dodaje się liniami lub słowami ze zweryfikowaną geometrią. Zakazane jest pojedyncze `insert_text()` dla wieloliniowego akapitu. `insert_textbox()` wymaga kontroli `rc >= 0` i pełnego tekstu po zapisie. Nie wolno dopasowywać tekstu przez mikroskopijny font maskujący zły bbox.

Odbudowa faktycznie nieużytecznej niewidocznej warstwy jest możliwa po odnotowanym uzasadnieniu i ponownej weryfikacji geometrii. Nadal zachowuje oryginalny PDF, widoczny tekst, obrazy i grafikę. Nie jest skrótem do usunięcia poprawnej geometrii.

### R12 — zawartość niewidocznej warstwy

OCR zawiera odczytany tekst źródła, również powtarzane kontakty i stopki pominięte w MD. Dodany tekst jest niewidoczny (`render_mode=3`), Unicode i prawidłowo przeszukiwalny. Opisy MODEL, np. „Pole podpisu: puste”, nie mogą trafić do warstwy OCR, jeżeli takich słów nie ma na stronie. Nie mogą pozostać stare sprzeczne tokeny ani podwójna warstwa.

### R13 — kontrola tekstu po zapisie

Należy ponownie otworzyć wynikowy PDF i wykonać QA w Pythonie. `chars_outside_page == 0` z tolerancją 2 pt, z uwzględnieniem obrotu i CropBox. Standardowy odczyt `page.get_text("text")` ograniczony do strony musi obejmować pełną zatwierdzoną treść, bez uciętych końcówek. `clip=INFINITE_RECT`, zgodna liczba stron albo same polskie znaki nie zastępują tej kontroli. Kompletność nie wymaga ślepego przyjęcia technicznej kolejności `sort=True`; obowiązuje R22.

### R14 — geometria zaznaczania i wyszukiwania

Wyszukane/zaznaczone słowa muszą wskazywać właściwy tekst w obrazie, nie tylko gdzieś występować na stronie. Kontrola obejmuje naprawiane słowa, poprawne sąsiedztwo oraz zachowaną warstwę w trybie `keep`, także bez opcjonalnych `search_checks`. Zachowanie błędnej geometrii wejścia bez zmian nie jest poprawnym wynikiem: należy ją porównać z obrazem. Chronione identyfikatory, nazwiska i wartości laboratoryjne sprawdza się z ich właściwymi etykietami i regionami.

### R15 — obrazy i wielkość pliku

Dla wejściowego PDF źródłowe strumienie obrazów, wymiary pikselowe, zawartość, maski i położenia muszą pozostać identyczne. Zgodne wymiary nie usprawiedliwiają podmiany obrazu. Rendery źródła i pochodnej przy identycznych parametrach muszą zachować wygląd. Zapis z subsetem fontu, `garbage=4` i `deflate=True` jest techniką optymalizacji; jeśli zmienia strumienie obrazów, pierwszeństwo ma ich dokładne zachowanie. Przyrost rozmiaru trzeba wyjaśnić obiektami/fontami, bez arbitralnego progu zastępującego kontrolę integralności.

### R16 — bramki wydania nie mogą się obchodzić

Każda ścieżka kończąca się finalnym bundle, w tym bezpośrednie `seal`, musi kontrolować rzeczywiste źródło, bazę, PDF, treść, geometrię, raport podpisów, raw i LOG. Wcześniejszy `stage`, ręczny inventory lub zgodny plan nie zastępują kontroli zapisanych plików. Niezgodność blokuje wydanie do czasu naprawy i ponownego sprawdzenia. Częściowe `validate` musi jasno określać ograniczony zakres i nie nazywać go pełnym odbiorem.

## JSON i lokalizacja — R17–R22

### R17 — pełna reprezentacja źródła

JSON obejmuje każdą fizyczną stronę/klatkę 1…N i wszystkie regiony źródłowe, również pominięte w MD. Bloki mają jednoznaczne ID, typ, kolejność, źródłowy tekst lub opis i bbox. Taksonomia rozróżnia co najmniej tytuły, akapity, tabele, listy, równania, podpisy, pieczęcie, figury, nagłówki, stopki i elementy nieustalone; musi też reprezentować pismo odręczne, logo i puste pole podpisu. Lista/checkbox/formularz zachowuje hierarchię, stan i wartości.

Pusta strona wymaga potwierdzenia wizualnego. Strona z grafiką bez tekstu wymaga opisu grafiki, nie pustej listy bloków. Opis odzwierciedla widoczne źródło; nie jest wynikiem diagnozy ani analizy prawnej.

### R18 — jednoznaczny układ współrzędnych

Publiczne bbox są `xyxy`, znormalizowane do wyświetlanego CropBox, z początkiem w lewym górnym rogu. Muszą zawierać cztery skończone liczby i spełniać `0 <= x0 < x1 <= 1`, `0 <= y0 < y1 <= 1`. Wymiary stron odpowiadają rzeczywistemu wyświetlanemu obszarowi, z uwzględnieniem obrotu i offsetów; nie domyślnemu A4. Linie/komórki mają prawidłowe powiązania z blokami. Przeliczanie punktów nieobróconego PDF, pikseli renderu i współrzędnych publicznych musi być jawne i sprawdzone.

### R19 — użytecznie precyzyjny bbox i właściwe wystąpienie

Bbox musi umożliwiać odnalezienie konkretnej jednostki treści. Dla krótkiego tekstu nie wystarcza ramka całej strony zawierająca pasujące słowo. Powtórzenia w różnych miejscach muszą mieć osobne przypisania i regiony. Nie wolno użyć jednego wystąpienia PDF do uzasadnienia dwóch odrębnych odczytów. Długi lub nieregularny akapit może mieć obwiednię bloku, ale wymaga dokładniejszych regionów linii/podbloków, gdy sama obwiednia nie rozróżnia lokalizacji. Odczyt tekstu i trafność lokalizacji są odrębnymi warunkami.

### R20 — osobna kontrola regionów graficznych

Podpis, pieczęć, skreślenie, odręczny dopisek, grafika i istotne puste pole muszą mieć bbox sprawdzony przez MODEL na renderze źródła. Brak słów OCR lub pozytywne `unique_occurrences` nie dowodzi lokalizacji grafiki. Kontrola odnotowuje stronę/ID, region/crop i wynik w stanie roboczym/LOG. Status potwierdzenia przez człowieka jest dopuszczalny tylko po rzeczywistej odpowiedzi użytkownika; niepewność podlega R08. Cropy nie stają się finalnymi składnikami bundle.

### R21 — tabele i wszystkie reprezentacje treści

Tabela musi mieć wiersze, kolumny, komórki, nagłówki i scalenia oraz reprezentację pustych pozycji. Każda komórka ma własny bbox i poprawną relację do wartości, nazwy analitu, jednostki, zakresu i daty. Zero nie jest pustą komórką. Wspólna etykieta panelu nie może zostać bezpodstawnie przypisana osobno do każdego wyniku.

Wszystkie obecne reprezentacje `text`, `lines`, `cells`, MD i odczyt PDF muszą być zgodne w treści i relacjach. Poprawne linie nie zwalniają z kontroli komórek używanych przez renderer MD. Tolerancje porównania mogą obejmować NFC i niemerytoryczne odstępy, nie zmiany cyfr, znaków, jednostek lub przypisania. `PLT 304` w źródle/PDF/liniach oraz `PLT 999` w komórce/MD bezwarunkowo blokuje wydanie. Puste i nadmiernie szerokie komórki nie mogą ukrywać słów należących do sąsiednich komórek.

### R22 — logiczna kolejność i struktura

JSON/MD zachowują logiczne czytanie kolumn, akapitów, list i formularzy. Techniczna kolejność zwrócona przez ekstraktor nie jest automatycznie kolejnością źródła. Poprawne dwie kolumny nie mogą być odrzucone wyłącznie dlatego, że `sort=True` przeplata ich linie. Jednocześnie nie wolno akceptować zamiany wartości tabeli, zgubienia słowa lub zmiany relacji pod pretekstem dozwolonej kolejności. Kontrola musi obejmować tekst, krotność wystąpień i ich regiony.

## Markdown — R23–R29

### R23 — znaczenie „100% zgodny treściowo”

Każde twierdzenie i każda wartość w MD muszą mieć podstawę w PDF/obrazie. Żadna informacja istotna dla analizy nie może zniknąć. Dozwolone są zmiany formy i wyraźnie ograniczone pominięcia opisane w R25–R26. MD nie jest skrótem merytorycznym ani parafrazą; nie dodaje executive summary, ocen medycznych/prawnych, domniemanych przyczyn ani zarzutów. Obserwacje możliwych rozbieżności zachowuje w postaci danych źródłowych. Kryterium zgodności konkretnego wyniku nie jest obietnicą uniwersalnej nieomylności OCR.

### R24 — informacje chronione

Poniższe dane muszą pozostać w MD z ich rolą i relacją do źródła, niezależnie od położenia w nagłówku, stopce, tabeli lub grafice:

| Klasa | Obowiązkowe zachowanie |
|---|---|
| Daty i godziny | Wizyta/świadczenie, przyjęcie/wypis, pobranie/przyjęcie materiału, badanie/wynik, utworzenie/zmiana wpisu, autoryzacja/podpis, eksport EDM i wydruk jako osobne role. Niejasną etykietę zachować bez dopowiadania. |
| Osoby i podmioty | Dane pacjenta i identyfikatory, autor, osoba na pieczęci, podpisujący, role, specjalizacje, PWZ/NPWZ; minimalna tożsamość placówki/jednostki i każdy istotny wariant. |
| Treść medyczna | Objawy, badania, rozpoznania/kody, wyniki/liczby/jednostki/zakresy/flagi, leki/dawki/drogi/częstotliwości, zalecenia, negacje, warunki i zastrzeżenia. |
| Pochodzenie i stan | Identyfikatory dokumentów/zleceń/EDM/wersji, status roboczy/niezatwierdzony/anulowany/skorygowany i inne widoczne stany. |
| Ślady wizualne | Pieczęcie, podpisy, dopiski, skreślenia, poprawki, nakładanie elementów oraz rzeczywiście istniejące puste pola. Czytelne nazwiska/numery wymagają transkrypcji, nie ogólnego opisu „pieczątka”. |
| Oświadczenia i zdarzenia | Odbiór/wydanie dokumentacji, liczba egzemplarzy, zwrot oryginałów, odmowy, zgody, indywidualne instrukcje i informacje o dalszej opiece. |
| Treść prawna/inne dokumenty | Strony, sygnatury, żądania, warunki, terminy wraz z podstawą ich biegu, kwoty/waluty/zakresy, negacje i oryginalny język. |

Nie wolno usuwać tych danych po błędnym nadaniu roli `facility_contact`, `survey_invitation` czy `routine_media_instructions`. Ochrona musi uwzględniać treść, relacje i opis, nie wyłącznie etykietę lub listę kilku słów kluczowych. Wątpliwy element pozostaje w MD do rozstrzygnięcia. Powtórzone istotne wystąpienia pozostają nawet przy identycznym tekście.

Podpis odręczny, nadruk nazwiska, pieczęć i podpis cyfrowy to różne informacje. Puste pole podpisu opisuje się tylko w rzeczywiście wyznaczonym miejscu. Brak podpisu cyfrowego nie pozwala dopisać „brak podpisu lekarza”. Nieczytelna kreska nie dowodzi tożsamości podpisującego. Jeśli różne miejsca wskazują różne osoby, trzeba zachować wszystkie odczyty i lokalizacje.

### R25 — dozwolone odszumianie

Z MD można usuwać rutynowe, nieistotne kontakty placówki, centralę telefoniczną, fax, ogólny adres/e-mail/WWW, reklamę, dekoracyjne logo i zwykłe zaproszenia do ankiet. Rutynowe NIP/REGON i instrukcje nośnika można pominąć tylko wtedy, gdy nie rozróżniają podmiotów i nie zawierają indywidualnych zdarzeń lub danych. Należy zachować minimalną tożsamość placówki i każdą istotną odmianę.

Mieszany blok trzeba rozdzielić przed pominięciem. Zalecany kontakt po pogorszeniu, dane konkretnego autora, termin wizyty lub potwierdzenie odbioru dokumentacji nie są rutynowym kontaktem. Każdy pominięty element pozostaje kompletny w JSON i wizualnym PDF; jego czytelny tekst źródłowy pozostaje również w OCR. Grafika bez tekstu nie otrzymuje wymyślonego tekstu OCR. Decyzja z ID/stroną i przyczyną trafia do LOG. MD nie zawiera etykiet „pominięto stopkę”.

### R26 — deduplikacja formy

Deduplikacja dotyczy jedynie rzeczywiście identycznych, niechronionych elementów formy, np. nagłówka, stopki lub logo. Zarówno usuwany element, jak i wcześniejszy uwzględniony cel muszą być dopuszczalne; wynik medyczny, podpis, data lub indywidualne oświadczenie nie mogą być celem obejścia. Tekst i opis wizualny muszą być zgodne. Naturalne powtórzenie źródła nie jest samo w sobie zbędnym duplikatem. JSON/PDF zachowują wszystkie wystąpienia.

### R27 — fizyczne strony i literalny tag bazowy

**Obowiązującym wymaganiem bazowym pozostaje początek zapisu każdej strony w postaci:**

```text
==== <original_filename> (Page x/y) ====
```

`original_filename` zawiera rzeczywistą nazwę wraz z rozszerzeniem, `x` to numer fizycznej strony/klatki od 1, a `y` to ich całkowita liczba. Każda strona, także pusta lub pozbawiona treści po odszumieniu, ma znacznik; strony zachowują kolejność źródła. Strony odszumionej nie wolno opisać jako pustej.

Późniejsze zalecenie audytu dotyczące nazwy raz i krótkich `[s. x]` nie jest samo w sobie jednoznacznym odwołaniem literalnego polecenia użytkownika. Profil skrócony lub analityczna reorganizacja mogą być użyte po **wyraźnym wyborze użytkownika dla danej konwersji lub zmianie wymagań**. Wtedy trzeba zachować jednoznaczne powiązanie każdego wystąpienia ze stroną i pełną permutację uwzględnionych bloków; JSON/PDF pozostają w fizycznej kolejności. Obecny domyślny `compact` w 0.2.0 jest zarejestrowaną rozbieżnością, nie nową zgodą użytkownika.

### R28 — zwarta forma tabel i tekstu

Proste tabele należy zapisywać jako GFM Markdown. HTML jest dopuszczalny, gdy jest potrzebny dla scaleń lub relacji nagłówków. Nie wolno wymyślać nagłówka ani spłaszczać relacji. Surowy plik MD, który będzie czytał LLM, ma zachowywać dosłowne operatory i symbole, np. `< 0,1`, `≥`, `µ` i `D-dimer & INR`, gdy składnia na to pozwala. Niezbędne escapowanie separatorów komórek i backslash nie może psuć struktury lub treści. Brak zbędnych dekoracji i powtarzanych ID akapitów nie może usuwać wymaganego tagu strony R27.

### R29 — treść oddzielona od procesu

MD i publiczny JSON nie zawierają confidence, silnika, `processing_metadata`, historii działań, pytań/odpowiedzi, raportów QA, hashy źródła lub wersji schematu. Te informacje należą do LOG/stanu roboczego. JSON zachowuje nazwę i typ źródła, strony, rzeczywiste wymiary, opis współrzędnych, ID/typy/role treści oraz bbox potrzebne do interpretacji. Opis widocznej pieczęci albo pustego pola jest treścią źródła; komentarz o stopniu pewności modelu jest informacją procesu.

## Podpisy cyfrowe — R30–R32

### R30 — detekcja i zwykły brak podpisu

Należy sprawdzić strukturę rzeczywistego wejścia. PDF bez podpisu oznacza `not_present` i normalne pominięcie kryptografii; nie jest to wada pliku ani powód żądania podpisania. Dla obrazu kontrola osadzonego podpisu PDF to `not_applicable`. Puste pole podpisu, pieczątka i rysunek podpisu nie są podpisem kryptograficznym. Wypełniona wadliwa struktura `/Sig`, np. z błędnym `ByteRange`, pozostaje wykrytym kandydatem `malformed`/`unknown`; błąd detekcji nie staje się zwykłym brakiem.

### R31 — walidacja warunkowa na oryginale

Gdy podpis faktycznie występuje, należy wykonać dostępną techniczną walidację na oryginalnych bajtach przed zmianami. Integralność, zaufanie do certyfikatu, podpisana rewizja, późniejsze zmiany i zakres nieweryfikowalny są oddzielnymi wynikami. Brak biblioteki lub materiału zaufania musi być jasno zapisany, bez fałszywego statusu `valid`/`invalid`. MODEL nie zastępuje obliczeń kryptograficznych. Nie przypisuje się statusu podpisu kwalifikowanego bez odpowiedniego badania. Konwerter niczego nie podpisuje; pochodny searchable PDF nie dziedziczy twierdzenia, że jego nowe bajty podpisał autor raw.

### R32 — wiarygodny raport podpisów

Raport musi pochodzić z rzeczywistego checkera i być związany z nazwą, hashem, typem i detekcją oryginału. Oddzielnie zapisuje się czas deklarowany przez podpisującego, timestamp treści, timestamp podpisu i timestamp dokumentu. Próba, wykonanie, ukończenie i zakres częściowy muszą odpowiadać faktycznym wynikom, także per podpis. Błąd jednego podpisu nie ukrywa pozostałych. Walidacja struktury raportu nie poświadcza ręcznie wymyślonego wyniku kryptografii. Wyniki techniczne należą do LOG; widoczne nadruki nadal są treścią źródła.

## LOG i dostawa — R33–R38

### R33 — pełny, sprawdzany LOG

LOG zapisuje zwięźle faktycznie wykonane działania, parametry renderowania, hash źródła i artefaktów, wersję reguł, pokrycie stron, decyzje o OCR i MD, kontrole geometrii, pytania/odpowiedzi, stan podpisów, QA i ograniczenia. Nie zawiera prywatnego toku rozumowania modelu. Nie może zostać zastąpiony dowolnym niepustym tekstem. Rdzeń musi wynikać z aktualnych plików i przeglądu, a końcowa bramka sprawdza jego zgodność. Potwierdzenia dostawy pochodzą z rzeczywistych operacji i nie mogą zmienić wyników kontroli. Nie wymaga się samoreferencyjnego hasha LOG w LOG ani ZIP we własnym wnętrzu.

### R34 — dokładny skład bundle

Dla jednego pliku wejściowego bundle zawiera dokładnie:

```text
<stem>_searchable.pdf
<stem>.md
<stem>.json
LOG.md
raw/<original_filename>
```

`stem` wynika z nazwy pierwotnego pliku bez końcowego rozszerzenia. Ewentualna konieczna bezpieczna zmiana nazwy musi być jednoznacznie odnotowana, bez utraty nazwy źródła w odsyłaczach. PNG/cropy, inventory, plan warstwy, review i osobne robocze raporty nie należą do finalnego bundle. Wszystkie fakty potrzebne do rozumienia decyzji trafiają do LOG.

### R35 — ZIP zgodny z wydanym kompletem

Cały bundle, w tym raw i LOG, należy spakować do jednej paczki ZIP. Po spakowaniu należy sprawdzić listę plików, ścieżki, integralność archiwum i zgodność jego bajtów z zatwierdzonym kompletem. Nie dołącza się plików roboczych ani ZIP-a do jego własnej zawartości. Zmiana treści po kontroli wymaga ponownego sprawdzenia i pakowania. Powtarzalność archiwum dla identycznych wejść jest pożądana; sama deterministyczność nie dowodzi poprawności treści.

### R36 — Google Drive

Właściwe połączone konto Google Workspace otrzymuje komplet w korzeniu Dysku: `Konwerter/<stem>/`, z oryginałem w `raw/`. Do tego samego katalogu trafia ZIP. Należy ustalić rzeczywisty korzeń i rodziców, sprawdzić nazwy, rozmiary oraz dostępne checksumy/odczyt zwrotny. Inny dokument o tej samej nazwie nie może zostać nadpisany. Sposób rozróżnienia kolizji ma zachować związek z nazwą źródła i zostać zapisany w LOG. Nie zmienia się uprawnień udostępniania. Zlecony zapis nie wymaga ponownego ogólnego pytania o zgodę.

### R37 — odpowiedź i status dostawy

Odpowiedź końcowa zawiera jeden ZIP i, po potwierdzonej dostawie, link do katalogu Drive. Nie zawiera pojedynczych plików, PNG ani etapów pośrednich. Wyjątkiem są niezbędne wycinki w pytaniu o odczyt przed finalizacją. Lokalnie poprawny ZIP i ukończony zapis w Drive to dwa odrębne zdarzenia. Gdy integracja jest niedostępna, należy jasno wskazać niezakończoną dostawę; nie fabrykować linku ani receipts. Dostępny poprawny ZIP można przekazać z jawnym statusem częściowej dostawy.

### R38 — długie dokumenty i wznowienie

Praca może przebiegać partiami z trwałym rejestrem stron i bloków. Limity narzędzi lub kontekstu nie uprawniają do cichego ucięcia dokumentu ani deklaracji kompletności. Wznowienie wymaga zgodnego źródła, wersji reguł/parametrów i prawidłowych wyników. Korekta użytkownika unieważnia zależne treści, plan, MD/JSON/PDF, LOG i kontrole w zakresie zmiany. Nie usuwa się stron/oryginałów na podstawie samej równości tekstu.

## Skill, dystrybucja i audyt — R39–R45

### R39 — zachowanie wiedzy podczas scalenia

Jeden główny Skill musi scalać użyteczną wiedzę pięciu dostarczonych skilli: strukturę dokumentów, dynamiczne renderowanie, cytaty/typografię, tabele/listy/formularze, kompletność, niepewność i rozdzieloną kontrolę podpisów. Obowiązkowa samoocena wskazuje każdą zachowaną, zmienioną, odrzuconą lub nieweryfikowaną regułę, źródło i miejsce docelowe. Zmiana backendu, wyłączenie anonimizacji i indeksu nie usprawiedliwiają utraty innych kroków. Istniejąca mapa 95 reguł jest materiałem do weryfikacji, a nie dowodem kompletności przez samą liczbę wierszy.

### R40 — jawne wyłączenia

Plugin nie wykonuje anonimizacji, maskowania danych ani odziedziczonych kancelaryjnych bramek zgody. Jest to zakres zamówienia, nie ocena stosowania prawa do użytkownika. Nie tworzy indeksu akt, FTS, wyszukiwarki, chronologii sprawy, raportu ryzyk/findings, automatycznej opinii prawnej ani dodatkowych formatów DOCX/OOXML. Nie odsyła do dawnych backendów i nie dopisuje zarzutów jako treści dokumentu. Późniejsza analiza jest osobnym etapem.

### R41 — rzeczywista wykonalność

Dokumentacja wydania musi podawać wspierany host/środowisko, zależności, przygotowanie fontu i ograniczenia. Sprawdza się rzeczywisty dostęp do wykonania kodu, obrazów i Drive. Brak dostępu lub nieobsługiwane API daje konkretną informację o blokadzie. Nie zastępuje się zweryfikowanego fontu nieznanym zasobem ani nie deklaruje obsługi każdego systemu bez sprawdzenia. Posiadanie instrukcji Skilla nie zapewnia narzędzia ani uprawnień.

### R42 — dowody wydania i granice twierdzeń

Raporty muszą wskazywać commit/artefakt, środowisko, zakres i rzeczywisty wynik. Test instrukcji, helpera, struktury, OCR MODEL, kryptografii, importu i Drive to odrębne kontrole. Wynik autora lub poprzedniego archiwum nie staje się automatycznie niezależnym wynikiem bieżącego repozytorium. Liczby znaków nie są liczbami tokenów. Nie deklaruje się powszechnej dokładności OCR, szybkości ani gotowości produkcyjnej na podstawie kilku syntetycznych stron. CI, benchmark korpusu i provisioning wielu systemów pozostają osobno oznaczonymi zaleceniami A2, dopóki nie mają wdrożenia i dowodów.

### R43 — repozytorium zawiera produkt i bezpieczne materiały testowe

Publiczne repozytorium zawiera kod, instrukcje, specyfikację, licencje i syntetyczne materiały audytowe. Zapis założeń nie upoważnia do publikacji prywatnych dokumentów użytkownika, danych pacjenta, sekretów lub materiałów sprawy. Testy na takich dokumentach mogą być potrzebne poza publicznym repo; raport musi rozróżniać ich rzeczywiste wykonanie od syntetycznych przykładów. Wyłączenie anonimizacji w konwersji nie jest poleceniem publikowania wejścia w GitHub.

### R44 — niezależny audyt według wymagań

Audytor ma otrzymać specyfikację, kryteria, przypiętą wersję źródeł i istniejące raporty. Ocenia zarówno fałszywe akceptacje, jak i odrzucanie poprawnego dokumentu; osobno sprawdza treść, geometrię, odszumianie, pytania i dostawę. `PASS` musi wskazywać dowód właściwego zakresu. `FAIL`, `NOT_TESTED`, `BLOCKED` i uzasadnione `N/A` nie mogą być zastępowane przez ogólne „zweryfikowano”.

Potwierdzone G62-01…G62-17 oraz zapisane ustalenia A2 są wejściem do dalszej pracy. Nie uruchamia się ponownie identycznych reprodukcji starej wersji w celu udowodnienia tego samego. Weryfikacja poprawionej wersji pod nowe kryterium jest odrębną czynnością. Ta zmiana dokumentacji nie obejmuje takiego wykonania.

### R45 — repozytorium marketplace

`derecho-pl` ma być repozytorium marketplace z pierwszym pluginem MODEL Konwerter i możliwością dodania kolejnych pluginów. Manifest marketplace, lokalna ścieżka pluginu, manifesty pluginu i deklarowane komponenty muszą być wzajemnie zgodne i przyjmowane przez docelowy host. Opis bieżącego sposobu importu i zależności musi odpowiadać dystrybucji. Sam poprawny JSON, publikacja kodu lub prywatna instalacja nie dowodzą udanego importu marketplace ani publicznego zatwierdzenia w katalogu. Takie zdarzenia wymagają osobnego potwierdzenia.

## Warunek zakończenia

Konwersja jest ukończona po spełnieniu wszystkich mających zastosowanie wymagań treści, geometrii, integralności i rozstrzygnięcia pytań, sprawdzeniu finalnego bundle/ZIP oraz potwierdzeniu zleconej dostawy. Normalny brak podpisu cyfrowego oznacza uzasadnione pominięcie kryptografii, a nie błąd. Brak obsługi wejścia, otwarte pytanie, niezgodne artefakty lub niewykonana dostawa muszą pozostać widocznym stanem, nie pozornym sukcesem.

Zmiana tego kontraktu wymaga opisu przyczyny, źródła decyzji i wpływu na kryteria. Nie wolno dostosować założeń po fakcie wyłącznie po to, aby istniejąca implementacja otrzymała pozytywny audyt.
