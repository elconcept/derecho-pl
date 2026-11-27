# MODEL Konwerter — pochodzenie decyzji i stan rozbieżności

**Stan dokumentacji:** 2026-11-27.  
**Specyfikacja normatywna:** [ZALOZENIA.md](ZALOZENIA.md), wersja 1.0.  
**Kryteria:** [KRYTERIA_ODBIORU.md](KRYTERIA_ODBIORU.md).

Ten rejestr oddziela wymagania użytkownika, wybory implementacji, ustalenia audytów i wykonane kontrole. **Nie jest nowym audytem wykonawczym ani potwierdzeniem napraw.** Przy sporządzaniu dokumentów odczytano raporty i aktualne instrukcje; nie uruchamiano ponownie wcześniejszych reprodukcji.

## 1. Przypięty stan źródeł

| Element | Identyfikacja |
|---|---|
| Repozytorium | [elconcept/derecho-pl](https://github.com/elconcept/derecho-pl) |
| Odczytany HEAD przed dodaniem tej specyfikacji | [`219a1a02c4bf144de1271a1acb85390aced3ac04`](https://github.com/elconcept/derecho-pl/commit/219a1a02c4bf144de1271a1acb85390aced3ac04) |
| Wersja kodu oceniana przez audyt MODEL 0.2.0 | [`18f6fffc8bc1a82677ebe9b88dc1d60fdf7fa096`](https://github.com/elconcept/derecho-pl/commit/18f6fffc8bc1a82677ebe9b88dc1d60fdf7fa096) |
| Raport A2 | [`audyt/2026-11-27T03-25-01Z_v0.2.0/AUDYT_DERECHO_PL_0_2_0.md`](../../audyt/2026-11-27T03-25-01Z_v0.2.0/AUDYT_DERECHO_PL_0_2_0.md) |
| Blob raportu A2 w odczytanym drzewie | `92d07ec7c1e227b6f4652e027f9b343e079754e9` |
| Dawne rozliczenie G62 przez autora pluginu | [`AUDIT_REMEDIATION.md`](../../plugins/model-document-converter/docs/AUDIT_REMEDIATION.md) — opis zmian, nie zamiennik A2. |

Raport Gemini w drugim katalogu `audyt/` dotyczy innego pluginu. Nie przypisujemy jego wyników MODEL Konwerterowi. Istniejące raporty pozostają historycznymi dokumentami; kolejne wyniki powinny powstać w nowym katalogu audytu z własnym przypiętym commitem.

## 2. Wymagania i świadome interpretacje

| Decyzja | Podstawa i obowiązująca interpretacja | Konsekwencja dla audytu |
|---|---|---|
| **DEC-01 — tagi stron** | Użytkownik literalnie wymagał `==== <original_filename> (Page x/y) ====`. Później przekazał zalecenie audytora o krótkich odsyłaczach i celu oszczędności kontekstu. Nie odnaleziono jednoznacznego polecenia użytkownika odwołującego pełny tag. W 0.2.0 autor przyjął `compact` jako domyślny i opisał tę interpretację jako decyzję użytkownika. Ta deklaracja nie jest wystarczającą podstawą zmiany zamówienia. | **Otwarte odstępstwo dokumentacji/implementacji względem R27.** Bazowy odbiór wymaga pełnych tagów. `compact`/reorganizacja wymagają wyraźnego wyboru. Nie nazywać dotychczasowej implementacji dowodem zgody. |
| **DEC-02 — wierność a odszumianie** | Użytkownik wymagał zgodności treści i później wyraźnie dopuścił pomijanie rutynowych kontaktów, administracji i ankiet w MD. | Nie porównywać MD do całego tekstu PDF jako wymagania identycznego ciągu. Sprawdzać brak zmian/dopowiedzeń, kompletność chronionej treści, dozwoloność każdego pominięcia i pełny JSON/PDF: R23–R26. |
| **DEC-03 — obrazy i głębia** | Zamówienie obejmuje obrazy. 0.2.0 jawnie odrzuca część trybów/głębi, aby nie obcinać próbek do fałszywego obrazu. | To ograniczenie zakresu, nie życzenie użytkownika ani poprawna konwersja takiego pliku. Osobno ocenić uczciwą odmowę i zakres faktycznej obsługi: R03/R41. |
| **DEC-04 — optymalizacja PDF** | Użytkownik wskazał ochronę obrazów i konkretne opcje zapisu. Źródłowy niezmiennik ma pierwszeństwo, gdy flaga kompresji zmienia strumień. | Oceniać rzeczywiste strumienie, geometrię i wygląd, nie sam tekst wywołania `deflate=True`: R09/R15. |
| **DEC-05 — podpisy cyfrowe** | Weryfikacja ma następować tylko, gdy podpis występuje. Raport detekcji dla każdego wejścia nie oznacza obowiązkowej kryptografii dla unsigned PDF. | Brak podpisu to normalne pominięcie. Malformed/unknown, brak walidatora i wynik integralności/zaufania są odrębne: R30–R32. |
| **DEC-06 — weryfikacja grafiki** | A2 zaleca osobny ślad kontroli regionu graficznego. Użytkownik zlecił odczyt MODEL i pytania tylko dla rzeczywistej niepewności. | Nie wprowadzać obowiązkowego ręcznego zatwierdzania każdej grafiki. Wymagać rzeczywistej kontroli MODEL; status człowieka tylko po odpowiedzi: R08/R20. |
| **DEC-07 — anonimizacja i indeks** | Użytkownik wyłączył te funkcje oraz dawne backendy. | Wyłączenia rozliczać jako zakres produktu, bez dodatkowych twierdzeń o prawie. Pozostała użyteczna wiedza musi zostać zachowana: R02/R39/R40. |
| **DEC-08 — wymagania funkcjonalne a rozwój** | CI, provisioning wielu platform i rozległy benchmark to rekomendacje A2. | Nie przedstawiać ich retrospektywnie jako literalnych pierwotnych życzeń użytkownika. Zachować jako zalecenia i ograniczenia dowodowe; brak pomiaru nie pozwala twierdzić, że go wykonano: R41/R42. |
| **DEC-09 — jedna paczka a weryfikacja użytkownika** | Zakaz osobnych renderów w odpowiedzi końcowej nie wyklucza pokazania niezbędnego cropa podczas pytania przed finalizacją. | Sprawdzić właściwą fazę procesu. Finalnie jeden ZIP; materiały robocze nie wchodzą do bundle: R08/R34/R37. |

### Szczegóły DEC-01

Odczytane pliki 0.2.0, m.in. `SKILL.md`, `references/output-contract.md`, `references/retained-knowledge.md`, `docs/SELF_EVALUATION.md` i `docs/AUDIT_REMEDIATION.md`, twierdzą, że nowsza decyzja użytkownika zastąpiła pełne tagi. Dla niezależnego audytu nie należy traktować tych deklaracji autora jako źródła nowego wymagania. Aktualny tekst [R27](ZALOZENIA.md#r27--fizyczne-strony-i-literalny-tag-bazowy) jawnie zachowuje pierwotny wymóg. Wprowadzenie specyfikacji nie zmienia jeszcze domyślnego zachowania kodu ani nie potwierdza działania wariantu `legacy_pages` w konkretnym przebiegu.

## 3. Powiązanie 17 wcześniejszych ustaleń z kontraktem

Status poniżej jest **przytoczeniem oceny A2 dla commita 18f6fffc…**, nie wynikiem nowego wykonania. A2 definiuje „wdrożone” jako obecność zabezpieczenia i testów autora, bez deklaracji pełnego niezależnego zatwierdzenia.

| Ustalenie | Wymagania / kryteria | Ocena A2 i pozostały zakres |
|---|---|---|
| G62-01 — sprzeczne komórki MD | R01, R21 / K01, K21 | Wdrożone; wszystkie reprezentacje i relacje komórek wymagają zgodności. |
| G62-02 — obce raw i baza | R03–R04, R16 / K03–K04, K16 | Wdrożone; więź rzeczywistego źródła musi pozostać obowiązkowa w obu bramkach. |
| G62-03 — błędna lokalizacja JSON | R18–R20 / K18–K20 | **Częściowo**; pozostają DPL-01/02. |
| G62-04 — przesunięcia słów przy korekcie linii | R10–R11, R14 / K10–K11, K14 | Wdrożone; patch pojedynczych całych słów. |
| G62-05 — brak kontroli keep | R14 / K14 | Wdrożone; zachowanie geometrii jest sprawdzane, a odczyt/modelowa kontrola źródła nadal potrzebne. |
| G62-06 — zniekształcenie high-bit TIFF | R03 / K03 | Wdrożone przez odrzucenie wariantu; nie pełna obsługa obrazu wysokiej głębi. |
| G62-07 — błędny podgląd alpha | R05 / K05 | Wdrożone; podgląd renderowany z bazy. |
| G62-08 — znikający podpis/opis | R17, R20, R24 / K17, K20, K24 | **Częściowo**; opis wymagany, lecz położenie grafiki pozostaje DPL-02. |
| G62-09 — niezwiązany raport podpisów | R16, R31–R32 / K16, K31–K32 | Wdrożone; związanie źródłem nie jest ponowną kryptografią ani poświadczeniem ręcznego raportu. |
| G62-10 — malformed uznany za brak | R30 / K30 | Wdrożone; uszkodzony wypełniony kandydat odróżniony od pustego pola. |
| G62-11 — podmiana LOG | R16, R33, R36 / K16, K33, K36 | Wdrożone; deterministyczny rdzeń i oddzielne potwierdzenia dostawy. |
| G62-12 — niebezpieczna deduplikacja | R24–R26 / K24–K26 | **Częściowo**; cel deduplikacji chroniony, błędne role nadal DPL-03. |
| G62-13 — pominięty timestamp treści | R31–R32 / K31–K32 | Wdrożone; osobne rodzaje czasu. |
| G62-14 — performed po nieudanej próbie | R31–R32 / K31–K32 | Wdrożone; rozdzielenie attempted/performed/completed. |
| G62-15 — szum MD i metadane | R23–R29 / K23–K29 | **Częściowo**; pozostają DPL-03/05. Niezależnie od oceny A2 obowiązuje rozbieżność DEC-01 dotycząca literalnego formatu stron. |
| G62-16 — tabela bez struktury | R17, R21 / K17, K21 | Wdrożone; struktura i relacje obowiązkowe. |
| G62-17 — pozorna odpowiedź i brak porównania | R08, R16, R21 / K08, K16, K21 | Wdrożone; niepuste rzeczywiste Q&A i sprawdzanie wszystkich reprezentacji. |

## 4. Dalsze ustalenia audytu 0.2.0

**W tym zadaniu nie wykonano napraw runtime ani nowych prób tych ustaleń.** Nie oznaczamy ich jako zamkniętych wskutek dopisania wymagań.

| ID / priorytet A2 | Obowiązek wynikający z celu produktu | Stan i kryterium dalszej pracy |
|---|---|---|
| **DPL-01 / P1** | Precyzyjny bbox właściwego wystąpienia, nie tylko unikalne przypisanie słowa wewnątrz dowolnie wielkiej ramki. | Otwarte według A2. R19/K19: odrzucić dwie pełnostronicowe ramki dla odległych powtórzeń; przyjąć ciasne regiony i poprawny długi blok z liniami. |
| **DPL-02 / P1** | Osobna weryfikacja graficznego regionu na obrazie. | Otwarte według A2. R20/K20: zły bbox podpisu nie otrzymuje pozytywnego statusu na podstawie braku słów OCR. Wymagany faktyczny przegląd wizualny. |
| **DPL-03 / P1** | Istotna treść nie znika po błędnym przypisaniu bezpiecznej roli. | Otwarte według A2. R24–R26/K24–K26: zachować wyniki, odbiór dokumentacji, odmowy i statusy; rutynową ankietę nadal można pominąć. |
| **DPL-04 / P2** | Poprawna kolejność logiczna nie zależy bezwarunkowo od `sort=True`. | Otwarte według A2. R22/K22: prawidłowe kolumny przechodzą; zamiany wartości nie. Raport wykazał konflikt warunków, nie pełne wykonanie `qa()`. |
| **DPL-05 / P3** | Surowy GFM nie zawiera zbędnych encji utrudniających analizę. | Otwarte według A2. R28/K28: dosłowne operatory i ampersandy przy zachowaniu poprawnych separatorów. |
| **DPL-06 / P2** | Wykonalna, uczciwie opisana dystrybucja i odrębne dowody jakości. | Zestaw ograniczeń/zaleceń. R41–R42/R45: udokumentować rzeczywisty provisioning i zakres platform; CI, syntetyczny smoke i benchmark rozliczyć osobno, nie deklarować ich wykonania. |

Priorytety pochodzą z raportu A2. Ich zapis nie jest nową oceną ważności ani potwierdzeniem scenariusza na dokumentach użytkownika.

## 5. Co dotychczasowe dowody potwierdzają

Poniższy zakres pochodzi z sekcji 2 i 6 raportu A2:

- Audyt przypiął commit i porównał **11/11 hashy** kodu/schematu/testów z `docs/VALIDATION.json`. Jest to związanie raportu z plikami, nie niezależne uruchomienie wszystkich testów.
- **83/83 PASS** jest wynikiem autora zapisanym w repozytorium. Audytor nie uruchomił całej suity 0.2.0 i nie przedstawia tej liczby jako własnego wykonania.
- DPL-01/02 sprawdzono na dokładnym `content_geometry.py`, SHA-256 `919a6de43ca4902f7bf3127087a393766274899954feb1ad9a87dbc975ff18a3`, z PyMuPDF 1.26.7 i wyłącznie syntetycznymi PDF-ami.
- DPL-03 badał odizolowane warunki pomijania MD, nie całe `stage`/`seal`. DPL-04 porównywał warunki geometrii/kolejności, nie pełne wywołanie `qa()`.
- A2 nie wykonał pełnej konwersji 0.2.0 na dokumentacji pacjenta, rzeczywistej walidacji kryptograficznej, importu marketplace, dostawy Google Drive ani pomiaru jakości OCR MODEL.

W odczytanym drzewie GitHub brak było `.github/workflows`. Źródłowa dystrybucja używa `prepare_font.py` i konkretnego SHA-256 fontu zamiast dołączonego pliku TTF. Raport archiwalnego wydania z fontem nie jest sam w sobie dowodem działania dowolnego hosta tej dystrybucji. Specyfikacja nie zamienia tych ograniczeń w sukces ani w potwierdzenie nowych usterek.

## 6. Reguły utrzymania dokumentacji

1. Zmiana wymagania otrzymuje datę, źródło decyzji użytkownika lub jawnego doprecyzowania technicznego, uzasadnienie i listę zmienionych R/K. Nie przepisuje się historii audytu.
2. Każda poprawka runtime wskazuje wymaganie i kryterium, które realizuje. Stan „naprawione” wymaga dowodu dla nowego commita, właściwego zakresu i aktualnych artefaktów.
3. Przykładowy plan testów nie staje się raportem jego wykonania. Przyjęte wyniki starej wersji nie są dopisywane jako nowe.
4. Gdy instrukcja Skilla lub opis produktu przeczy zamówieniu, konflikt ma być widoczny. Dokumentacji nie dostosowuje się do kodu po to, aby zmniejszyć liczbę usterek.
5. W przyszłym audycie należy czytać łącznie specyfikację, kryteria i ten rejestr; wcześniejsze `SELF_EVALUATION` oraz `AUDIT_REMEDIATION` są materiałami autora ocenianego produktu.

## Historia dokumentacji

| Wersja | Data | Zakres |
|---|---|---|
| 1.0 | 2026-11-27 | Utrwalenie wymagań U1–U4, 45 identyfikatorów R/K, powiązania z G62 i DPL, jawne DEC-01 oraz rozdzielenie kryteriów, ograniczeń i wyników. Zmiana dokumentacyjna; bez ponownego wykonywania audytów i bez deklaracji zamknięcia ustaleń. |
