#!/usr/bin/env python3
"""Switch the site from staging to production: removes the noindex blocks.

Run ONLY on the day the new site goes live on sloy.pl (after the Shopify store
is closed and the domain points to Hostinger):
    python3 tools/go_live.py .
"""
import os
import re
import sys

root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')
META = '<meta name="robots" content="noindex" data-sloy="staging"/>'
n = 0
for dp, dn, fn in os.walk(root):
    dn[:] = [d for d in dn if not d.startswith(('.', '_next')) and d != 'tools']
    for f in fn:
        if f.endswith('.html'):
            p = os.path.join(dp, f)
            with open(p, encoding='utf-8') as fh:
                h = fh.read()
            if META in h:
                with open(p, 'w', encoding='utf-8') as fh:
                    fh.write(h.replace(META, ''))
                n += 1
ht = os.path.join(root, '.htaccess')
with open(ht, encoding='utf-8') as fh:
    s = fh.read()
s2 = re.sub(r'# >>> STAGING-NOINDEX.*?# <<< STAGING-NOINDEX\n', '', s, flags=re.S)
with open(ht, 'w', encoding='utf-8') as fh:
    fh.write(s2)
print(f'noindex removed from {n} pages; .htaccess header block', 'removed' if s2 != s else 'not found')
