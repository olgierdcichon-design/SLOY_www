# Migracja SLOY: Shopify → nowa strona

Ten katalog zawiera skrypty, które nakładają poprawki SEO na **zbudowaną** stronę
(eksport Next.js). Design strony pozostaje bez zmian.

## Co zostało zrobione

| Zmiana | Gdzie |
|---|---|
| Przekierowania 301 ze starych adresów Shopify (produkty, kolekcje, strony, polityki, blog, `/en`, `/en-eu`, `/pl-eu`, koszyk) | `.htaccess` |
| Blokada indeksowania na czas testów (`noindex` w każdej stronie + nagłówek `X-Robots-Tag`) | wszystkie `index.html`, `.htaccess` |
| Dane strukturalne produktów: cena, PLN, dostępność, SKU, marka, polityka zwrotów | `lot/*/` |
| Strony kategorii z tekstami SEO z Shopify | `/oswietlenie/`, `/meble/`, `/dodatki/` |
| Pełny regulamin i dokumenty prawne przeniesione z Shopify | `/regulamin/`, `/polityka-prywatnosci/`, `/cookies/`, `/odstapienie-od-umowy/` |
| Baner zgody na cookies + Google Analytics 4 (`G-R2WHKJCEG4`), działa tylko na sloy.pl | `consent.js`, `sloy-extra.css` |
| Mapa strony uzupełniona o nowe strony | `sitemap.xml` |

## Dzień startu (kolejność ma znaczenie)

1. Wgrać pliki na Hostinger (do `public_html`), łącznie z `.htaccess`.
2. Sprawdzić na tymczasowym adresie Hostingera, że wszystko działa.
3. Przełączyć domenę sloy.pl na Hostinger i zamknąć sklep Shopify.
4. **Zdjąć blokadę indeksowania:** `python3 tools/go_live.py .`, a potem wgrać zmienione pliki
   (wszystkie `index.html` i `.htaccess`). Bez tego kroku Google usunie stronę z wyników!
5. Search Console: wysłać `https://sloy.pl/sitemap.xml`, sprawdzić kilka starych adresów
   narzędziem „Sprawdzanie adresu URL”, przez 2–4 tygodnie obserwować raport 404.

## Gdy strona zostanie przebudowana (`next build`)

Nowy build nadpisze te poprawki. Trzeba wtedy uruchomić na świeżym eksporcie:

```
python3 tools/postbuild.py .          # wersja testowa (noindex)
python3 tools/postbuild.py . --live   # wersja produkcyjna
```

Docelowo najlepiej przenieść te zmiany do kodu źródłowego projektu Next.js.

## Test banera cookies poza sloy.pl

W konsoli przeglądarki: `localStorage.setItem('sloy-consent-test','1')` i odświeżyć stronę.
