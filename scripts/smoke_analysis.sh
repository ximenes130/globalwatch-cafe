#!/usr/bin/env sh
# Verificação em produção (T2.11, T3.4): envia uma imagem (padrão: o kit),
# acompanha até terminar e mostra o resultado e o tempo. O token não passa pelo chat nem fica no
# histórico do shell se for colado com `read`:
#
#   read -rs TOKEN && export TOKEN      # cole o access_token da sessão e Enter
#   scripts/smoke_analysis.sh            # API padrão: produção no Render
#   API=http://localhost:8000 scripts/smoke_analysis.sh
#   IMAGE=data/adicional/<item>/imagem_multiespectral.tif \
#     SCL=data/adicional/<item>/qualidade_scl.tif scripts/smoke_analysis.sh
#   IMAGE_2=data/adicional/<item>/imagem_multiespectral.tif \
#     SCL_2=data/adicional/<item>/qualidade_scl.tif scripts/smoke_analysis.sh   # duas datas
#
# O access_token está no localStorage do front (chave sb-<ref>-auth-token).
set -eu

API="${API:-https://globalwatch-cafe-api.onrender.com}"
KIT="$(dirname "$0")/../data/exemplo"
IMAGE="${IMAGE:-$KIT/imagem_multiespectral.tif}"
SCL="${SCL:-$KIT/qualidade_scl.tif}"
: "${TOKEN:?defina TOKEN com o access_token da sessão (veja o topo do script)}"

auth="Authorization: Bearer $TOKEN"
# Segunda data opcional (T3.5): só entra no formulário se IMAGE_2 estiver definida.
set --
[ -n "${IMAGE_2:-}" ] && set -- -F "image_2=@$IMAGE_2;type=image/tiff"
[ -n "${SCL_2:-}" ] && set -- "$@" -F "scl_2=@$SCL_2;type=image/tiff"
start=$(date +%s)

created=$(curl -sS -f -H "$auth" \
  -F "image=@$IMAGE;type=image/tiff" \
  -F "scl=@$SCL;type=image/tiff" \
  "$@" \
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
print("data da imagem:", d.get("acquired_at"), "| segunda data:", s.get("second_acquired_at"))
print("área total:", s.get("total_area_ha"), "ha | área potencial:", s.get("potential_area_ha"),
      "ha | polígonos:", s.get("polygon_count"))
print("excluído por amplitude:", (s.get("excluded_area_ha") or {}).get("high_amplitude"), "ha")
print("erro:", d.get("error"))
print("links assinados:", sorted((d.get("urls") or {}).keys()))'
