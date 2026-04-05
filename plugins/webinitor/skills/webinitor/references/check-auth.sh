#!/bin/bash
# check-auth.sh — check authentication status for a web service
# Usage: check-auth.sh <cloudflare|railway|godaddy>
# Output: JSON { "service": "...", "authenticated": true/false, "account": "...", "error": "..." }

SERVICE="$1"
CONFIG_DIR="$HOME/.webinitor"
CONFIG_FILE="$CONFIG_DIR/config.json"

case "$SERVICE" in
  cloudflare)
    if ! command -v wrangler >/dev/null 2>&1; then
      jq -n '{"service":"cloudflare","authenticated":false,"error":"wrangler not installed"}'
      exit 0
    fi
    OUTPUT=$(wrangler whoami --json 2>/dev/null)
    if [ $? -eq 0 ] && echo "$OUTPUT" | jq -e '.account // .accounts[0]' >/dev/null 2>&1; then
      ACCOUNT=$(echo "$OUTPUT" | jq -r '(.account.name // .accounts[0].name // .email // "authenticated")')
      jq -n --arg acct "$ACCOUNT" '{"service":"cloudflare","authenticated":true,"account":$acct}'
    else
      jq -n '{"service":"cloudflare","authenticated":false,"error":"not logged in"}'
    fi
    ;;

  cloudflare_api)
    if [ ! -f "$CONFIG_FILE" ]; then
      jq -n '{"service":"cloudflare_api","authenticated":false,"error":"no config file"}'
      exit 0
    fi
    TOKEN=$(jq -r '.cloudflare.api_token // empty' "$CONFIG_FILE" 2>/dev/null)
    if [ -z "$TOKEN" ]; then
      jq -n '{"service":"cloudflare_api","authenticated":false,"error":"no api token configured"}'
      exit 0
    fi
    RESPONSE=$(curl -s -H "Authorization: Bearer ${TOKEN}" \
      "https://api.cloudflare.com/client/v4/user/tokens/verify" 2>/dev/null)
    SUCCESS=$(echo "$RESPONSE" | jq -r '.success' 2>/dev/null)
    if [ "$SUCCESS" = "true" ]; then
      STATUS=$(echo "$RESPONSE" | jq -r '.result.status // "active"' 2>/dev/null)
      MASKED="${TOKEN:0:4}...${TOKEN: -4}"
      jq -n --arg status "$STATUS" --arg token "$MASKED" \
        '{"service":"cloudflare_api","authenticated":true,"account":("token: "+$token),"status":$status}'
    else
      ERROR=$(echo "$RESPONSE" | jq -r '.errors[0].message // "token invalid"' 2>/dev/null)
      jq -n --arg err "$ERROR" '{"service":"cloudflare_api","authenticated":false,"error":$err}'
    fi
    ;;

  railway)
    if ! command -v railway >/dev/null 2>&1; then
      jq -n '{"service":"railway","authenticated":false,"error":"railway not installed"}'
      exit 0
    fi
    OUTPUT=$(railway whoami 2>&1)
    if [ $? -eq 0 ] && ! echo "$OUTPUT" | grep -qi "not logged in"; then
      ACCOUNT=$(echo "$OUTPUT" | head -1 | sed 's/^Logged in as //')
      jq -n --arg acct "$ACCOUNT" '{"service":"railway","authenticated":true,"account":$acct}'
    else
      jq -n '{"service":"railway","authenticated":false,"error":"not logged in"}'
    fi
    ;;

  godaddy)
    if [ ! -f "$CONFIG_FILE" ]; then
      jq -n '{"service":"godaddy","authenticated":false,"error":"no config file"}'
      exit 0
    fi
    KEY=$(jq -r '.godaddy.api_key // empty' "$CONFIG_FILE" 2>/dev/null)
    SECRET=$(jq -r '.godaddy.api_secret // empty' "$CONFIG_FILE" 2>/dev/null)
    ENV=$(jq -r '.godaddy.environment // "production"' "$CONFIG_FILE" 2>/dev/null)
    if [ -z "$KEY" ] || [ -z "$SECRET" ]; then
      jq -n '{"service":"godaddy","authenticated":false,"error":"api key or secret not configured"}'
      exit 0
    fi
    if [ "$ENV" = "ote" ]; then
      BASE_URL="https://api.ote-godaddy.com"
    else
      BASE_URL="https://api.godaddy.com"
    fi
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
      -H "Authorization: sso-key ${KEY}:${SECRET}" \
      "${BASE_URL}/v1/domains?limit=1" 2>/dev/null)
    if [ "$RESPONSE" = "200" ]; then
      MASKED_KEY="${KEY:0:4}...${KEY: -4}"
      jq -n --arg env "$ENV" --arg key "$MASKED_KEY" \
        '{"service":"godaddy","authenticated":true,"account":"API key configured","environment":$env,"key_preview":$key}'
    else
      jq -n --arg code "$RESPONSE" --arg env "$ENV" \
        '{"service":"godaddy","authenticated":false,"environment":$env,"error":"API returned HTTP "+$code}'
    fi
    ;;

  github)
    if ! command -v gh >/dev/null 2>&1; then
      jq -n '{"service":"github","authenticated":false,"error":"gh not installed"}'
      exit 0
    fi
    OUTPUT=$(gh auth status --json user,activeAccount 2>&1)
    if [ $? -eq 0 ]; then
      USER=$(echo "$OUTPUT" | jq -r '.user // .activeAccount // "authenticated"' 2>/dev/null)
      jq -n --arg acct "$USER" '{"service":"github","authenticated":true,"account":$acct}'
    else
      jq -n '{"service":"github","authenticated":false,"error":"not logged in"}'
    fi
    ;;

  *)
    jq -n --arg s "$SERVICE" '{"service":$s,"error":"unknown service"}'
    ;;
esac
