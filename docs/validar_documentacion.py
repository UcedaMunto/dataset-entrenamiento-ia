#!/usr/bin/env python3
"""Valida enlaces Markdown locales e inventario, sin red ni escrituras."""
import re
import subprocess
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r'(?<!!)\[[^\]\n]+\]\((<[^>]+>|[^)\n]+)\)')


def markdown_files():
    result = subprocess.run(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
        cwd=ROOT, check=True, capture_output=True,
    )
    return sorted({ROOT / name.decode() for name in result.stdout.split(b'\0')
                   if name and name.decode().endswith('.md')})


def prose(text):
    return re.sub(r'^```[^\n]*\n.*?^```[^\n]*$', '', text, flags=re.M | re.S)


def anchors(path):
    found, counts = set(), {}
    for heading in re.findall(r'^#{1,6}\s+(.+?)\s*#*$', prose(path.read_text()), re.M):
        slug = re.sub(r'[`*_]', '', heading).lower()
        slug = ''.join(c for c in slug if c in ' -_' or unicodedata.category(c)[0] in 'LN')
        slug = slug.replace(' ', '-')
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        found.add(slug if count == 0 else f'{slug}-{count}')
    return found


def main():
    files, errors, checked = markdown_files(), [], 0
    index = ROOT / 'docs/INDICE.md'
    indexed = set()
    for source in files:
        for match in LINK.finditer(prose(source.read_text())):
            target = match.group(1)
            target = target[1:-1] if target.startswith('<') else target.split(' "', 1)[0]
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc:
                continue
            destination = (source.parent / unquote(parsed.path)).resolve() if parsed.path else source
            checked += 1
            if source == index:
                indexed.add(destination)
            if not destination.exists():
                errors.append(f'{source.relative_to(ROOT)}: no existe {target}')
            elif parsed.fragment and destination.suffix == '.md':
                if unquote(parsed.fragment) not in anchors(destination):
                    errors.append(f'{source.relative_to(ROOT)}: ancla no encontrada {target}')
    for source in files:
        if source.resolve() not in indexed and source != index:
            errors.append(f'No indexado: {source.relative_to(ROOT)}')
    print(f'{len(files)} documentos; {checked} enlaces locales comprobados; {len(errors)} errores.')
    for error in errors:
        print(error)
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
