"""Tiny markup -> (React flight JSON, React-identical SSR HTML).

Markup: '## ' h2, '### ' h3, '- ' list items, '| a | b |' table rows (first row
= header), blank line = new block, single newline inside a paragraph = <br/>,
**bold**, *italic*, [text](url), backslash escapes (\\*).
"""
import json
import re

VOID = {'br'}


class El:
    def __init__(self, tag, props=None, children=None):
        self.tag = tag
        self.props = props or {}
        self.children = children or []


def esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
             .replace('"', '&quot;').replace("'", '&#x27;'))


def _norm_children(ch):
    out = []
    for c in ch:
        if isinstance(c, str) and out and isinstance(out[-1], str):
            out[-1] += c
        elif c != '':
            out.append(c)
    return out


ATTR = {'className': 'class'}


def to_html(node):
    if isinstance(node, str):
        return esc(node)
    if isinstance(node, list):
        parts = []
        prev_text = False
        for c in node:
            is_text = isinstance(c, str)
            if is_text and prev_text:
                parts.append('<!-- -->')
            parts.append(to_html(c))
            prev_text = is_text
        return ''.join(parts)
    attrs = ''
    for k, v in node.props.items():
        if v is None:
            continue
        attrs += f' {ATTR.get(k, k)}="{esc(str(v))}"'
    if node.tag in VOID:
        return f'<{node.tag}{attrs}/>'
    ch = _norm_children(node.children)
    return f'<{node.tag}{attrs}>{to_html(ch)}</{node.tag}>'


def to_flight(node, key=None):
    if isinstance(node, str):
        return node
    props = dict(node.props)
    ch = _norm_children(node.children)
    if ch:
        if len(ch) == 1:
            props['children'] = to_flight(ch[0])
        else:
            props['children'] = [to_flight(c) for c in ch]
    return ['$', node.tag, key, props]


def flight_json(node):
    return json.dumps(to_flight(node), ensure_ascii=False, separators=(',', ':'))


# ---------------------------------------------------------------- inline
INLINE_RE = re.compile(r'\\(.)|\*\*(.+?)\*\*|\*(.+?)\*|\[([^\]]+)\]\(([^)]+)\)')


def inline(text):
    out = []
    pos = 0
    for m in INLINE_RE.finditer(text):
        out.append(text[pos:m.start()])
        if m.group(1) is not None:
            out.append(m.group(1))
        elif m.group(2) is not None:
            out.append(El('strong', {}, inline(m.group(2))))
        elif m.group(3) is not None:
            out.append(El('em', {}, inline(m.group(3))))
        else:
            href = m.group(5)
            props = {'className': 'link', 'href': href}
            if href.startswith('http'):
                props.update({'target': '_blank', 'rel': 'noopener noreferrer'})
            out.append(El('a', props, inline(m.group(4))))
        pos = m.end()
    out.append(text[pos:])
    return _norm_children(out)


def lines_inline(lines):
    out = []
    for i, ln in enumerate(lines):
        if i:
            out.append(El('br'))
        out.extend(inline(ln))
    return out


def parse(md):
    blocks = [b for b in re.split(r'\n\s*\n', md.strip()) if b.strip()]
    out = []
    for b in blocks:
        lines = b.split('\n')
        if lines[0].startswith('### '):
            out.append(El('h3', {}, inline(lines[0][4:])))
        elif lines[0].startswith('## '):
            out.append(El('h2', {}, inline(lines[0][3:])))
        elif all(l.startswith('- ') for l in lines):
            out.append(El('ul', {}, [El('li', {}, inline(l[2:])) for l in lines]))
        elif all(l.startswith('|') for l in lines):
            rows = [[c.strip() for c in l.strip().strip('|').split(' | ')] for l in lines]
            head = El('thead', {}, [El('tr', {}, [El('th', {}, inline(c)) for c in rows[0]])])
            body = El('tbody', {}, [El('tr', {}, [El('td', {}, inline(c)) for c in r]) for r in rows[1:]])
            out.append(El('div', {'className': 'doc__table'}, [El('table', {}, [head, body])]))
        else:
            out.append(El('p', {}, lines_inline(lines)))
    return out
