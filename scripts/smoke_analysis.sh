#!/usr/bin/env sh
# Verificação da T2.11 em produção: envia o kit, acompanha até terminar e
# mostra o resultado e o tempo. O token não passa pelo chat nem fica no
# histórico do shell se for colado com `read`:
#
#   read -rs TOKEN && export TOKEN      # cole o access_token da sessão e Enter
#   scripts/smoke_analysis.sh            # API padrão: produção no Render
#   API=http://localhost:8000 scripts/smoke_analysis.sh
#
# O access_token está no localStorage do front (chave sb-<ref>-auth-token).
set -eu

API="${API:-https://globalwatch-cafe-api.onrender.com}"
KIT="$(dirname "$0")/../data/exemplo"
: "${TOKEN:?defina TOKEN com o access_token da sessão (veja o topo do script)}"

auth="Authorization: Bearer $TOKEN"
start=$(date +%s)

created=$(curl -sS -f -H "$auth" \
  -F "image=@$KIT/imagem_multiespectral.tif;type=image/tiff" \
  -F "scl=@$KIT/qualidade_scl.tif;type=image/tiff" \
  "$API/analyses")
id=$(printf '%s' "$created" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
echo "POST /analyses -> 202, id $id"

while :; do
  detail=$(curl -sS -f -H "$auth" "$API/analyses/$id")
  status=$(printf '%s' "$detail" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')
  [ "$status" != "processing" ] && break
  sleep 2
done
echo "status: $status após $(( $(date +%s) - start )) s (inclui upload)"

printf '%s' "$detail" | python3 -c '
import json, sys
d = json.load(sys.stdin)
s = d.get("stats") or {}
print("área total:", s.get("total_area_ha"), "ha | área potencial:", s.get("potential_area_ha"),
      "ha | polígonos:", s.get("polygon_count"))
print("erro:", d.get("error"))
print("links assinados:", sorted((d.get("urls") or {}).keys()))'
