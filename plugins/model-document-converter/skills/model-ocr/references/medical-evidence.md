# Dokumentacja medyczna: treść do analizy i ślady źródłowe

Celem jest wierna konwersja dokumentu do analizy przez LLM, bez oceny medycznej, prawnej ani przypisywania intencji autorom. MODEL ma zachować to, co dokument pokazuje, wraz z umiejscowieniem na stronie. Nie dopisuje rozpoznania, przyczyny zdarzenia, zarzutu, fałszerstwa ani przestępstwa.

## Co bezwzględnie pozostaje

| Rodzaj informacji | Reguła |
|---|---|
| Placówka i jednostka | Zachowaj minimalną tożsamość placówki i oddział/poradnię/laboratorium. Zachowaj odmienną nazwę, jednostkę lub identyfikator, jeśli pojawia się w innej części dokumentu; nie ujednolicaj wariantów. |
| Pacjent | Zachowaj imię, nazwisko, PESEL i inne widoczne identyfikatory, datę urodzenia, płeć oraz dane powiązania wyniku ze zdarzeniem. Nie anonimizuj i nie odtwarzaj brakujących cyfr z innych dokumentów. |
| Autor, podpisujący, pieczęć | Zachowaj każde czytelne imię/nazwisko, rolę, specjalizację, PWZ/NPWZ i inne numery identyfikacyjne. Autor wpisu, osoba na pieczęci i podpisujący mogą być różni; nie scalaj ich do jednej osoby. |
| Czas | Zachowaj osobno wszystkie widoczne daty/godziny: świadczenia lub wizyty, przyjęcia/wypisu, pobrania/przyjęcia materiału, badania, wyniku, utworzenia wpisu, autoryzacji/podpisu, eksportu EDM i wydruku. Nie zastępuj wcześniejszych najpóźniejszą datą. |
| Badania laboratoryjne | Zachowaj nazwę analitu, wartość, znak nierówności, jednostkę, zakres referencyjny, flagę H/L lub inną, próbkę/materiał, metodę i datę, jeżeli są widoczne. Przynależność wartości do właściwego wiersza i kolumny ma pierwszeństwo przed skracaniem. |
| Opis kliniczny | Zachowaj dolegliwości, badanie, rozpoznania, kody, zalecenia, dawki, drogi podania, częstotliwość, negacje, przeciwwskazania i warunki zaleceń dokładnie jak w źródle. Nie rozwijaj niepewnych skrótów. |
| Korekty i dopiski | Transkrybuj czytelne dopiski odręczne, daty i podpisane poprawki; zachowaj informację o skreśleniu/uzupełnieniu i jego miejscu. Nie wybieraj jednej wersji jako „właściwej” bez odzwierciedlenia obu. |
| Identyfikatory dokumentu | Zachowaj numer zlecenia, badania, historii choroby, wersji, identyfikatory EDM oraz czytelne informacje o wydruku/eksporcie istotne dla pochodzenia. |
| Status dokumentu | Zachowaj oznaczenia „niezatwierdzony”, „roboczy”, „anulowany”, „skorygowany” i inne rzeczywiste stany. Rola `document_status` jest chroniona także wtedy, gdy tekst jest znakiem wodnym lub częścią opisu grafiki. |

Daty i identyfikatory są tokenami wymagającymi szczególnej kontroli obrazu. Jeśli etykieta daty jest niejasna, zachowaj widoczną etykietę i umiejscowienie, zamiast nadawać jej domniemaną funkcję. Wspólna godzina w nagłówku panelu badań może dotyczyć grupy wyników; zachowaj tę relację, nie rozpisuj jej jako potwierdzonej osobno dla każdego wyniku bez podstawy.

## Mocne odszumienie MD, pełny zapis OCR i JSON

Z MD usuwaj standardowe, powtarzane elementy instytucjonalne, które nie niosą treści klinicznej ani istotnej informacji o pochodzeniu. Dotyczy to w szczególności ogólnego adresu i centrali telefonicznej, faxu, strony WWW, ogólnego e-maila, godzin rejestracji, sloganów, standardowych bannerów, dekoracyjnych logotypów oraz zaproszeń do ankiet satysfakcji. Pełna widoczna treść pozostaje w warstwie OCR i blokach JSON.

Zwykłe zaproszenie do ankiety może zawierać słowo „pacjent” i nadal być boilerplate. Samo to słowo nie jest identyfikatorem pacjenta. Odróżnij je od konkretnej osoby, etykiety danych pacjenta, indywidualnego oświadczenia lub informacji klinicznej.

Rutynowe powtórzone NIP/REGON i administracyjne dane instytucji można oznaczyć `facility_administration` i pominąć w MD, o ile nie są jedynym rozróżnieniem podmiotów, wariantem tożsamości lub istotną rozbieżnością. Zachowaj minimalną identyfikację placówki, jednostkę i każdy znaczący wariant. Rutynowe instrukcje technicznego odczytu płyty/nośnika można oznaczyć `routine_media_instructions`; zachowaj jednak konkretne nazwy badań, identyfikatory materiału, daty, listę faktycznie wydanych danych i instrukcje dalszej opieki. Indywidualne informacje mieszane z tymi instrukcjami wymagają wydzielenia.

Nie stosuj tej reguły do danych pacjenta, kontaktu konkretnego autora, zaleconego kontaktu w razie pogorszenia, terminu wizyty, instrukcji dalszej opieki, indywidualnego oświadczenia/zgody, wariantu jednostki, daty wydruku ani informacji o autoryzacji. Treść może być ważna mimo położenia w stopce.

Procedura dla każdego usuwanego elementu:

1. Ustal, czy element jest rzeczywiście standardowym boilerplate, a nie informacją specyficzną dla tego dokumentu lub wizyty.
2. Jeśli blok miesza boilerplate z datą, identyfikatorem, autorem lub treścią kliniczną, rozdziel części i zachowaj ważne fragmenty.
3. Pozostaw pełną transkrypcję i lokalizację w JSON oraz widoczne słowa w OCR.
4. Zapisz dyspozycję usuniętej części w LOG z numerem strony i identyfikatorem/regionem. Log jest miejscem dla opisu decyzji; MD nie wymaga komentarza „usunięto boilerplate”.
5. Sprawdź, że strona nadal ma odniesienie `[s. x]` w domyślnym MD i że żadne istotne wystąpienie informacji nie zniknęło. Publiczny JSON zachowuje wszystkie jej bloki, niezależnie od reorganizacji MD.

Nie usuwaj wszystkich powtórzeń nazwy placówki, jeżeli nazwy lub jednostki się różnią. Nie wycinaj logo z pełną nazwą będącą jedyną identyfikacją laboratorium. Jeżeli czysto dekoracyjne logo zostaje pominięte w MD, jego opis i bbox nadal należą do pełnej reprezentacji JSON.

Przy deduplikacji zarówno pomijany element, jak i wcześniejszy uwzględniony cel muszą być niechronionymi elementami formy `header/footer/logo`. Nie można wskazać wyniku medycznego lub podpisu jako celu identycznej stopki. Ochrona sprawdza też opis wizualny: znak wodny „DOKUMENT NIEZATWIERDZONY” nie staje się dekoracją przez nadanie typu `logo`. MODEL nadaje mu `document_status` i zachowuje opis/tekst.

## Podpisy, pieczęcie i pola puste

Podpis odręczny, nadruk nazwiska, pieczęć i rzeczywisty podpis cyfrowy PDF to różne rzeczy. Render ani screenshot nie dowodzi obecności lub poprawności kryptograficznego podpisu. Techniczne wyniki sprawdzania PDF należą do LOG; widoczny nadruk „podpisano elektronicznie” pozostaje treścią dokumentu jako nadruk.

- Opisz widoczną formę podpisu i transkrybuj czytelny tekst obok niego. Nie przypisuj tożsamości na podstawie nieczytelnej kreski.
- Podpis, pieczęć, pole podpisu i pismo odręczne wymagają niepustego `visual_description`. `include` musi wyemitować opis oraz istniejący tekst; pusty `text` bez opisu nie dokumentuje ani śladu, ani pustego pola.
- Jeżeli na stronie jest rzeczywiście wskazane miejsce na podpis, a pole jest widocznie puste, wolno opisać: `[Pole podpisu: puste]`. Powiąż opis z tym konkretnym regionem/bbox. Nie twórz takiej adnotacji tylko dlatego, że na całej stronie nie znaleziono podpisu lub PDF nie jest cyfrowo podpisany.
- Jeśli dokument nie wyznacza miejsca na podpis, sam brak rysunku podpisu nie uprawnia do dopisania „brak podpisu autora”. Nie oceniaj ważności dokumentu.
- Zachowaj czytelne dane pieczęci w jej miejscu. Jeśli nazwa lekarza w treści różni się od nazwiska na pieczęci, zapisz obie wersje, etykiety i lokalizacje. Nie „naprawiaj” rozbieżności przez zastąpienie jednej drugą.
- Zachowaj podpisy i pieczęcie przekreślone, częściowo nałożone, słabo odbite lub dodane obok wcześniejszego wpisu. Nie wnioskuj o chronologii naniesienia wyłącznie na podstawie wyglądu.

Przykłady sformułowań dotyczą obserwacji, nie pochodzą z dokumentu użytkownika: `[Pieczęć: czytelny tekst „…”]`, `[Podpis odręczny; nazwisko nieodczytane]`, `[Pole podpisu: puste]`. Każde rzeczywiste użycie wymaga odpowiedniego regionu źródłowego. Nie używaj określeń „sfałszowano”, „podpis podrobiony”, „bezprawnie” ani „przestępstwo” jako modelowej treści transkrypcji. Jeśli takie słowo dosłownie występuje w źródle, zachowaj je jako tekst autora.

## Laboratoria i mały druk

Weryfikuj wartości razem z nazwą analitu, jednostką i zakresem. Wynik `112` nie jest samodzielną informacją bez właściwego wiersza. Zachowaj przecinki dziesiętne, spacje grupujące, potęgi, symbole `µ`, `≥`, `<`, minusy oraz różnicę między zerem a pustą komórką. Nie przeliczaj jednostek i nie klasyfikuj wyniku jako prawidłowego lub nieprawidłowego, chyba że taką flagę lub ocenę podaje sam dokument.

Tabela wymaga jawnych wierszy, kolumn, komórek i ich bbox. Tekst całego bloku, ewentualne linie i komórki muszą zgadzać się niezależnie: poprawne `PLT 304` w linii nie dopuszcza `999` w komórce. Sprawdź położenie każdej komórki i konkretne wystąpienie słów; same słowa obecne gdzieś na stronie nie dowodzą właściwego przypisania. Prosty wynik laboratoryjny zapisuj jako GFM; HTML zachowuje konieczne scalenia lub nietypowe relacje nagłówków.

Wzrost DPI służy odczytaniu małego druku, nie zmianie rozdzielczości oryginalnych obrazów w PDF. Dla niepewnej cyfry pokaż użytkownikowi cały istotny wiersz z etykietą i jednostką, a nie samą cyfrę pozbawioną kontekstu. W regresjach sprawdź wyszukiwanie na właściwej stronie dla faktycznie obecnych `PLT`, `304`, `KREATYNINA`, `112`, PESEL i PWZ/NPWZ oraz zgodność ich zaznaczenia z obrazem.

## Granica wnioskowania

Dokument może zawierać sprzeczne daty, nazwiska, stemple lub opisy. Konwersja zachowuje je wszystkie i ich relacje źródłowe. Oddzielna późniejsza analiza może wskazywać findings; obecny bundle nie zamienia rozbieżności w udowodnioną przyczynę, nie dopisuje motywów personelu ani zarzutów wobec szpitala. LOG może opisać decyzję „zachowano oba warianty” bez rozstrzygania, który jest prawdziwy.
