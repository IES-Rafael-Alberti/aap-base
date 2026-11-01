#!/usr/bin/env bash
# Guarda en .env la clave, el endpoint y el modelo del proveedor.
# La clave se escribe sin que se vea en pantalla y no queda en el historial.
#
#   ./configurar.sh
#
# En el Kali del aula no hace falta: sin .env, el agente usa la IA del aula
# (~/.aula-ia.env). Si lo ejecutas ahí, Enter deja los datos del aula.
set -euo pipefail
cd "$(dirname "$0")"

URL_POR_DEFECTO="https://api.qdiv0.com/v1/chat/completions"
MODELO_POR_DEFECTO=""
CLAVE_AULA=""

# Datos del aula: se leen línea a línea, nunca se ejecuta el fichero.
AULA="$HOME/.aula-ia.env"
dato_aula() { sed -n "s/^$1=//p" "$AULA" | head -n 1 | tr -d "\"'"; }
if [ -f "$AULA" ] && [ ! -L "$AULA" ]; then
  URL_POR_DEFECTO="$(dato_aula AAP_URL)"
  MODELO_POR_DEFECTO="$(dato_aula AAP_MODELO)"
  CLAVE_AULA="$(dato_aula AAP_API_KEY)"
  echo "Tienes la IA del aula (los datos de Acceso-IA.txt): pulsa Enter para usarla."
  echo
fi

echo "== Modelo (obligatorio) =="
echo "(Enter = valor entre corchetes)"
read -rp "Endpoint [$URL_POR_DEFECTO]: " url
read -rp "Modelo (serving name) [$MODELO_POR_DEFECTO]: " modelo
if [ -n "$CLAVE_AULA" ]; then
  read -rsp "Clave del modelo (no se muestra) [Enter = la del aula]: " clave
  clave="${clave:-$CLAVE_AULA}"
else
  read -rsp "Clave del modelo (no se muestra): " clave
fi
echo

[ -n "$clave" ] || { echo "No has escrito ninguna clave. No se ha cambiado nada."; exit 1; }
modelo="${modelo:-$MODELO_POR_DEFECTO}"

umask 077
# Conserva las demás líneas del .env (claves de otras APIs).
otras=""
[ -f .env ] && otras="$(grep -vE '^(AAP_API_KEY|AAP_URL|AAP_MODELO)=' .env || true)"
{
  [ -n "$otras" ] && printf '%s\n' "$otras"
  echo "AAP_API_KEY=$clave"
  echo "AAP_URL=${url:-$URL_POR_DEFECTO}"
  [ -n "$modelo" ] && echo "AAP_MODELO=$modelo"
} > .env
chmod 600 .env

echo
echo "Guardado en $(pwd)/.env (solo lo puede leer tu usuario)."
echo
echo "Si alguna herramienta que construyas necesita su propia clave de API,"
echo "añádela a mano al fichero .env con el formato:  NOMBRE_API_KEY=tu_valor"
echo "y léela en tu herramienta con os.environ.get(\"NOMBRE_API_KEY\")."
