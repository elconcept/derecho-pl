# Dostarczenie bundle do Google Drive

## Przeznaczenie i dostęp

Docelowy katalog to **My Drive/root** użytkownika, następnie `Konwerter`,
a w nim podkatalog oparty na nazwie oryginalnego PDF lub obrazu. Nie zapisuj
w dysku współdzielonym tylko dlatego, że konto jest w Google Workspace.
Plugin deklaruje istniejącą aplikację Google Drive, bez własnego serwera,
tokenów, kluczy API ani zmiany uprawnień.

W aktualnym hoście odkryj funkcje połączonego Google Drive: list_folder_page,
create_folder, upload_file, get_file_metadata oraz opcjonalnie update_file.
Nazwy prefiksów mogą się różnić. Użyj bieżących schematów narzędzi.
Nie przenoś tokenów do Python i nie wymyślaj REST autoryzacji.

## Sekwencja

1. Sprawdź połączenie i możliwość zapisu. W przypadku faktycznego błędu
   uwierzytelnienia użyj dostępnej procedury ponownego połączenia; wykonuj
   niezależne prace lokalne. Nie twórz pustych katalogów testowych.
2. Wylistuj korzeń (`url="root"`) i wszystkie strony wyników, dopóki nie
   zostanie rozstrzygnięty właściwy katalog `Konwerter`. Nie zakładaj, że
   pierwsze 100 pozycji oznacza całą zawartość. Wykorzystaj wyszukiwanie po
   nazwie i rodzicach, jeśli dostępne. Zweryfikuj rodzica przez metadata.
3. Gdy nie istnieje, utwórz `create_folder(name="Konwerter", parent_folder="root")`.
   Zachowaj dokładny zwrócony ID. Dwa równorzędne katalogi o tej nazwie wymagają
   rozstrzygnięcia na podstawie metadanych/kontekstu, a przy realnej niejasności
   krótkiego pytania o wybór, nie zgadywania.
4. W nim utwórz podkatalog `<stem>`. Usuń tylko znaki niebezpieczne w ścieżkach;
   oryginalna nazwa pozostaje w nagłówku MD, JSON i raw. Kolizję rozstrzygaj hashem
   źródła i wersją: użyj `<stem>__<hash8>` albo kolejnej jawnej wersji. Nie
   nadpisuj innego źródła ani wcześniejszego zatwierdzenia w ciemno.
5. Utwórz `raw` w podkatalogu. Wgraj oryginał tam, a searchable PDF, MD i JSON
   do podkatalogu dokumentu. Użyj upload_file z absolutną ścieżką lokalną:

   - file_uri: rzeczywista absolutna ścieżka pliku;
   - file_name: oczekiwana nazwa z rozszerzeniem;
   - parent_folder_id: sam zweryfikowany ID docelowego folderu, nie URL/nazwa/root;
   - mime_type: application/pdf, text/markdown, application/json lub typ oryginału.

6. Po każdej zakończonej operacji sprawdź metadane: nazwa, rodzice, rozmiar,
   MIME i checksumy, gdy są dostępne. Gdy host umożliwia odczyt bajtów,
   porównaj hash w razie konkretnej wątpliwości. Nie traktuj przewidywanego URL
   ani wysłanego żądania jako potwierdzonego uploadu. Nie konwertuj MD/JSON/PDF
   na natywne Google Docs, bo zmieniłoby to format wyjściowy.
7. Zapisz potwierdzone ID/linki/czynności jako roboczy plik receipt zgodny
   z kontraktem poniżej. Uruchom `record-delivery`; **nie edytuj LOG ręcznie**.
   Wgraj aktualny LOG i sprawdź go; jego treść nie musi znać własnego ID.
   Uruchom `seal`, który ponownie sprawdza źródło/QA i nienaruszony rdzeń LOG.
   Wgraj otrzymany ZIP jako application/zip do tego samego podkatalogu
   i zweryfikuj. Wynik ostatniego uploadu ZIP podaj w końcowym potwierdzeniu;
   nie zmieniaj potem LOG ani wnętrza ZIP, by dopisać jego własny hash lub ID.
8. Odpowiedź zawiera tylko ZIP jako załącznik oraz zweryfikowany URL folderu.
   Nie udostępniaj osobno MD/JSON/PDF, raw, renderów i plików roboczych.

## Potwierdzenia dostawy i niezmienny LOG

Assembler tworzy rdzeń LOG z aktualnego review, wyników QA i hashy artefaktów.
Nie zastępuj go podsumowaniem i nie dopisuj swobodnego tekstu. Jedyna ścieżka
dopisania dostawy to:

```sh
python scripts/assemble_bundle.py record-delivery --bundle-dir output/dokument --receipt work/drive-receipt.json
```

Receipt jest pojedynczym obiektem zdarzenia. Wymagane pola to
`provider: "google_drive"`, `status`, `recorded_at` oraz dla statusu innego niż
`failed` zweryfikowane `folder_id` i `folder_url`. Dopuszczalne statusy:
`verified`, `partial`, `failed`; odnoszą się do faktycznie sprawdzonego zakresu.
Opcjonalna tablica `files` zawiera obiekty `path` (względem bundle), `file_id`
oraz znane `size_bytes`/`sha256`; `note` jest zwięzłym tekstem o wyniku operacji.
Nie dodawaj innych pól i nie zapisuj hasha, którego faktycznie nie policzono.

Przed wysłaniem LOG/ZIP potwierdzaj wyłącznie już wysłane niezmienne artefakty:
raw, searchable PDF, MD i JSON. Użyj `partial`, jeżeli dostawa całego bundle
nie jest jeszcze ukończona. Hashe/rozmiary tych plików są ponownie sprawdzane
przez `seal`. Dane o samym LOG i późniejszym ZIP weryfikuj po uploadzie bez
próby umieszczenia własnego hasha we własnej zawartości. Ostatni rezultat
dostawy należy do końcowego potwierdzenia użytkownikowi.

`record-delivery` sprawdza strukturę rekordu, ale nie kontaktuje się z Drive.
MODEL może zapisać status `verified` wyłącznie na podstawie rzeczywistych
wyników połączonej aplikacji. Jeśli błąd nastąpi po zapieczętowaniu ZIP,
zachowaj tę paczkę i zgłoś nieukończoną dostawę; nie zmieniaj jej potajemnie.

## Wznowienie i błędy

Nie powtarzaj niepewnego uploadu w ciemno: najpierw sprawdź folder/metadata
według nazwy, rozmiaru i potwierdzonego ID. Wznowienie opiera się na hashu
źródła, wersji pipeline, aktualnych hashach treści i zdanym QA wszystkich
artefaktów. Samo istnienie MD lub katalogu nie oznacza ukończenia.

Autoryzacja konwersji obejmuje opisany zapis w prywatnym Drive. Nie proś
ponownie o ogólne zezwolenie i nie wprowadzaj bramek kancelaryjnej anonimizacji.
Nie zmieniaj sharing, właściciela ani odbiorców. Jeżeli faktyczny brak dostępu
uniemożliwia zapis, zachowaj zweryfikowany ZIP, podaj go i opisz konkretnie
nieukończony krok. Nie przedstawiaj lokalnego sukcesu jako zapisu na Drive.

## Zakres weryfikacji wydania pluginu

Implementacja konwersji jest testowana na lokalnych fixture'ach. Same instrukcje
Drive i poprawne deklarowanie aplikacji nie dowodzą wysłania rzeczywistego
dokumentu. Przy każdym uruchomieniu przeprowadź opisane kontrole na faktycznie
zwróconych wynikach połączonej aplikacji.
