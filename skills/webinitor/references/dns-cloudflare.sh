#!/bin/bash
# dns-cloudflare.sh — DNS record management via Cloudflare API
# Usage:
#   dns-cloudflare.sh list <domain>
#   dns-cloudflare.sh add <domain> <type> <name> <value> [ttl] [proxied]
#   dns-cloudflare.sh update <domain> <record_id> <value> [ttl] [proxied]
#   dns-cloudflare.sh delete <domain> <record_id>
# Output: JSON

CONFIG_FILE="$HOME/.webinitor/config.json"
ACTION="$1"
DOMAIN="$2"
CF_API="https://api.cloudflare.com/client/v4"

get_auth() {
  if [ ! -f "$CONFIG_FILE" ]; then
    echo '{"error":"no config file"}' >&2
    exit 1
  fi
  TOKEN=$(jq -r '.cloudflare.api_token // empty' "$CONFIG_FILE")
  if [ -z "$TOKEN" ]; then
    echo '{"error":"Cloudflare API token not configured — run /webinitor setup cloudflare"}' >&2
    exit 1
  fi
  AUTH_HEADER="Authorization: Bearer ${TOKEN}"
}

get_zone_id() {
  local domain="$1"
  ZONE_RESPONSE=$(curl -s -H "$AUTH_HEADER" \
    "${CF_API}/zones?name=${domain}&per_page=1" 2>/dev/null)
  ZONE_ID=$(echo "$ZONE_RESPONSE" | jq -r '.result[0].id // empty' 2>/dev/null)
  if [ -z "$ZONE_ID" ]; then
    jq -n --arg domain "$domain" '{"error":"Zone not found for "+$domain+" in Cloudflare"}'
    exit 1
  fi
}

if [ -z "$DOMAIN" ]; then
  jq -n '{"error":"domain argument required"}'
  exit 1
fi

case "$ACTION" in
  list)
    get_auth
    get_zone_id "$DOMAIN"
    PAGE=1
    ALL_RECORDS="[]"
    while true; do
      RESPONSE=$(curl -s -H "$AUTH_HEADER" \
        "${CF_API}/zones/${ZONE_ID}/dns_records?per_page=100&page=${PAGE}" 2>/dev/null)
      SUCCESS=$(echo "$RESPONSE" | jq -r '.success' 2>/dev/null)
      if [ "$SUCCESS" != "true" ]; then
        ERROR=$(echo "$RESPONSE" | jq -r '.errors[0].message // "unknown error"' 2>/dev/null)
        jq -n --arg err "$ERROR" '{"error":$err}'
        exit 1
      fi
      RECORDS=$(echo "$RESPONSE" | jq '[.result[] | {id, type, name, content, ttl, proxied}]')
      ALL_RECORDS=$(echo "$ALL_RECORDS" "$RECORDS" | jq -s '.[0] + .[1]')
      TOTAL=$(echo "$RESPONSE" | jq -r '.result_info.total_pages // 1')
      if [ "$PAGE" -ge "$TOTAL" ]; then
        break
      fi
      PAGE=$((PAGE + 1))
    done
    echo "$ALL_RECORDS"
    ;;

  add)
    get_auth
    get_zone_id "$DOMAIN"
    TYPE="$3"
    NAME="$4"
    VALUE="$5"
    TTL="${6:-1}"
    PROXIED="${7:-false}"
    if [ -z "$TYPE" ] || [ -z "$NAME" ] || [ -z "$VALUE" ]; then
      jq -n '{"error":"add requires: <domain> <type> <name> <value> [ttl] [proxied]"}'
      exit 1
    fi
    PAYLOAD=$(jq -n --arg type "$TYPE" --arg name "$NAME" --arg content "$VALUE" \
      --argjson ttl "$TTL" --argjson proxied "$PROXIED" \
      '{"type":$type,"name":$name,"content":$content,"ttl":$ttl,"proxied":$proxied}')
    RESPONSE=$(curl -s -X POST \
      -H "$AUTH_HEADER" \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD" \
      "${CF_API}/zones/${ZONE_ID}/dns_records" 2>/dev/null)
    SUCCESS=$(echo "$RESPONSE" | jq -r '.success' 2>/dev/null)
    if [ "$SUCCESS" = "true" ]; then
      echo "$RESPONSE" | jq '{status:"added", id:.result.id, type:.result.type, name:.result.name, content:.result.content}'
    else
      ERROR=$(echo "$RESPONSE" | jq -r '.errors[0].message // "unknown error"' 2>/dev/null)
      jq -n --arg err "$ERROR" '{"status":"failed","error":$err}'
    fi
    ;;

  update)
    get_auth
    get_zone_id "$DOMAIN"
    RECORD_ID="$3"
    VALUE="$4"
    TTL="${5:-1}"
    PROXIED="${6:-false}"
    if [ -z "$RECORD_ID" ] || [ -z "$VALUE" ]; then
      jq -n '{"error":"update requires: <domain> <record_id> <value> [ttl] [proxied]"}'
      exit 1
    fi
    PAYLOAD=$(jq -n --arg content "$VALUE" --argjson ttl "$TTL" --argjson proxied "$PROXIED" \
      '{"content":$content,"ttl":$ttl,"proxied":$proxied}')
    RESPONSE=$(curl -s -X PATCH \
      -H "$AUTH_HEADER" \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD" \
      "${CF_API}/zones/${ZONE_ID}/dns_records/${RECORD_ID}" 2>/dev/null)
    SUCCESS=$(echo "$RESPONSE" | jq -r '.success' 2>/dev/null)
    if [ "$SUCCESS" = "true" ]; then
      echo "$RESPONSE" | jq '{status:"updated", id:.result.id, type:.result.type, name:.result.name, content:.result.content}'
    else
      ERROR=$(echo "$RESPONSE" | jq -r '.errors[0].message // "unknown error"' 2>/dev/null)
      jq -n --arg err "$ERROR" '{"status":"failed","error":$err}'
    fi
    ;;

  delete)
    get_auth
    get_zone_id "$DOMAIN"
    RECORD_ID="$3"
    if [ -z "$RECORD_ID" ]; then
      jq -n '{"error":"delete requires: <domain> <record_id>"}'
      exit 1
    fi
    RESPONSE=$(curl -s -X DELETE \
      -H "$AUTH_HEADER" \
      "${CF_API}/zones/${ZONE_ID}/dns_records/${RECORD_ID}" 2>/dev/null)
    SUCCESS=$(echo "$RESPONSE" | jq -r '.success' 2>/dev/null)
    if [ "$SUCCESS" = "true" ]; then
      jq -n --arg id "$RECORD_ID" '{"status":"deleted","id":$id}'
    else
      ERROR=$(echo "$RESPONSE" | jq -r '.errors[0].message // "unknown error"' 2>/dev/null)
      jq -n --arg err "$ERROR" '{"status":"failed","error":$err}'
    fi
    ;;

  *)
    jq -n '{"error":"usage: dns-cloudflare.sh [list|add|update|delete] <domain> [args]"}'
    exit 1
    ;;
esac
