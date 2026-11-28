# FORMAT-PISMA - standard wyglądu pisma (DOCX do wydruku)

Kopia standardu pluginu, trzymana w skillu. Obowiązuje zawiadomienie, uzupełnienie i wniosek towarzyszący
składane do podpisu. Ma pierwszeństwo przed każdą inną regułą czcionki i nagłówka (np. „Times New Roman 12 pt”,
„tytuł pogrubiony”). Nie dotyczy notatek i analiz wewnętrznych.

Publikację i historię wersji prowadź według `references/artefakty-i-wersje.md`: wersje Markdown zostają
w `drafty/<pismo>/`, jedyny DOCX pisma jest w `legal/output/`.

## Narzędzie

Pismo powstaje z pliku źródłowego `.md` przez renderer, nie przez ręczny HTML, pandoc ani ad hoc DOCX.
Źródło `.md` (każda wersja `_vN`) leży w `<sprawa>/drafty/<pismo>/`, DOCX w `legal/output/`; obok DOCX nie ma
sidecara `.md`. Renderer wołaj przez `scripts/wersja_pisma.py` (renderer: `scripts/render_pismo.py`), który pilnuje tego podziału:

```bash
python3 -I scripts/wersja_pisma.py nowe --md <sprawa>/drafty/<pismo>/rrrrMMdd_hhmm_<nazwa>_v1.md --output legal/output
```

PDF nie powstaje: użytkownik redaguje DOCX w Wordzie, drukuje i podpisuje. Składnię metryki i treści opisuje
docstring `render_pismo.py`.

- Plik pisma w `output/` ma nazwę bez daty i `_vN` (`<nazwa>.docx`) i jest jeden przez całe życie pisma.
  Kolejna wersja nie jest nowym renderem ani nowym plikiem: to zmiany śledzone w tym samym DOCX
  (`wersja_pisma.py start` i `redline`, cykl w `references/artefakty-i-wersje.md`). Ręczne zmiany autora trafiają do
  snapshotu `rrrrMMdd_hhmm_<nazwa>_vN.md`, który `start` zapisuje w `drafty/`.
- `render_pismo.py --nadpisz` i ręczny render do `output/` są zakazane dla pisma, które ma już DOCX.
- Celuj w jedną stronę przy piśmie odpowiadającym na wezwanie lub pytanie sądu: tylko odpowiedź,
  krótka podstawa i wniosek.

## Krój i rozmiar

- Georgia 10 pt w całym piśmie. Gdy Georgii nie ma w systemie, może zostać krój zbliżony (szeryfowy,
  np. Gelasio, Charter) - DOCX wskazuje Georgię, a Word użytkownika ją wyświetli i wydrukuje.
- 14 pt mają tylko: imię i nazwisko (nazwa) nadawcy oraz nazwa organu adresata.
- 12 pt: wydział, oddział lub inna podjednostka organu (`adresat_jednostka`), np. „III Wydział Karny”.
- Tytuł pisma: wersaliki rozstrzelone, 12 pt, wyśrodkowany, bez pogrubienia; podtytuł 10 pt.
- Cytat blokowy 9,5 pt, wcięty z obu stron. Stopka: tylko numer strony z prawej.
- Tekst wyjustowany, interlinia ok. 1,25, odstęp 6 pt po akapicie. A4, lewy margines 3 cm (miejsce na wszycie do akt), pozostałe 2 cm; przy redline
  istniejącego pisma lewy margines poniżej 3 cm podnieś do 3 cm.

## Nagłówek

```
                                                Kraków, dnia 15 października 2026 r.
Jan Kowalski                                   ← 14 pt
ul. Przykładowa 1/2, 30-001 Kraków                     ← ulica/osiedle, kod, miasto: JEDNA linia
tel. 600 000 000, e-mail: …                          ← jedna linia

                                      Sąd Okręgowy w Krakowie   ← organ 14 pt, wyrównanie do prawej
                                            III Wydział Karny   ← podjednostka 12 pt, do prawej
                             ul. Przy Rondzie 7, 31-547 Kraków   ← 10 pt, jedna linia, do prawej

Sygn. akt:        III Ko 1/26                       ← etykieta i wartość w kolumnach
Wnioskodawca:     Jan Kowalski
```

- Telefon i e-mail nadawcy: wpisz, jeśli znasz je z dokumentów sprawy (wcześniejsze pisma, profil).
  Jeśli nie znasz - zapytaj użytkownika przed wygenerowaniem pisma. Nie zgaduj i nie wstawiaj
  pustych pól. Oświadczenie o nieposiadaniu telefonu lub e-maila wpisuj tylko na polecenie użytkownika.
- Blok adresata w całości wyrównany do prawej (Align Right), bez wcięcia.
- Adres organu sprawdź w dokumentach sprawy albo wyszukiwaniem, nie z pamięci.
- Podpis: imię i nazwisko autora pod miejscem na podpis; bez tytułu zawodowego i numeru wpisu.

## Wyróżnienia: pogrubienie i podkreślenie

- Pogrubienie i podkreślenie służą wyłącznie do wskazania sędziemu fragmentu, na którym opiera się
  pismo: przede wszystkim uchybienia organu (brak protokołu, brak pouczenia, sprzeczność w dokumentacji),
  kluczowego zarzutu albo rozstrzygającego słowa w cytacie. Nie wyróżniaj własnej odpowiedzi na pytanie
  sądu ani własnej oceny. W krótkim piśmie strony wystarcza jedno wyróżnienie albo żadne. Podkreślenie
  jest równorzędne z pogrubieniem (praktyka pism procesowych); w cytacie podkreślaj pojedyncze słowa.
- Nie pogrubiaj elementów formalnych: nagłówka, nazwisk, nazwy sądu w nagłówku, tytułu, śródtytułów,
  etykiet („Sygn. akt”), numerów punktów, dat, kwot w petitum (chyba że kwota jest sporna).
- Nie zastępuj struktury pogrubieniem: zamiast pogrubionego śródtytułu użyj numerowanego punktu
  („1. Co do zażalenia na zatrzymanie: …”) albo nagłówka `#`/`##` renderera (wersaliki, bez pogrubienia).
- Limit orientacyjny: 1 wyróżnienie na ok. 250 słów, nie więcej niż 1 w akapicie. Renderer ostrzega
  po przekroczeniu - wtedy zostaw tylko te, bez których sędzia mógłby przeoczyć tezę.

## Treść

- Układ punktowy jak we wzorze: punkty `1.`, `2.`, podpunkty `a)`, `b)`. Numer od tekstu oddziela **jedna
  spacja** - bez tabulatora i bez wcięcia wiszącego (szeroka przerwa między numerem a treścią to błąd, który
  autor musi poprawiać ręcznie). Punkt ma wcięcie lewe 0,25 cm, podpunkt 0,5 cm.
- Między punktami nie ma pustych akapitów ani łamań wiersza; odstęp daje odstęp po akapicie (6 pt).
- Każdy tekst dopisany do istniejącego DOCX ma krój i rozmiar otoczenia (Georgia 10 pt); wstawka bez własnego
  formatowania (np. na początku akapitu) spada do domyślnej czcionki Worda (Aptos 12 pt) - to błąd.
- Na końcu: wniosek końcowy, podpis z prawej (linia kropkowana, imię i nazwisko), pod nim „Załączniki:”
  z numerowaną listą, jeśli są.
- Bez emoji, symboli i znaczników Markdown w gotowym piśmie.

## Kontrola przed wydaniem

1. Treść przeszła lokalną kontrolę języka z `references/styl.md` (bez wzorców AI i formuł procesowych).
2. Renderer przeszedł bez błędu; ostrzeżenie o wyróżnieniach rozpatrzone.
3. Telefon i e-mail nadawcy podane albo potwierdzone przez autora jako nieznane.
4. W `drafty/<pismo>/` są tylko wersje `.md`, w `legal/output/` jeden `.docx` pisma; nie ma PDF
   (`wersja_pisma.py sprawdz --output legal/output` = `PASS`).
5. Podpis nie zostaje sam na stronie.
