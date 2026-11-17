"""Python port of the CollectionBrowser server render (decade axis, mix order),
used to generate HTML for the static category pages. Ported 1:1 from
_next/static/chunks (module 89287 + CollectionBrowser); validated against
/kolekcja/ by tools/postbuild.py before use."""
import math

DECADES = [
    (1950, 'Lata 50.', '#D6ECFB', '#6FB4E6'), (1960, 'Lata 60.', '#D9F2CC', '#78C45C'),
    (1970, 'Lata 70.', '#FFE3C4', '#F59E4F'), (1980, 'Lata 80.', '#E8DCFB', '#9F78E0'),
    (1990, 'Lata 90.', '#FCD9E8', '#E97BAD'), (2000, 'Lata 2000.', '#FCF3B5', '#E8C52E'),
    (2010, 'Lata 2010.', '#C9F2EB', '#4FC4B3'), (2020, 'Lata 2020.', '#FFD6CE', '#EE7B66'),
]
NEUTRAL = ('#F1F0EB', '#C9C6BB')
WEIGHTS = [6, 6, 4, 6]


def dec(year):
    if year is None:
        return None
    return min(2020, max(1950, 10 * math.floor(year / 10)))


def tone(lot):
    if lot['year'] is None or lot['approx']:
        t = lot.get('tone')
        return 0.5 if t is None else t
    return min(1, max(0, (lot['year'] - dec(lot['year'])) / 9))


def _rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def _js_round(x):
    return math.floor(x + 0.5)


def mix_hex(a, b, r):
    A, B = _rgb(a), _rgb(b)
    return '#' + ''.join(format(_js_round(A[i] + (B[i] - A[i]) * r), '02x') for i in range(3)).upper()


def palette(year):
    d = dec(year)
    for k, _, light, dark in DECADES:
        if k == d:
            return light, dark
    return NEUTRAL


def color(lot):
    light, dark = palette(lot['year'])
    return mix_hex(light, dark, tone(lot))


def mix_order(lots):
    t = lambda l: dec(l['year']) or 0
    r = list(lots)
    a = []
    while r:
        def share(d):
            return len([x for x in r if t(x) == d]) / len(r)

        def score(x):
            acc = 0
            for o, w in enumerate(WEIGHTS):
                idx = len(a) - 1 - o
                if idx < 0:
                    continue
                l = a[idx]
                if t(l) != t(x):
                    continue
                i = abs(tone(l) - tone(x))
                acc += w * (2 - i + 2 * (1 if i < 0.2 else 0))
            return acc - 30 * share(t(x))
        best = 0
        for k, x in enumerate(r):
            if score(x) < score(r[best]):
                best = k
        a.append(r.pop(best))
    return a


def axis_html(lots):
    cols = [(k, label, (str(k)[2:] + '.') if k < 2000 else str(k)) for k, label, _, _ in DECADES]
    if any(l['year'] is None for l in lots):
        cols.append((0, 'Bez daty', 'b.d.'))
    groups = []
    for k, label, short in cols:
        items = [l for l in lots if (dec(l['year']) or 0) == k]
        items = sorted(items, key=tone)
        groups.append((k, label, short, items))
    rows = max([len(g[3]) for g in groups] + [1])
    out = [f'<div class="axis" role="group" aria-label="Filtr po dekadzie" style="--cols:{len(groups)};--rows:{rows}">']
    for k, label, short, items in groups:
        dis = '' if items else ' disabled=""'
        stack = ''.join(f'<i style="background:{color(l)}"></i>' for l in items)
        out.append(
            f'<button type="button" aria-pressed="false" aria-label="{label}, liczba przedmiotów: {len(items)}"{dis}>'
            f'<span class="axis__stack" aria-hidden="true">{stack}</span>'
            f'<span class="axis__label" aria-hidden="true"><span class="axis__long">{label}</span>'
            f'<span class="axis__short">{short}</span> <span class="data">{len(items)}</span></span></button>')
    out.append('</div>')
    return ''.join(out)
