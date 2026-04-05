#!/bin/bash
# cloudflare-zones.sh — Cloudflare zone management
# Usage:
#   cloudflare-zones.sh get <domain>      — lookup zone by name
#   cloudflare-zones.sh create <domain>   — create new zone
#   cloudflare-zones.sh check <domain>    — check activation status
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
  ACCOUNT_ID=$(jq -r '.cloudflare.account_id // empty' "$CONFIG_FILE")
  if [ -z "$TOKEN" ]; then
    echo '{"error":"Cloudflare API token not configured"}' >&2
    exit 1
  fi
  AUTH_HEADER="Authorization: Bearer ${TOKEN}"
}

if [ -z "$DOMAIN" ]; then
  jq -n '{"error":"domain argument required"}'
  exit 1
fi

case "$ACTION" in
  get)
    get_auth
    RESPONSE=$(curl -s -H "$AUTH_HEADER" \
      "${CF_API}/zones?name=${DOMAIN}&per_page=1" 2>/dev/null)
    SUCCESS=$(echo "$RESPONSE" | jq -r '.success' 2>/dev/null)
    if [ "$SUCCESS" != "true" ]; then
      ERROR=$(echo "$RESPONSE" | jq -r '.errors[0].message // "unknown error"' 2>/dev/null)
      jq -n --arg err "$ERROR" '{"error":$err}'
      exit 1
    fi
    COUNT=$(echo "$RESPONSE" | jq -r '.result_info.count // 0')
    if [ "$COUNT" -eq 0 ]; then
      jq -n --arg domain "$DOMAIN" '{"found":false,"domain":$domain}'
    else
      echo "$RESPONSE" | jq '{found:true, id:.result[0].id, domain:.result[0].name, status:.result[0].status, name_servers:.result[0].name_servers}'
    fi
    ;;

  create)
    get_auth
    if [ -z "$ACCOUNT_ID" ]; then
      jq -n '{"error":"account_id not configured — run /webinitor setup cloudflare"}'
      exit 1
    fi
    PAYLOAD=$(jq -n --arg name "$DOMAIN" --arg aid "$ACCOUNT_ID" \
      '{"name":$name,"account":{"id":$aid},"type":"full"}')
    RESPONSE=$(curl -s -X POST \
      -H "$AUTH_HEADER" \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD" \
      "${CF_API}/zones" 2>/dev/null)
    SUCCESS=$(echo "$RESPONSE" | jq -r '.success' 2>/dev/null)
    if [ "$SUCCESS" = "true" ]; then
      echo "$RESPONSE" | jq '{status:"created", id:.result.id, domain:.result.name, zone_status:.result.status, name_servers:.result.name_servers}'
    else
      CODE=$(echo "$RESPONSE" | jq -r '.errors[0].code // 0')
      # Code 1061 = zone already exists
      if [ "$CODE" = "1061" ]; then
        # Fetch existing zone instead
        EXISTING=$(curl -s -H "$AUTH_HEADER" \
          "${CF_API}/zones?name=${DOMAIN}&per_page=1" 2>/dev/null)
        echo "$EXISTING" | jq '{status:"already_exists", id:.result[0].id, domain:.result[0].name, zone_status:.result[0].status, name_servers:.result[0].name_servers}'
      else
        ERROR=$(echo "$RESPONSE" | jq -r '.errors[0].message // "unknown error"' 2>/dev/null)
        jq -n --arg err "$ERROR" '{"status":"failed","error":$err}'
      fi
    fi
    ;;

  check)
    get_auth
    RESPONSE=$(curl -s -H "$AUTH_HEADER" \
      "${CF_API}/zones?name=${DOMAIN}&per_page=1" 2>/dev/null)
    COUNT=$(echo "$RESPONSE" | jq -r '.result_info.count // 0')
    if [ "$COUNT" -eq 0 ]; then
      jq -n --arg domain "$DOMAIN" '{"found":false,"domain":$domain}'
      exit 0
    fi
    ZONE_ID=$(echo "$RESPONSE" | jq -r '.result[0].id')
    STATUS=$(echo "$RESPONSE" | jq -r '.result[0].status')
    NS=$(echo "$RESPONSE" | jq -c '.result[0].name_servers')
    jq -n --arg id "$ZONE_ID" --arg domain "$DOMAIN" --arg status "$STATUS" --argjson ns "$NS" \
      '{"found":true,"id":$id,"domain":$domain,"status":$status,"name_servers":$ns}'
    ;;

  *)
    jq -n '{"error":"usage: cloudflare-zones.sh [get|create|check] <domain>"}'
    exit 1
    ;;
esac
