#!/bin/bash
# godaddy-domains.sh — GoDaddy domain portfolio management
# Usage:
#   godaddy-domains.sh list [--status STATUS] [--expiring] [--privacy-off] [--autorenew-off] [--name PATTERN]
#   godaddy-domains.sh search <query>
#   godaddy-domains.sh info <domain>
#   godaddy-domains.sh privacy-check
# Output: JSON

CONFIG_FILE="$HOME/.webinitor/config.json"
ACTION="$1"
shift

get_auth() {
  if [ ! -f "$CONFIG_FILE" ]; then
    echo '{"error":"no config file — run /webinitor setup godaddy"}' >&2
    exit 1
  fi
  KEY=$(jq -r '.godaddy.api_key // empty' "$CONFIG_FILE")
  SECRET=$(jq -r '.godaddy.api_secret // empty' "$CONFIG_FILE")
  ENV=$(jq -r '.godaddy.environment // "production"' "$CONFIG_FILE")
  if [ -z "$KEY" ] || [ -z "$SECRET" ]; then
    echo '{"error":"GoDaddy API not configured — run /webinitor setup godaddy"}' >&2
    exit 1
  fi
  if [ "$ENV" = "ote" ]; then
    BASE_URL="https://api.ote-godaddy.com"
  else
    BASE_URL="https://api.godaddy.com"
  fi
  AUTH_HEADER="Authorization: sso-key ${KEY}:${SECRET}"
}

case "$ACTION" in
  list)
    get_auth
    STATUS_FILTER=""
    EXPIRING=false
    PRIVACY_OFF=false
    AUTORENEW_OFF=false
    NAME_FILTER=""
    while [ $# -gt 0 ]; do
      case "$1" in
        --status) STATUS_FILTER="$2"; shift 2 ;;
        --expiring) EXPIRING=true; shift ;;
        --privacy-off) PRIVACY_OFF=true; shift ;;
        --autorenew-off) AUTORENEW_OFF=true; shift ;;
        --name) NAME_FILTER="$2"; shift 2 ;;
        *) shift ;;
      esac
    done
    URL="${BASE_URL}/v1/domains?limit=500"
    if [ -n "$STATUS_FILTER" ]; then
      URL="${URL}&statuses=${STATUS_FILTER}"
    fi
    RESPONSE=$(curl -s -w "\n%{http_code}" \
      -H "$AUTH_HEADER" "$URL" 2>/dev/null)
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    if [ "$HTTP_CODE" != "200" ]; then
      jq -n --arg code "$HTTP_CODE" --arg body "$BODY" \
        '{"error":"API returned HTTP "+$code,"details":$body}'
      exit 1
    fi
    # Apply client-side filters
    FILTER='.'
    if [ "$EXPIRING" = true ]; then
      CUTOFF=$(date -v+30d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -d "+30 days" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)
      FILTER="[.[] | select(.expires <= \"$CUTOFF\")]"
    fi
    if [ "$PRIVACY_OFF" = true ]; then
      FILTER="$FILTER | [.[] | select(.privacy == false)]"
    fi
    if [ "$AUTORENEW_OFF" = true ]; then
      FILTER="$FILTER | [.[] | select(.renewAuto == false)]"
    fi
    if [ -n "$NAME_FILTER" ]; then
      FILTER="$FILTER | [.[] | select(.domain | ascii_downcase | contains(\"$(echo "$NAME_FILTER" | tr '[:upper:]' '[:lower:]')\"))]"
    fi
    echo "$BODY" | jq "$FILTER"
    ;;

  privacy-check)
    get_auth
    RESPONSE=$(curl -s -w "\n%{http_code}" \
      -H "$AUTH_HEADER" "${BASE_URL}/v1/domains?limit=500&statuses=ACTIVE" 2>/dev/null)
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    if [ "$HTTP_CODE" != "200" ]; then
      jq -n --arg code "$HTTP_CODE" '{"error":"API returned HTTP "+$code}'
      exit 1
    fi
    echo "$BODY" | jq '{
      total: length,
      privacy_off: [.[] | select(.privacy == false) | .domain],
      autorenew_off: [.[] | select(.renewAuto == false) | .domain],
      unlocked: [.[] | select(.locked == false) | .domain],
      expiration_protection_off: [.[] | select(.expirationProtected == false) | .domain],
      transfer_protection_off: [.[] | select(.transferProtected == false) | .domain]
    }'
    ;;

  search)
    get_auth
    QUERY="$1"
    if [ -z "$QUERY" ]; then
      jq -n '{"error":"search requires a query argument"}'
      exit 1
    fi
    RESPONSE=$(curl -s -w "\n%{http_code}" \
      -H "$AUTH_HEADER" "${BASE_URL}/v1/domains?limit=500" 2>/dev/null)
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    if [ "$HTTP_CODE" != "200" ]; then
      jq -n --arg code "$HTTP_CODE" '{"error":"API returned HTTP "+$code}'
      exit 1
    fi
    echo "$BODY" | jq --arg q "$QUERY" '[.[] | select(.domain | ascii_downcase | contains($q | ascii_downcase))]'
    ;;

  info)
    get_auth
    DOMAIN="$1"
    if [ -z "$DOMAIN" ]; then
      jq -n '{"error":"info requires a domain argument"}'
      exit 1
    fi
    RESPONSE=$(curl -s -w "\n%{http_code}" \
      -H "$AUTH_HEADER" "${BASE_URL}/v1/domains/${DOMAIN}" 2>/dev/null)
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    if [ "$HTTP_CODE" != "200" ]; then
      jq -n --arg code "$HTTP_CODE" --arg domain "$DOMAIN" \
        '{"error":"Failed to get info for "+$domain+": HTTP "+$code}'
      exit 1
    fi
    echo "$BODY" | jq '.'
    ;;

  *)
    jq -n '{"error":"usage: godaddy-domains.sh [list|search|info] [args]"}'
    exit 1
    ;;
esac
