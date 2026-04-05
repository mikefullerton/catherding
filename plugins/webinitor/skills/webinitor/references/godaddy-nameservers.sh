#!/bin/bash
# godaddy-nameservers.sh — get/set nameservers for a GoDaddy domain
# Usage:
#   godaddy-nameservers.sh get <domain>
#   godaddy-nameservers.sh set <domain> <ns1> <ns2> [ns3] [ns4]
# Output: JSON

CONFIG_FILE="$HOME/.webinitor/config.json"
ACTION="$1"
DOMAIN="$2"

get_auth() {
  if [ ! -f "$CONFIG_FILE" ]; then
    echo '{"error":"no config file"}' >&2
    exit 1
  fi
  KEY=$(jq -r '.godaddy.api_key // empty' "$CONFIG_FILE")
  SECRET=$(jq -r '.godaddy.api_secret // empty' "$CONFIG_FILE")
  ENV=$(jq -r '.godaddy.environment // "production"' "$CONFIG_FILE")
  if [ -z "$KEY" ] || [ -z "$SECRET" ]; then
    echo '{"error":"GoDaddy API not configured"}' >&2
    exit 1
  fi
  if [ "$ENV" = "ote" ]; then
    BASE_URL="https://api.ote-godaddy.com"
  else
    BASE_URL="https://api.godaddy.com"
  fi
  AUTH_HEADER="Authorization: sso-key ${KEY}:${SECRET}"
}

if [ -z "$DOMAIN" ]; then
  jq -n '{"error":"domain argument required"}'
  exit 1
fi

case "$ACTION" in
  get)
    get_auth
    RESPONSE=$(curl -s -w "\n%{http_code}" \
      -H "$AUTH_HEADER" "${BASE_URL}/v1/domains/${DOMAIN}" 2>/dev/null)
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    if [ "$HTTP_CODE" != "200" ]; then
      jq -n --arg code "$HTTP_CODE" '{"error":"HTTP "+$code}'
      exit 1
    fi
    echo "$BODY" | jq '{domain: .domain, nameServers: .nameServers}'
    ;;

  set)
    get_auth
    shift 2  # skip action and domain
    NS_ARRAY=$(printf '%s\n' "$@" | jq -R -s 'split("\n") | map(select(length > 0))')
    PAYLOAD=$(jq -n --argjson ns "$NS_ARRAY" '{"nameServers": $ns}')
    RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH \
      -H "$AUTH_HEADER" \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD" \
      "${BASE_URL}/v1/domains/${DOMAIN}" 2>/dev/null)
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
      jq -n --arg domain "$DOMAIN" --argjson ns "$NS_ARRAY" \
        '{"status":"updated","domain":$domain,"nameServers":$ns}'
    else
      jq -n --arg code "$HTTP_CODE" --arg body "$BODY" \
        '{"status":"failed","http_code":$code,"error":$body}'
    fi
    ;;

  *)
    jq -n '{"error":"usage: godaddy-nameservers.sh [get|set] <domain> [ns1 ns2 ...]"}'
    exit 1
    ;;
esac
