# Zasób Unicode

W repozytorium nie przechowujemy pliku fontu. Użyj `python scripts/prepare_font.py` z katalogu Skilla. Zwrócona ścieżka wskazuje zweryfikowany font o SHA-256 `57f73e11f51999432bf7ab22ce55b6f945d5eca1bf824404cfa9ec2e3718c84e`, dokładnie taki jak w testach 0.2.0. W Debian/Ubuntu można użyć pakietu `fonts-dejavu-core`; gdy lokalna wersja nie odpowiada hashowi, helper przerwie działanie. `--install` przygotowuje katalog lokalnego wydania do testów i pakowania; nie jest konieczne dla `build --font`. Nota licencyjna: [DejaVu.txt](../../../licenses/DejaVu.txt).
