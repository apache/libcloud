#!/usr/bin/env python3
"""Writes SHA-256 and SHA-512 hashes of files passed as arguments"""

import hashlib
import sys

for path in sys.argv[1:]:
    for ext, hash in [('sha256', hashlib.sha256), ('sha512', hashlib.sha512)]:
        written = '{}.{}'.format(path, ext)
        with open(path, 'rb') as fin, open(written, 'w') as fout:
            digest = hash(fin.read()).hexdigest()
            print('{} *{}'.format(digest, path), file=fout)
