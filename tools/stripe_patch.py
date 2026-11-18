#!/usr/bin/env python3
"""Podpina prawdziwe płatności Stripe pod koszyk w zbudowanej stronie.

    python3 tools/stripe_patch.py .

1. Zapisuje api/products.json (nazwy, ceny, statusy, dostawa) z danych strony.
   Uruchamiaj po KAŻDEJ zmianie produktów, bo serwer liczy ceny tylko z tego pliku.
2. Podmienia w koszyku ekran demo na przejście do Stripe Checkout (/api/checkout.php)
   i ekran „Dziękujemy” po powrocie ze Stripe. Patchowany plik JS dostaje nową nazwę,
   bo _next/static jest cache'owany na rok (immutable).
"""
import glob
import json
import os
import re
import sys

root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')
chunks = os.path.join(root, '_next', 'static', 'chunks')


def js_string(src, start):
    """Zwraca zawartość literału JS '...' zaczynającego się na pozycji start."""
    i = start + 1
    out = []
    while src[i] != "'":
        if src[i] == '\\':
            nxt = src[i + 1]
            if nxt == 'u':
                out.append(chr(int(src[i + 2:i + 6], 16)))
                i += 6
                continue
            out.append({'n': '\n', 't': '\t', 'r': '\r'}.get(nxt, nxt))
            i += 2
            continue
        out.append(src[i])
        i += 1
    return ''.join(out)


# --- 1. katalog produktów dla serwera ------------------------------------------
data_file = next(f for f in glob.glob(os.path.join(chunks, '*.js'))
                 if '"srcImage"' in open(f, encoding='utf-8').read())
src = open(data_file, encoding='utf-8').read()
items = json.loads(js_string(src, src.index("JSON.parse('") + 11))
catalog = {}
for p in items:
    ship = p.get('ship') or {}
    catalog[p['slug']] = {
        'name': p['name'], 'sub': p.get('sub') or '', 'price': p.get('price'),
        'status': p['status'], 'sku': p.get('sku') or '',
        'image': p['images'][0]['src'] if p.get('images') else None,
        'inpost': (ship.get('inpost') or {}).get('price'),
        'inpost_label': (ship.get('inpost') or {}).get('label'),
        'courier': (ship.get('courier') or {}).get('price'),
    }
os.makedirs(os.path.join(root, 'api'), exist_ok=True)
with open(os.path.join(root, 'api', 'products.json'), 'w', encoding='utf-8') as fh:
    json.dump(catalog, fh, ensure_ascii=False, indent=1)
avail = sum(1 for p in catalog.values() if p['status'] == 'dostepny')
print(f'api/products.json: {len(catalog)} produktów, {avail} dostępnych')

# --- 2. koszyk -> Stripe ------------------------------------------------------
cart_file = next((f for f in glob.glob(os.path.join(chunks, '*.js'))
                  if 'CartView' in open(f, encoding='utf-8').read()), None)
js = open(cart_file, encoding='utf-8').read()
if '/api/checkout.php' in js:
    print('koszyk: już podpięty pod Stripe, pomijam')
    sys.exit(0)

PAY = ('onClick:async a=>{if("van"===O?.id){location.href="mailto:hello@sloy.pl?subject="+encodeURIComponent("Wycena dowozu")'
       '+"&body="+encodeURIComponent("Dzień dobry,\\nproszę o wycenę dowozu:\\n"+$.map(e=>"- "+e.name).join("\\n")+"\\nKod pocztowy: "+e.zip);return}'
       'let r=a.currentTarget;r.disabled=!0;try{let n=document.querySelector(\'.summary input[inputmode="numeric"]\'),'
       'l=await fetch("/api/checkout.php",{method:"POST",headers:{"Content-Type":"application/json"},'
       'body:JSON.stringify({cart:$.map(e=>e.slug),ship:N,country:e.country,zip:e.zip,nip:w&&n?n.value:""})}),'
       'o=await l.json().catch(()=>({}));if(l.ok&&o.url){location.href=o.url;return}'
       'alert(o.error||"Nie udało się otworzyć płatności. Spróbuj ponownie lub napisz na hello@sloy.pl.")}'
       'catch{alert("Brak połączenia z serwerem płatności. Spróbuj ponownie za chwilę.")}r.disabled=!1}')

REPLACEMENTS = [
    ('onClick:()=>z("pay")', PAY),
    ('children:["Zapłać ",E(L)]', 'children:"van"===O?.id?["Zapytaj o dowóz"]:["Zapłać ",E(L)]'),
    ('get("zadatek")&&b(!1)',
     'get("zadatek")&&b(!1);"ok"===new URLSearchParams(location.search).get("zamowienie")'
     '&&((0,d.P)({cart:[],heldAt:null}),z("done"),history.replaceState(null,"","/koszyk/"))'),
    ('"Dziękujemy (wersja demo)"', '"Dziękujemy za zamówienie"'),
    ('children:[S,": żadna płatność nie została pobrana ani nie wyszedł żaden e-mail. Zobacz w panelu, co by się stało: zamówienie, status przedmiotu i dziennik zdarzeń."]',
     'children:["Płatność przyjęta. Potwierdzenie i dowód zakupu wyślemy e-mailem. Gdy paczka wyruszy, dostaniesz numer do śledzenia."]'),
    ('href:"/panel/#zamowienia"', 'href:"/kontakt/"'),
    ('"Otwórz w panelu"', '"Pytania? Kontakt"'),
]
for old, new in REPLACEMENTS:
    n = js.count(old)
    if n != 1:
        sys.exit(f'BŁĄD: fragment występuje {n}x zamiast 1x: {old[:60]}')
    js = js.replace(old, new)

old_name = os.path.basename(cart_file)
new_name = old_name[:-3] + '-stripe.js'
with open(os.path.join(chunks, new_name), 'w', encoding='utf-8') as fh:
    fh.write(js)
os.remove(cart_file)
n = 0
for dp, dn, fn in os.walk(root):
    dn[:] = [d for d in dn if d not in ('.git', '_next', 'tools', 'api')]
    for f in fn:
        if f.endswith(('.html', '.txt')):
            p = os.path.join(dp, f)
            s = open(p, encoding='utf-8').read()
            if old_name in s:
                with open(p, 'w', encoding='utf-8') as fh:
                    fh.write(s.replace(old_name, new_name))
                n += 1
print(f'koszyk: {old_name} -> {new_name}, zaktualizowane odwołania w {n} plikach')
