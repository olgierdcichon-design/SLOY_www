"""Small helpers for safely editing a Next.js static export (output: 'export').

Every page directory holds the same React Server Component ("flight") payload in
several places: inline in index.html (self.__next_f.push([1,"..."])), in
index.txt / __next._full.txt, and split into per-segment __next.*.txt files.
Edits must be applied consistently to all of them, otherwise React hydration
would overwrite the HTML with the old payload.
"""
import json
import os
import re

PUSH_RE = re.compile(r'self\.__next_f\.push\((\[1,".*?"\])\)</script>', re.S)


def jesc(s):
    """Escape a Python str the way JSON.stringify does (without quotes)."""
    return json.dumps(s, ensure_ascii=False)[1:-1]


def encode_inline(decoded):
    """Re-encode a decoded flight string as the JS array literal Next emits."""
    lit = json.dumps([1, decoded], ensure_ascii=False, separators=(',', ':'))
    # Next's htmlEscapeJsonString
    return (lit.replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
               .replace('\u2028', '\\u2028').replace('\u2029', '\\u2029'))


class Page:
    def __init__(self, root, route):
        self.root = root
        self.route = route.strip('/')
        self.dir = os.path.join(root, self.route) if self.route else root
        self.html_path = os.path.join(self.dir, 'index.html')
        with open(self.html_path, encoding='utf-8') as f:
            self.html = f.read()
        m = PUSH_RE.search(self.html)
        self._push_literal = m.group(1) if m else None
        self.inline = json.loads(m.group(1))[1] if m else None
        if m:
            assert encode_inline(self.inline) == self._push_literal, 'inline round-trip failed: ' + self.html_path
        self.txt = {}
        for name in os.listdir(self.dir):
            p = os.path.join(self.dir, name)
            if name.endswith('.txt') and os.path.isfile(p):
                with open(p, encoding='utf-8') as f:
                    self.txt[name] = f.read()

    # ---- flight payload -------------------------------------------------
    def fsub(self, old, new, required=True, max_inline=None):
        """Replace a decoded-flight substring in the inline payload and all .txt files."""
        n = 0
        if self.inline is not None and old in self.inline:
            c = self.inline.count(old)
            if max_inline is not None:
                assert c <= max_inline, f'{self.route}: {c} matches for {old[:60]!r}'
            self.inline = self.inline.replace(old, new)
            n += c
        for k, v in self.txt.items():
            if old in v:
                self.txt[k] = v.replace(old, new)
                n += 1
        if required and n == 0:
            raise ValueError(f'{self.route}: flight text not found: {old[:80]!r}')
        return n

    # ---- html (outside the inline payload) ------------------------------
    def hsub(self, old, new, count=1):
        head, sep, tail = self._split()
        c = head.count(old) + tail.count(old)
        if count is not None and c != count:
            raise ValueError(f'{self.route}: expected {count} html match(es), got {c}: {old[:80]!r}')
        head = head.replace(old, new)
        tail = tail.replace(old, new)
        self.html = head + sep + tail

    def _split(self):
        if self._push_literal is None:
            return self.html, '', ''
        i = self.html.index(self._push_literal)
        return self.html[:i], self._push_literal, self.html[i + len(self._push_literal):]

    def save(self, new_dir=None):
        d = new_dir or self.dir
        os.makedirs(d, exist_ok=True)
        html = self.html
        if self._push_literal is not None:
            html = html.replace(self._push_literal, encode_inline(self.inline), 1)
        with open(os.path.join(d, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html)
        for k, v in self.txt.items():
            with open(os.path.join(d, k), 'w', encoding='utf-8') as f:
                f.write(v)


def all_routes(root):
    out = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if not d.startswith(('.', '_next')) and d != 'tools']
        if 'index.html' in fn:
            out.append(os.path.relpath(dp, root).replace('\\', '/') if dp != root else '')
    return sorted(out)


def find_element(s, start):
    """Given s[start] == '[', return index just past the matching ']' (JSON-aware)."""
    assert s[start] == '['
    depth = 0
    i = start
    in_str = False
    while i < len(s):
        ch = s[i]
        if in_str:
            if ch == '\\':
                i += 2
                continue
            if ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch in '[{':
                depth += 1
            elif ch in ']}':
                depth -= 1
                if depth == 0:
                    return i + 1
        i += 1
    raise ValueError('unbalanced')
