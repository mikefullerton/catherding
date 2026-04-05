# Webinitor v2.0.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add domain portfolio management, DNS record management (auto-routing between GoDaddy/Cloudflare), and an end-to-end connect workflow to the webinitor plugin.

**Architecture:** Seven new bash scripts handle API calls (GoDaddy REST, Cloudflare REST). The SKILL.md orchestrates interactive flows via AskUserQuestion. Config grows a `cloudflare` section for API token + account_id. DNS operations auto-detect provider by checking nameservers.

**Tech Stack:** Bash, curl, jq, GoDaddy REST API v1, Cloudflare API v4, Railway CLI

**Spec:** `docs/superpowers/specs/2026-04-05-webinitor-v2-design.md`

---

### Task 1: Cloudflare API Configuration Script

**Files:**
- Create: `plugins/webinitor/skills/webinitor/references/configure-cloudflare.sh`

- [ ] **Step 1: Create configure-cloudflare.sh**

```bash
#!/bin/bash
# configure-cloudflare.sh — manage Cloudflare API token
# Usage:
#   configure-cloudflare.sh get           — show masked token + account_id
#   configure-cloudflare.sh set <token>   — save token, auto-fetch account_id, test
#   configure-cloudflare.sh test          — verify token works
# Output: JSON

CONFIG_DIR="$HOME/.webinitor"
CONFIG_FILE="$CONFIG_DIR/config.json"
ACTION="$1"

ensure_config() {
  if [ ! -d "$CONFIG_DIR" ]; then
    mkdir -p "$CONFIG_DIR"
    chmod 700 "$CONFIG_DIR"
  fi
  if [ ! -f "$CONFIG_FILE" ]; then
    cat > "$CONFIG_FILE" <<'DEFAULTS'
{
  "godaddy": {
    "api_key": "",
    "api_secret": "",
    "environment": "production"
  },
  "cloudflare": {
    "api_token": "",
    "account_id": ""
  },
  "preferences": {
    "install_method": "brew"
  }
}
DEFAULTS
    chmod 600 "$CONFIG_FILE"
  fi
  # Ensure cloudflare section exists in existing config
  if ! jq -e '.cloudflare' "$CONFIG_FILE" >/dev/null 2>&1; then
    jq '.cloudflare = {"api_token":"","account_id":""}' \
      "$CONFIG_FILE" > "${CONFIG_FILE}.tmp" && mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
    chmod 600 "$CONFIG_FILE"
  fi
}

case "$ACTION" in
  get)
    if [ ! -f "$CONFIG_FILE" ]; then
      jq -n '{"configured":false}'
      exit 0
    fi
    TOKEN=$(jq -r '.cloudflare.api_token // empty' "$CONFIG_FILE")
    ACCOUNT_ID=$(jq -r '.cloudflare.account_id // empty' "$CONFIG_FILE")
    if [ -n "$TOKEN" ] && [ "$TOKEN" != "" ]; then
      MASKED="${TOKEN:0:4}...${TOKEN: -4}"
      jq -n --arg token "$MASKED" --arg aid "$ACCOUNT_ID" \
        '{"configured":true,"api_token":$token,"account_id":$aid}'
    else
      jq -n '{"configured":false}'
    fi
    ;;

  set)
    TOKEN="$2"
    ensure_config
    # Test the token first
    RESPONSE=$(curl -s -H "Authorization: Bearer ${TOKEN}" \
      "https://api.cloudflare.com/client/v4/zones?per_page=1" 2>/dev/null)
    SUCCESS=$(echo "$RESPONSE" | jq -r '.success' 2>/dev/null)
    if [ "$SUCCESS" != "true" ]; then
      ERROR=$(echo "$RESPONSE" | jq -r '.errors[0].message // "unknown error"' 2>/dev/null)
      jq -n --arg err "$ERROR" '{"status":"failed","error":$err}'
      exit 0
    fi
    # Fetch account_id
    ACCT_RESPONSE=$(curl -s -H "Authorization: Bearer ${TOKEN}" \
      "https://api.cloudflare.com/client/v4/accounts?per_page=1" 2>/dev/null)
    ACCOUNT_ID=$(echo "$ACCT_RESPONSE" | jq -r '.result[0].id // empty' 2>/dev/null)
    ACCOUNT_NAME=$(echo "$ACCT_RESPONSE" | jq -r '.result[0].name // empty' 2>/dev/null)
    # Save token and account_id
    jq --arg token "$TOKEN" --arg aid "$ACCOUNT_ID" \
      '.cloudflare.api_token = $token | .cloudflare.account_id = $aid' \
      "$CONFIG_FILE" > "${CONFIG_FILE}.tmp" && mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
    chmod 600 "$CONFIG_FILE"
    ZONE_COUNT=$(echo "$RESPONSE" | jq -r '.result_info.total_count // 0' 2>/dev/null)
    jq -n --arg aid "$ACCOUNT_ID" --arg name "$ACCOUNT_NAME" --argjson zones "$ZONE_COUNT" \
      '{"status":"saved","account_id":$aid,"account_name":$name,"zones":$zones}'
    ;;

  test)
    if [ ! -f "$CONFIG_FILE" ]; then
      jq -n '{"status":"failed","error":"no config file"}'
      exit 0
    fi
    TOKEN=$(jq -r '.cloudflare.api_token // empty' "$CONFIG_FILE")
    if [ -z "$TOKEN" ]; then
      jq -n '{"status":"failed","error":"no api token configured"}'
      exit 0
    fi
    RESPONSE=$(curl -s -H "Authorization: Bearer ${TOKEN}" \
      "https://api.cloudflare.com/client/v4/zones?per_page=1" 2>/dev/null)
    SUCCESS=$(echo "$RESPONSE" | jq -r '.success' 2>/dev/null)
    if [ "$SUCCESS" = "true" ]; then
      ZONE_COUNT=$(echo "$RESPONSE" | jq -r '.result_info.total_count // 0' 2>/dev/null)
      jq -n --argjson zones "$ZONE_COUNT" '{"status":"ok","zones":$zones}'
    else
      ERROR=$(echo "$RESPONSE" | jq -r '.errors[0].message // "unknown error"' 2>/dev/null)
      jq -n --arg err "$ERROR" '{"status":"failed","error":$err}'
    fi
    ;;

  *)
    jq -n '{"error":"usage: configure-cloudflare.sh [get|set|test]"}'
    exit 1
    ;;
esac
```

- [ ] **Step 2: Make executable**

Run: `chmod +x plugins/webinitor/skills/webinitor/references/configure-cloudflare.sh`

- [ ] **Step 3: Commit**

```bash
git add plugins/webinitor/skills/webinitor/references/configure-cloudflare.sh
git commit -m "feat(webinitor): add Cloudflare API token configuration script"
```

---

### Task 2: Update Config Defaults and Auth Checks for Cloudflare API

**Files:**
- Modify: `plugins/webinitor/skills/webinitor/references/config-defaults.json`
- Modify: `plugins/webinitor/skills/webinitor/references/configure-godaddy.sh:14-33` (ensure_config function)
- Modify: `plugins/webinitor/skills/webinitor/references/check-auth.sh:10-22` (cloudflare case)
- Modify: `plugins/webinitor/skills/webinitor/references/status-all.sh`

- [ ] **Step 1: Update config-defaults.json to include cloudflare section**

Replace full contents of `config-defaults.json`:

```json
{
  "godaddy": {
    "api_key": "",
    "api_secret": "",
    "environment": "production"
  },
  "cloudflare": {
    "api_token": "",
    "account_id": ""
  },
  "preferences": {
    "install_method": "brew"
  }
}
```

- [ ] **Step 2: Update configure-godaddy.sh ensure_config to include cloudflare section**

In `configure-godaddy.sh`, update the DEFAULTS heredoc (lines 20-30) to include the cloudflare section:

```bash
    cat > "$CONFIG_FILE" <<'DEFAULTS'
{
  "godaddy": {
    "api_key": "",
    "api_secret": "",
    "environment": "production"
  },
  "cloudflare": {
    "api_token": "",
    "account_id": ""
  },
  "preferences": {
    "install_method": "brew"
  }
}
DEFAULTS
```

- [ ] **Step 3: Add cloudflare_api case to check-auth.sh**

Add a new case `cloudflare_api)` after the existing `cloudflare)` case (which checks wrangler CLI). Insert before the `railway)` case:

```bash
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
```

- [ ] **Step 4: Update status-all.sh to include Cloudflare API status**

Replace full contents of `status-all.sh`:

```bash
#!/bin/bash
# status-all.sh — unified status check for all webinitor services
# Usage: status-all.sh
# Output: JSON with CLI install status and auth status for all services

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

CF_CLI=$(bash "$SCRIPT_DIR/check-cli.sh" wrangler --version)
RW_CLI=$(bash "$SCRIPT_DIR/check-cli.sh" railway version)

CF_AUTH=$(bash "$SCRIPT_DIR/check-auth.sh" cloudflare)
CF_API=$(bash "$SCRIPT_DIR/check-auth.sh" cloudflare_api)
RW_AUTH=$(bash "$SCRIPT_DIR/check-auth.sh" railway)
GD_AUTH=$(bash "$SCRIPT_DIR/check-auth.sh" godaddy)

jq -n \
  --argjson cf_cli "$CF_CLI" \
  --argjson rw_cli "$RW_CLI" \
  --argjson cf_auth "$CF_AUTH" \
  --argjson cf_api "$CF_API" \
  --argjson rw_auth "$RW_AUTH" \
  --argjson gd_auth "$GD_AUTH" \
  '{
    "cloudflare": {"cli": $cf_cli, "auth": $cf_auth, "api": $cf_api},
    "railway": {"cli": $rw_cli, "auth": $rw_auth},
    "godaddy": {"auth": $gd_auth}
  }'
```

- [ ] **Step 5: Commit**

```bash
git add plugins/webinitor/skills/webinitor/references/config-defaults.json \
  plugins/webinitor/skills/webinitor/references/configure-godaddy.sh \
  plugins/webinitor/skills/webinitor/references/check-auth.sh \
  plugins/webinitor/skills/webinitor/references/status-all.sh
git commit -m "feat(webinitor): add Cloudflare API auth checks and update config defaults"
```

---

### Task 3: GoDaddy Domains Script

**Files:**
- Create: `plugins/webinitor/skills/webinitor/references/godaddy-domains.sh`

- [ ] **Step 1: Create godaddy-domains.sh**

```bash
#!/bin/bash
# godaddy-domains.sh — GoDaddy domain portfolio management
# Usage:
#   godaddy-domains.sh list [--status STATUS] [--expiring]
#   godaddy-domains.sh search <query>
#   godaddy-domains.sh info <domain>
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
    while [ $# -gt 0 ]; do
      case "$1" in
        --status) STATUS_FILTER="$2"; shift 2 ;;
        --expiring) EXPIRING=true; shift ;;
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
    if [ "$EXPIRING" = true ]; then
      CUTOFF=$(date -v+30d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -d "+30 days" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)
      echo "$BODY" | jq --arg cutoff "$CUTOFF" '[.[] | select(.expires <= $cutoff)]'
    else
      echo "$BODY" | jq '.'
    fi
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
```

- [ ] **Step 2: Make executable**

Run: `chmod +x plugins/webinitor/skills/webinitor/references/godaddy-domains.sh`

- [ ] **Step 3: Commit**

```bash
git add plugins/webinitor/skills/webinitor/references/godaddy-domains.sh
git commit -m "feat(webinitor): add GoDaddy domain listing, search, and info script"
```

---

### Task 4: GoDaddy Nameservers Script

**Files:**
- Create: `plugins/webinitor/skills/webinitor/references/godaddy-nameservers.sh`

- [ ] **Step 1: Create godaddy-nameservers.sh**

```bash
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
```

- [ ] **Step 2: Make executable**

Run: `chmod +x plugins/webinitor/skills/webinitor/references/godaddy-nameservers.sh`

- [ ] **Step 3: Commit**

```bash
git add plugins/webinitor/skills/webinitor/references/godaddy-nameservers.sh
git commit -m "feat(webinitor): add GoDaddy nameserver get/set script"
```

---

### Task 5: DNS Provider Detection Script

**Files:**
- Create: `plugins/webinitor/skills/webinitor/references/dns-detect.sh`

- [ ] **Step 1: Create dns-detect.sh**

```bash
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
```

- [ ] **Step 2: Make executable**

Run: `chmod +x plugins/webinitor/skills/webinitor/references/dns-detect.sh`

- [ ] **Step 3: Commit**

```bash
git add plugins/webinitor/skills/webinitor/references/dns-detect.sh
git commit -m "feat(webinitor): add DNS provider detection script"
```

---

### Task 6: GoDaddy DNS CRUD Script

**Files:**
- Create: `plugins/webinitor/skills/webinitor/references/dns-godaddy.sh`

- [ ] **Step 1: Create dns-godaddy.sh**

```bash
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
```

- [ ] **Step 2: Make executable**

Run: `chmod +x plugins/webinitor/skills/webinitor/references/dns-godaddy.sh`

- [ ] **Step 3: Commit**

```bash
git add plugins/webinitor/skills/webinitor/references/dns-godaddy.sh
git commit -m "feat(webinitor): add GoDaddy DNS CRUD script"
```

---

### Task 7: Cloudflare DNS CRUD Script

**Files:**
- Create: `plugins/webinitor/skills/webinitor/references/dns-cloudflare.sh`

- [ ] **Step 1: Create dns-cloudflare.sh**

```bash
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
```

- [ ] **Step 2: Make executable**

Run: `chmod +x plugins/webinitor/skills/webinitor/references/dns-cloudflare.sh`

- [ ] **Step 3: Commit**

```bash
git add plugins/webinitor/skills/webinitor/references/dns-cloudflare.sh
git commit -m "feat(webinitor): add Cloudflare DNS CRUD script"
```

---

### Task 8: Cloudflare Zones Script

**Files:**
- Create: `plugins/webinitor/skills/webinitor/references/cloudflare-zones.sh`

- [ ] **Step 1: Create cloudflare-zones.sh**

```bash
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
```

- [ ] **Step 2: Make executable**

Run: `chmod +x plugins/webinitor/skills/webinitor/references/cloudflare-zones.sh`

- [ ] **Step 3: Commit**

```bash
git add plugins/webinitor/skills/webinitor/references/cloudflare-zones.sh
git commit -m "feat(webinitor): add Cloudflare zone management script"
```

---

### Task 9: Update SKILL.md — Add Domains, DNS, and Connect Sections

**Files:**
- Modify: `plugins/webinitor/skills/webinitor/SKILL.md`

This is the largest task. The SKILL.md needs:
1. Version bump to 2.0.0
2. Updated routing table
3. New sections: Domains, DNS, Connect, Setup Cloudflare API, Configure Cloudflare
4. Updated Status section (Cloudflare API line)
5. Updated Help section

- [ ] **Step 1: Bump version in frontmatter and header**

Change line 4 from `version: "1.0.0"` to `version: "2.0.0"`.
Change line 5 from `argument-hint: "[status|setup|configure|--help|--version]"` to `argument-hint: "[status|setup|configure|domains|dns|connect|--help|--version]"`.
Change line 10 from `# Webinitor v1.0.0` to `# Webinitor v2.0.0`.
Update all instances of `v1.0.0` to `v2.0.0` (lines 20, 23, and in the Help section at the end).

- [ ] **Step 2: Update routing table (lines 29-40)**

Replace the routing table with:

```markdown
## Route by argument

| `$ARGUMENTS` | Action |
|---|---|
| `status` or empty | Go to **Status** |
| `setup` | Go to **Setup All** |
| `setup cloudflare` | Go to **Setup Cloudflare** |
| `setup railway` | Go to **Setup Railway** |
| `setup godaddy` | Go to **Setup GoDaddy** |
| `configure` | Go to **Configure** |
| `configure godaddy` | Go to **Configure GoDaddy** |
| `configure cloudflare` | Go to **Configure Cloudflare** |
| `domains` or `domains list` | Go to **Domains List** |
| `domains list --status <S>` | Go to **Domains List** (with status filter) |
| `domains list --expiring` | Go to **Domains List** (expiring filter) |
| `domains search <query>` | Go to **Domains Search** |
| `domains info <domain>` | Go to **Domains Info** |
| `dns list <domain>` | Go to **DNS List** |
| `dns add <domain>` | Go to **DNS Add** |
| `dns update <domain>` | Go to **DNS Update** |
| `dns delete <domain>` | Go to **DNS Delete** |
| `connect <domain>` | Go to **Connect** |
| `--help` | Go to **Help** |
| `--version` | Print version (handled in Startup) |
| anything else | Print: "Usage: /webinitor [status\|setup\|configure\|domains\|dns\|connect\|--help\|--version]" and stop |
```

- [ ] **Step 3: Update Status section to include Cloudflare API line**

In the Status section's "Step 2: Format and display", update the format to include:

```
=== WEBINITOR STATUS ===

Cloudflare (Wrangler)
  CLI:  <installed (vX.X.X)> or <not installed>
  Auth: <authenticated (account-name)> or <not authenticated — reason>
  API:  <configured (token: abcd...efgh)> or <not configured — reason>

Railway
  CLI:  <installed (vX.X.X)> or <not installed>
  Auth: <authenticated (account-name)> or <not authenticated — reason>

GoDaddy (API)
  Env:  <production> or <ote>
  Auth: <configured (key: abcd...efgh)> or <not configured — reason>
```

And update the Issues section to include:
```
  - Cloudflare API not configured → /webinitor setup cloudflare
```

- [ ] **Step 4: Add Setup Cloudflare API section after Setup Cloudflare Step 4**

Insert after the existing Setup Cloudflare section (after line 164), before Setup Railway:

```markdown
### Step 5: Check Cloudflare API token

```bash
bash ${CLAUDE_SKILL_DIR}/references/check-auth.sh cloudflare_api
```

If authenticated, print: "Cloudflare API: configured." and stop this section.

### Step 6: Guide API token creation

Print:
> Cloudflare API token is needed for DNS and zone management.
>
> To create a token:
> 1. Go to https://dash.cloudflare.com/profile/api-tokens
> 2. Click "Create Token"
> 3. Use the "Edit zone DNS" template, or create a custom token with:
>    - **Zone:Zone:Read** and **Zone:DNS:Edit** permissions
> 4. Copy the token — it's only shown once

Use AskUserQuestion:
- Question: "Enter your Cloudflare API token (or type 'skip' to skip):"
- Option 1: "Skip" — Skip Cloudflare API setup
- (User will type their token in "Other")

If "Skip", print "Cloudflare API setup skipped." and stop this section.

### Step 7: Save and test API token

```bash
bash ${CLAUDE_SKILL_DIR}/references/configure-cloudflare.sh set <TOKEN>
```

Parse the JSON output:
- If `status` is `saved`, print: "Cloudflare API configured. Account: <account_name>. Zones: <zones>."
- If `status` is `failed`, print the error and use AskUserQuestion:
  - "Cloudflare API token test failed. What would you like to do?"
  - Option 1: "Re-enter token" — Go back to Step 6
  - Option 2: "Skip for now"
```

- [ ] **Step 5: Add Configure Cloudflare section after Configure GoDaddy Environment**

Insert before the Help section:

```markdown
---

## Configure Cloudflare

### Step 1: Show current config

```bash
bash ${CLAUDE_SKILL_DIR}/references/configure-cloudflare.sh get
```

Print the current (masked) configuration.

### Step 2: Choose action

Use AskUserQuestion:
- Question: "What would you like to do?"
- Option 1: "Update API token" — Collect new token (same flow as Setup Cloudflare Step 6-7)
- Option 2: "Test connection" — Run `configure-cloudflare.sh test` and report
- Option 3: "Done" — Stop

After each action, loop back to Step 1 to show updated config.
```

Also update the Configure section's AskUserQuestion to add "Cloudflare API token" as an option:

```markdown
Use AskUserQuestion:
- Question: "What would you like to configure?"
- Option 1: "GoDaddy API credentials" — Go to **Configure GoDaddy**
- Option 2: "Cloudflare API token" — Go to **Configure Cloudflare**
- Option 3: "GoDaddy environment (production/ote)" — Go to **Configure GoDaddy Environment**
- Option 4: "Done" — Stop
```

- [ ] **Step 6: Add Domains sections before DNS sections**

Insert after Configure Cloudflare, before Help:

```markdown
---

## Domains List

### Step 1: Fetch domains

```bash
bash ${CLAUDE_SKILL_DIR}/references/godaddy-domains.sh list
```

If `$ARGUMENTS` contains `--status`, pass the status filter:
```bash
bash ${CLAUDE_SKILL_DIR}/references/godaddy-domains.sh list --status <STATUS>
```

If `$ARGUMENTS` contains `--expiring`:
```bash
bash ${CLAUDE_SKILL_DIR}/references/godaddy-domains.sh list --expiring
```

### Step 2: Format and display

Parse the JSON array and print a table:

```
Domain                    Status    Expires      Auto-Renew  Privacy  Nameservers
example.com               ACTIVE    2027-03-15   on          on       Cloudflare
mysite.org                ACTIVE    2026-12-01   on          off      GoDaddy
oldsite.net               ACTIVE    2026-04-20   off         on       GoDaddy
```

Nameserver column logic:
- If any nameserver contains "cloudflare" → "Cloudflare"
- If nameservers contain "domaincontrol" → "GoDaddy"
- Otherwise → "Other"

Print total count at the bottom: "Showing N domain(s)."

---

## Domains Search

### Step 1: Search domains

Extract the query from `$ARGUMENTS` (the word after `domains search`).

```bash
bash ${CLAUDE_SKILL_DIR}/references/godaddy-domains.sh search <query>
```

### Step 2: Format and display

Same table format as Domains List. Print: "Found N domain(s) matching '<query>'."

---

## Domains Info

### Step 1: Get domain info

Extract the domain from `$ARGUMENTS` (the word after `domains info`).

```bash
bash ${CLAUDE_SKILL_DIR}/references/godaddy-domains.sh info <domain>
```

### Step 2: Format and display

Print detailed info:

```
=== <domain> ===

Status:       ACTIVE
Created:      2020-01-15
Expires:      2027-03-15
Auto-Renew:   on
Privacy:      on
Locked:       true

Nameservers:
  - ada.ns.cloudflare.com
  - bob.ns.cloudflare.com

DNS Provider: Cloudflare
```
```

- [ ] **Step 7: Add DNS sections**

Insert after Domains Info, before Help:

```markdown
---

## DNS List

### Step 1: Detect provider

Extract the domain from `$ARGUMENTS` (the word after `dns list`).

```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-detect.sh <domain>
```

Parse the JSON. Print: "DNS provider: <Provider> (nameservers: <ns1>, <ns2>)"

### Step 2: Fetch records

If provider is `cloudflare`:
```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-cloudflare.sh list <domain>
```

If provider is `godaddy`:
```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-godaddy.sh list <domain>
```

If provider is `unknown`, use AskUserQuestion:
- "Nameservers don't match GoDaddy or Cloudflare. Which provider manages DNS for this domain?"
- Option 1: "Cloudflare"
- Option 2: "GoDaddy"
- Option 3: "Cancel"

### Step 3: Format and display

For Cloudflare records, print:

```
#   Type    Name              Value                    TTL     Proxied
1   A       example.com       192.168.1.1              auto    yes
2   CNAME   www               example.com              auto    yes
3   MX      example.com       mail.example.com         3600    -
4   TXT     example.com       v=spf1 include:...       auto    -
```

For GoDaddy records, print (no Proxied column, no # id):

```
#   Type    Name    Value                    TTL
1   A       @       192.168.1.1              3600
2   CNAME   www     example.com              3600
3   MX      @       mail.example.com         3600
```

Print total: "N record(s) for <domain>."

---

## DNS Add

### Step 1: Detect provider

Extract the domain from `$ARGUMENTS`.

```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-detect.sh <domain>
```

Print the detected provider.

### Step 2: Collect record details

Use AskUserQuestion:
- Question: "What type of DNS record?"
- Options: "A", "AAAA", "CNAME", "MX", "TXT"

Use AskUserQuestion:
- Question: "Record name (e.g., @, www, mail, subdomain):"
- (User types in "Other")

Use AskUserQuestion:
- Question: "Record value (e.g., IP address, hostname, text):"
- (User types in "Other")

Use AskUserQuestion:
- Question: "TTL (time to live)?"
- Option 1: "Auto (Recommended)" — Use 1 for Cloudflare, 3600 for GoDaddy
- Option 2: "3600 (1 hour)"
- Option 3: "86400 (1 day)"

If provider is `cloudflare`:
Use AskUserQuestion:
- Question: "Proxy through Cloudflare? (orange cloud)"
- Option 1: "Yes (Recommended for web traffic)" — proxied=true
- Option 2: "No (DNS only)" — proxied=false

### Step 3: Confirm and create

Print a summary of what will be created. Use AskUserQuestion to confirm:
- "Create this DNS record?"
- Option 1: "Yes, create it"
- Option 2: "Cancel"

If confirmed, for Cloudflare:
```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-cloudflare.sh add <domain> <type> <name> <value> <ttl> <proxied>
```

For GoDaddy:
```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-godaddy.sh add <domain> <type> <name> <value> <ttl>
```

Report the result.

---

## DNS Update

### Step 1: Detect provider and list records

Extract the domain from `$ARGUMENTS`.

```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-detect.sh <domain>
```

Print the detected provider. Then list records (same as DNS List Step 2-3).

### Step 2: Select record

Use AskUserQuestion:
- Question: "Which record number to update?"
- (User types the number in "Other")

### Step 3: Collect new value

Show the current record values. Use AskUserQuestion:
- Question: "New value for this record:"
- (User types in "Other")

Optionally ask about TTL and proxied changes.

### Step 4: Confirm and update

Print a summary showing old → new. Use AskUserQuestion to confirm.

If confirmed, for Cloudflare (use record id from the list):
```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-cloudflare.sh update <domain> <record_id> <value> <ttl> <proxied>
```

For GoDaddy (use type and name):
```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-godaddy.sh update <domain> <type> <name> <value> <ttl>
```

Report the result.

---

## DNS Delete

### Step 1: Detect provider and list records

Extract the domain from `$ARGUMENTS`.

```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-detect.sh <domain>
```

Print the detected provider. Then list records (same as DNS List Step 2-3).

### Step 2: Select record

Use AskUserQuestion:
- Question: "Which record number to delete?"
- (User types the number in "Other")

### Step 3: Confirm deletion

Show the record that will be deleted. Use AskUserQuestion:
- "Delete this DNS record? This cannot be undone."
- Option 1: "Yes, delete it"
- Option 2: "Cancel"

If confirmed, for Cloudflare:
```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-cloudflare.sh delete <domain> <record_id>
```

For GoDaddy:
```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-godaddy.sh delete <domain> <type> <name> <value>
```

Report the result.
```

- [ ] **Step 8: Add Connect section**

Insert after DNS Delete, before Help:

```markdown
---

## Connect

End-to-end workflow: GoDaddy domain → Cloudflare zone → Railway custom domain.

Extract the domain from `$ARGUMENTS` (the word after `connect`).

### Step 1: Verify domain ownership

```bash
bash ${CLAUDE_SKILL_DIR}/references/godaddy-domains.sh info <domain>
```

If the request fails, print the error and stop.

Print: "Domain: <domain> — Status: <status>, Nameservers: <ns list>"

### Step 2: Check/create Cloudflare zone

```bash
bash ${CLAUDE_SKILL_DIR}/references/cloudflare-zones.sh get <domain>
```

If `found` is true:
- Print: "Cloudflare zone exists. Status: <status>. Nameservers: <ns1>, <ns2>"
- Skip to Step 3.

If `found` is false:
Use AskUserQuestion:
- "Domain <domain> has no Cloudflare zone. Create one?"
- Option 1: "Yes, create zone"
- Option 2: "Skip Cloudflare" — Stop the connect workflow

If yes:
```bash
bash ${CLAUDE_SKILL_DIR}/references/cloudflare-zones.sh create <domain>
```

Print the result including assigned nameservers.

### Step 3: Update GoDaddy nameservers

Get the Cloudflare-assigned nameservers from the zone (from Step 2 output).
Get the current GoDaddy nameservers:

```bash
bash ${CLAUDE_SKILL_DIR}/references/godaddy-nameservers.sh get <domain>
```

Compare. If nameservers already match Cloudflare's, print: "Nameservers already point to Cloudflare. Skipping." and go to Step 4.

If different, print the change clearly:
```
Current nameservers:  ns1.domaincontrol.com, ns2.domaincontrol.com
New nameservers:      ada.ns.cloudflare.com, bob.ns.cloudflare.com
```

Use AskUserQuestion:
- "Update nameservers to Cloudflare? This changes live DNS and may take up to 24h to propagate."
- Option 1: "Yes, update nameservers"
- Option 2: "Skip" — Continue without changing nameservers

If yes:
```bash
bash ${CLAUDE_SKILL_DIR}/references/godaddy-nameservers.sh set <domain> <cf_ns1> <cf_ns2>
```

Report the result.

### Step 4: Check Cloudflare activation

```bash
bash ${CLAUDE_SKILL_DIR}/references/cloudflare-zones.sh check <domain>
```

If status is `active`: Print: "Cloudflare zone is active."
If status is `pending`: Print: "Zone is pending activation. Nameserver changes can take up to 24 hours to propagate. Check back with `/webinitor dns list <domain>` later."

Use AskUserQuestion:
- "Continue to Railway custom domain setup?"
- Option 1: "Yes, configure Railway"
- Option 2: "Done" — Print summary and stop

### Step 5: Configure Railway custom domain

Check if current directory is linked to a Railway project:

```bash
railway status --json 2>/dev/null
```

If linked, print: "Detected Railway project: <project_name>, service: <service_name>"
Use AskUserQuestion:
- "Add <domain> as a custom domain to this Railway service?"
- Option 1: "Yes, use this project"
- Option 2: "Different project" — Ask user to `railway link` in another directory
- Option 3: "Skip Railway" — Go to Step 6

If not linked:
Print: "No Railway project linked in this directory."
Use AskUserQuestion:
- "Would you like to link a Railway project first?"
- Option 1: "Yes" — Tell user to type `! railway link` then check again
- Option 2: "Skip Railway" — Go to Step 6

Once a project is linked, add the custom domain:
```bash
railway domain
```

Note: `railway domain` is interactive. Tell the user: "Type `! railway domain` to add your custom domain. Enter `<domain>` when prompted."

After the domain is added, Railway provides a CNAME target (typically `<service>.up.railway.app`). Create the DNS record in Cloudflare:

```bash
bash ${CLAUDE_SKILL_DIR}/references/dns-cloudflare.sh add <domain> CNAME <name> <railway-target> 1 true
```

### Step 6: Summary

Print a final summary:

```
=== CONNECT SUMMARY: <domain> ===

GoDaddy:    Domain verified ✓
Cloudflare: Zone <active|pending> ✓
            Nameservers: <ns1>, <ns2>
Railway:    Custom domain <configured|skipped>

Next steps:
  - <any pending items, e.g., "Wait for Cloudflare activation">
  - Use /webinitor dns list <domain> to verify DNS records
```
```

- [ ] **Step 9: Update Help section**

Replace the Help section's content with:

```markdown
## Help

Print:

```
Webinitor v2.0.0

Website infrastructure management — setup, status, and configuration
for Cloudflare (Wrangler + API), Railway, and GoDaddy.

Usage: /webinitor [command]

Commands:
  status                   Show status of all services (default)
  setup                    Interactive setup for all services
  setup cloudflare         Setup Cloudflare (CLI + API token)
  setup railway            Setup Railway CLI
  setup godaddy            Setup GoDaddy API credentials
  configure                Edit service configuration
  configure godaddy        Edit GoDaddy API credentials
  configure cloudflare     Edit Cloudflare API token
  domains                  List all domains
  domains list             List domains (--status, --expiring)
  domains search <query>   Search domains by name
  domains info <domain>    Show detailed domain info
  dns list <domain>        List DNS records (auto-detects provider)
  dns add <domain>         Add a DNS record
  dns update <domain>      Update a DNS record
  dns delete <domain>      Delete a DNS record
  connect <domain>         GoDaddy → Cloudflare → Railway workflow
  --help                   Show this help
  --version                Show version

Services:
  Cloudflare — DNS, zones, Workers via API + Wrangler CLI
  Railway    — App hosting and databases via Railway CLI
  GoDaddy    — Domain portfolio management via REST API

Config: ~/.webinitor/config.json (mode 600)
```
```

- [ ] **Step 10: Commit SKILL.md**

```bash
git add plugins/webinitor/skills/webinitor/SKILL.md
git commit -m "feat(webinitor): add domains, dns, and connect sections to SKILL.md (v2.0.0)"
```

---

### Task 10: Update Plugin Metadata and README

**Files:**
- Modify: `plugins/webinitor/.claude-plugin/plugin.json`
- Modify: `plugins/webinitor/README.md`

- [ ] **Step 1: Bump plugin.json version**

Change `"version": "1.0.0"` to `"version": "2.0.0"` in `plugin.json`.

- [ ] **Step 2: Update README.md**

Replace full contents of `README.md`:

```markdown
# Webinitor

Website infrastructure management plugin for Claude Code. Manages setup, status, configuration, domain portfolio, DNS records, and end-to-end workflows for three services:

- **Cloudflare** — DNS, zones, Workers via API + Wrangler CLI
- **Railway** — App hosting and databases via Railway CLI
- **GoDaddy** — Domain portfolio management via REST API

## Commands

| Command | Description |
|---------|-------------|
| `/webinitor` | Show status of all services |
| `/webinitor status` | Show status of all services |
| `/webinitor setup` | Interactive setup for all services |
| `/webinitor setup cloudflare` | Setup Cloudflare (CLI + API token) |
| `/webinitor setup railway` | Setup Railway CLI |
| `/webinitor setup godaddy` | Setup GoDaddy API credentials |
| `/webinitor configure` | Edit service configuration |
| `/webinitor configure godaddy` | Edit GoDaddy API credentials |
| `/webinitor configure cloudflare` | Edit Cloudflare API token |
| `/webinitor domains` | List all domains |
| `/webinitor domains list` | List domains (supports --status, --expiring) |
| `/webinitor domains search <query>` | Search domains by name |
| `/webinitor domains info <domain>` | Show detailed domain info |
| `/webinitor dns list <domain>` | List DNS records (auto-detects GoDaddy vs Cloudflare) |
| `/webinitor dns add <domain>` | Add a DNS record |
| `/webinitor dns update <domain>` | Update a DNS record |
| `/webinitor dns delete <domain>` | Delete a DNS record |
| `/webinitor connect <domain>` | End-to-end: GoDaddy → Cloudflare → Railway |
| `/webinitor --help` | Show help |
| `/webinitor --version` | Show version |

## Configuration

Credentials are stored at `~/.webinitor/config.json` with restricted permissions (directory mode 700, file mode 600):

- **GoDaddy**: API key + secret
- **Cloudflare**: API token + account ID (auto-fetched)
- **Railway**: Uses its own CLI auth (`railway login`)

## Installation

```bash
# From the cat-herding marketplace
claude plugin install webinitor@cat-herding

# Or load directly for development
claude --plugin-dir ./plugins/webinitor
```
```

- [ ] **Step 3: Commit**

```bash
git add plugins/webinitor/.claude-plugin/plugin.json plugins/webinitor/README.md
git commit -m "feat(webinitor): bump to v2.0.0, update README with new commands"
```

---

### Task 11: Verification

- [ ] **Step 1: Verify all scripts are executable**

Run: `ls -la plugins/webinitor/skills/webinitor/references/*.sh`

All `.sh` files should have executable permission. If any are missing, run:
```bash
chmod +x plugins/webinitor/skills/webinitor/references/*.sh
```

- [ ] **Step 2: Verify all files exist**

Run: `find plugins/webinitor -type f | sort`

Expected files (17 total):
```
plugins/webinitor/.claude-plugin/plugin.json
plugins/webinitor/README.md
plugins/webinitor/skills/webinitor/SKILL.md
plugins/webinitor/skills/webinitor/references/check-auth.sh
plugins/webinitor/skills/webinitor/references/check-cli.sh
plugins/webinitor/skills/webinitor/references/cloudflare-zones.sh
plugins/webinitor/skills/webinitor/references/config-defaults.json
plugins/webinitor/skills/webinitor/references/configure-cloudflare.sh
plugins/webinitor/skills/webinitor/references/configure-godaddy.sh
plugins/webinitor/skills/webinitor/references/dns-cloudflare.sh
plugins/webinitor/skills/webinitor/references/dns-detect.sh
plugins/webinitor/skills/webinitor/references/dns-godaddy.sh
plugins/webinitor/skills/webinitor/references/ensure-permissions.sh
plugins/webinitor/skills/webinitor/references/godaddy-domains.sh
plugins/webinitor/skills/webinitor/references/godaddy-nameservers.sh
plugins/webinitor/skills/webinitor/references/install-cli.sh
plugins/webinitor/skills/webinitor/references/status-all.sh
```

- [ ] **Step 3: Test with plugin loaded**

Run: `claude --plugin-dir ./plugins/webinitor`

Test these commands:
1. `/webinitor --version` → should print "webinitor v2.0.0"
2. `/webinitor --help` → should show all commands including domains, dns, connect
3. `/webinitor status` → should show Cloudflare API line in output

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A plugins/webinitor/
git commit -m "fix(webinitor): verification fixes"
```
