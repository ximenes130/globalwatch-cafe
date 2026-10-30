#!/usr/bin/env bash
# Exporta a nota de pesquisa para PDF A4 e confere as duas páginas (T7.2, R7.13).
# Requer pandoc e Chrome/Chromium. Uso (da raiz): scripts/export_note.sh
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

cat > "$work/style.css" <<'CSS'
@page { size: A4; margin: 13mm 15mm; }
body { font: 10pt/1.36 "DejaVu Sans", sans-serif; color: #14201a; }
h1 { font-size: 14pt; margin: 0 0 2pt; }
h2 { font-size: 10.5pt; margin: 7pt 0 2pt; color: #1e4a2a; }
p, ul, ol { margin: 0 0 4pt; }
ul, ol { padding-left: 15pt; }
li { margin: 0; }
table { border-collapse: collapse; width: 100%; font-size: 8.8pt; margin: 2pt 0 4pt; }
th, td { border: 0.5pt solid #b8c0b8; padding: 1.5pt 4pt; text-align: left; vertical-align: top; }
code { font-size: 8.4pt; }
a { color: inherit; text-decoration: none; }
tr, li { break-inside: avoid; }
CSS

pandoc "$root/docs/nota-de-pesquisa.md" --standalone --metadata title=" " \
  --css "$work/style.css" --embed-resources -o "$work/nota.html" 2>/dev/null
chrome="$(command -v google-chrome || command -v chromium)"
"$chrome" --headless --no-pdf-header-footer --print-to-pdf="$root/docs/nota-de-pesquisa.pdf" \
  "file://$work/nota.html" 2>/dev/null
pages="$(pdfinfo "$root/docs/nota-de-pesquisa.pdf" | awk '/^Pages:/ {print $2}')"
echo "docs/nota-de-pesquisa.pdf: $pages página(s)"
[ "$pages" -le 2 ]
