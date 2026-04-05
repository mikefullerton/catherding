#!/bin/bash
# dns-godaddy.sh — DNS record management via GoDaddy API
# Usage:
#   dns-godaddy.sh list <domain>
#   dns-godaddy.sh add <domain> <type> <name> <value> [ttl]
#   dns-godaddy.sh update <domain> <type> <name> <value> [ttl]
#   dns-godaddy.sh delete <domain> <type> <name> <value>
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
  list)
    get_auth
    RESPONSE=$(curl -s -w "\n%{http_code}" \
      -H "$AUTH_HEADER" \
      "${BASE_URL}/v1/domains/${DOMAIN}/records" 2>/dev/null)
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    if [ "$HTTP_CODE" != "200" ]; then
      jq -n --arg code "$HTTP_CODE" '{"error":"HTTP "+$code}'
      exit 1
    fi
    echo "$BODY" | jq '[.[] | {type, name, data, ttl}]'
    ;;

  add)
    get_auth
    TYPE="$3"
    NAME="$4"
    VALUE="$5"
    TTL="${6:-3600}"
    if [ -z "$TYPE" ] || [ -z "$NAME" ] || [ -z "$VALUE" ]; then
      jq -n '{"error":"add requires: <domain> <type> <name> <value> [ttl]"}'
      exit 1
    fi
    RECORD=$(jq -n --arg type "$TYPE" --arg name "$NAME" --arg data "$VALUE" --argjson ttl "$TTL" \
      '[{"type":$type,"name":$name,"data":$data,"ttl":$ttl}]')
    RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH \
      -H "$AUTH_HEADER" \
      -H "Content-Type: application/json" \
      -d "$RECORD" \
      "${BASE_URL}/v1/domains/${DOMAIN}/records" 2>/dev/null)
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
      jq -n --arg type "$TYPE" --arg name "$NAME" --arg data "$VALUE" \
        '{"status":"added","type":$type,"name":$name,"data":$data}'
    else
      jq -n --arg code "$HTTP_CODE" --arg body "$BODY" \
        '{"status":"failed","http_code":$code,"error":$body}'
    fi
    ;;

  update)
    get_auth
    TYPE="$3"
    NAME="$4"
    VALUE="$5"
    TTL="${6:-3600}"
    if [ -z "$TYPE" ] || [ -z "$NAME" ] || [ -z "$VALUE" ]; then
      jq -n '{"error":"update requires: <domain> <type> <name> <value> [ttl]"}'
      exit 1
    fi
    RECORD=$(jq -n --arg data "$VALUE" --argjson ttl "$TTL" \
      '[{"data":$data,"ttl":$ttl}]')
    RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT \
      -H "$AUTH_HEADER" \
      -H "Content-Type: application/json" \
      -d "$RECORD" \
      "${BASE_URL}/v1/domains/${DOMAIN}/records/${TYPE}/${NAME}" 2>/dev/null)
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
      jq -n --arg type "$TYPE" --arg name "$NAME" --arg data "$VALUE" \
        '{"status":"updated","type":$type,"name":$name,"data":$data}'
    else
      jq -n --arg code "$HTTP_CODE" --arg body "$BODY" \
        '{"status":"failed","http_code":$code,"error":$body}'
    fi
    ;;

  delete)
    get_auth
    TYPE="$3"
    NAME="$4"
    VALUE="$5"
    if [ -z "$TYPE" ] || [ -z "$NAME" ]; then
      jq -n '{"error":"delete requires: <domain> <type> <name> [value]"}'
      exit 1
    fi
    # GoDaddy has no individual record delete — fetch existing, remove target, PUT back
    RESPONSE=$(curl -s -w "\n%{http_code}" \
      -H "$AUTH_HEADER" \
      "${BASE_URL}/v1/domains/${DOMAIN}/records/${TYPE}/${NAME}" 2>/dev/null)
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    if [ "$HTTP_CODE" != "200" ]; then
      jq -n --arg code "$HTTP_CODE" '{"status":"failed","error":"HTTP "+$code}'
      exit 1
    fi
    COUNT=$(echo "$BODY" | jq 'length')
    if [ "$COUNT" -eq 0 ]; then
      jq -n '{"status":"not_found","error":"no records match"}'
      exit 0
    fi
    if [ -n "$VALUE" ]; then
      # Remove specific record by value
      REMAINING=$(echo "$BODY" | jq --arg val "$VALUE" '[.[] | select(.data != $val)]')
    else
      # Remove all records of this type/name (empty array)
      REMAINING="[]"
    fi
    RESPONSE2=$(curl -s -w "\n%{http_code}" -X PUT \
      -H "$AUTH_HEADER" \
      -H "Content-Type: application/json" \
      -d "$REMAINING" \
      "${BASE_URL}/v1/domains/${DOMAIN}/records/${TYPE}/${NAME}" 2>/dev/null)
    HTTP_CODE2=$(echo "$RESPONSE2" | tail -1)
    if [ "$HTTP_CODE2" = "200" ] || [ "$HTTP_CODE2" = "204" ]; then
      REMAINING_COUNT=$(echo "$REMAINING" | jq 'length')
      jq -n --arg type "$TYPE" --arg name "$NAME" --argjson remaining "$REMAINING_COUNT" \
        '{"status":"deleted","type":$type,"name":$name,"remaining_records":$remaining}'
    else
      BODY2=$(echo "$RESPONSE2" | sed '$d')
      jq -n --arg code "$HTTP_CODE2" --arg body "$BODY2" \
        '{"status":"failed","http_code":$code,"error":$body}'
    fi
    ;;

  *)
    jq -n '{"error":"usage: dns-godaddy.sh [list|add|update|delete] <domain> [args]"}'
    exit 1
    ;;
esac
