#!/bin/bash
# dns-detect.sh — detect DNS provider for a domain by checking nameservers
# Usage: dns-detect.sh <domain>
# Output: JSON { "domain": "...", "provider": "cloudflare|godaddy|unknown", "nameservers": [...] }

CONFIG_FILE="$HOME/.webinitor/config.json"
DOMAIN="$1"

if [ -z "$DOMAIN" ]; then
  jq -n '{"error":"domain argument required"}'
  exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
  jq -n '{"error":"no config file — run /webinitor setup"}'
  exit 1
fi

KEY=$(jq -r '.godaddy.api_key // empty' "$CONFIG_FILE")
SECRET=$(jq -r '.godaddy.api_secret // empty' "$CONFIG_FILE")
ENV=$(jq -r '.godaddy.environment // "production"' "$CONFIG_FILE")

if [ -z "$KEY" ] || [ -z "$SECRET" ]; then
  jq -n '{"error":"GoDaddy API not configured"}'
  exit 1
fi

if [ "$ENV" = "ote" ]; then
  BASE_URL="https://api.ote-godaddy.com"
else
  BASE_URL="https://api.godaddy.com"
fi

RESPONSE=$(curl -s -w "\n%{http_code}" \
  -H "Authorization: sso-key ${KEY}:${SECRET}" \
  "${BASE_URL}/v1/domains/${DOMAIN}" 2>/dev/null)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
  jq -n --arg domain "$DOMAIN" --arg code "$HTTP_CODE" \
    '{"error":"Failed to lookup domain "+$domain+": HTTP "+$code}'
  exit 1
fi

NAMESERVERS=$(echo "$BODY" | jq -c '.nameServers // []')
NS_STRING=$(echo "$NAMESERVERS" | jq -r '.[]' | tr '\n' ' ')

PROVIDER="unknown"
if echo "$NS_STRING" | grep -qi "cloudflare"; then
  PROVIDER="cloudflare"
elif echo "$NS_STRING" | grep -qi "domaincontrol"; then
  PROVIDER="godaddy"
fi

jq -n --arg domain "$DOMAIN" --arg provider "$PROVIDER" --argjson ns "$NAMESERVERS" \
  '{"domain":$domain,"provider":$provider,"nameservers":$ns}'
