#!/usr/bin/env bash
# Guarda en .env la clave, el endpoint y el modelo del proveedor.
# La clave se escribe sin que se vea en pantalla y no queda en el historial.
#
#   ./configurar.sh
#
set -euo pipefail
cd "$(dirname "$0")"

URL_POR_DEFECTO="https://api.qdiv0.com/v1/chat/completions"

echo "== Modelo (obligatorio) =="
echo "(Enter = valor entre corchetes)"
read -rp "Endpoint [$URL_POR_DEFECTO]: " url
read -rp "Modelo (serving name): " modelo
read -rsp "Clave del modelo (no se muestra): " clave
echo

[ -n "$clave" ] || { echo "No has escrito ninguna clave. No se ha cambiado nada."; exit 1; }

echo
echo "== Claves de herramientas (opcionales, Enter para saltar) =="
read -rsp "HUNTER_API_KEY (correos, hunter.io): " hunter; echo
read -rsp "SHODAN_API_KEY (servicios, shodan.io): " shodan; echo

umask 077
{
  echo "AAP_API_KEY=$clave"
  echo "AAP_URL=${url:-$URL_POR_DEFECTO}"
  [ -n "$modelo" ] && echo "AAP_MODELO=$modelo"
  [ -n "$hunter" ] && echo "HUNTER_API_KEY=$hunter"
  [ -n "$shodan" ] && echo "SHODAN_API_KEY=$shodan"
} > .env
chmod 600 .env

echo
echo "Guardado en $(pwd)/.env (solo lo puede leer tu usuario)."
echo "Claves guardadas: $(grep -oE '^[A-Z_]+' .env | tr '\n' ' ')"
