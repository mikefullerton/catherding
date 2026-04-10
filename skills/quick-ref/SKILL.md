---
name: quick-ref
version: "1.0.0"
description: "Generate a searchable quick-reference page and open it in the browser. Defaults to Claude Code slash commands. Pass a topic or preset (e.g. claude-flags) to generate a reference."
argument-hint: "[topic | claude-flags | help]"
allowed-tools: Read, Write, Bash(cp *), Bash(date *), Bash(python3 *), Glob, Grep
model: sonnet
---

## Help

If `$ARGUMENTS` is `help` or `--help`, respond with:

> **`/quick-ref [topic]`** -- Generate a searchable, dark-themed quick-reference page and open it in the browser.
>
> **No arguments**: generates a reference of all installed Claude Code `/` slash commands grouped by source marketplace and plugin.
>
> **Presets**:
> - `/quick-ref claude-flags` -- all CLI flags & env vars with live values from your environment
>
> **With a topic**: generates a reference page about that topic. Examples:
> - `/quick-ref git commands` -- common git commands
> - `/quick-ref keyboard shortcuts` -- Claude Code keyboard shortcuts
> - `/quick-ref HTTP status codes` -- HTTP status code reference
>
> The generated page includes:
> - Find with next/prev navigation (arrow keys, Enter)
> - Filter with `source:` and `section:` prefix support
> - Autocomplete history (shared between fields, persisted in localStorage)
> - Escape to clear, Tab to switch fields
> - Dark theme with teal accents

Then stop.

## Behavior

### Preset: `claude-flags`

If `$ARGUMENTS` is `claude-flags`:

1. Run the generator script to produce the HTML with live env var values:
   ```
   python3 ${CLAUDE_SKILL_DIR}/references/claude-flags-generator.py > ~/.local-server/sites/claude-flags.html
   ```
2. Tell the user the page is live at `http://localhost:2080/claude-flags.html`. Mention how many env vars are currently set vs unset.

The generator reads `claude-flags-template.html` (a static reference of all ~70 CLI flags and ~120 env vars), scans the current environment for each env var's value, and injects color-coded badges:
- **green** (`= value`) for set variables
- **amber** (`sk-a...xyz4`) for set sensitive variables (masked)
- **gray** (`not set`) for unset variables

Then stop — do not proceed to other sections.

### Default (no arguments): Claude Code slash commands

If `$ARGUMENTS` is empty or blank:

1. Read the system reminder in the current conversation to enumerate all available skills
2. For each skill, gather: command name, description, source plugin, source marketplace
3. Group skills by marketplace (h2) then by plugin (h3)
4. Generate the HTML page using the template below
5. Write to `~/.local-server/sites/slash-commands.html`

### Custom topic

If `$ARGUMENTS` contains a topic:

1. Use your knowledge to compile a useful quick-reference for that topic
2. Organize items into logical groups (h2) and sub-groups (h3)
3. Generate the HTML page using the template below
4. Slugify the topic (lowercase, spaces/special chars → hyphens, e.g. "HTTP Status Codes" → `http-status-codes`)
5. Write to `~/.local-server/sites/<slug>.html`

## HTML Template

Generate a complete HTML file following this exact structure and style. The page uses a dark theme with teal accents.

### Page structure

```
Title (h1): The reference topic
Subtitle (p.subtitle): A one-line description

Toolbar:
  Find row: text input + prev/next buttons + position indicator
  Help slug (right-aligned): keyboard shortcuts hint
  Filter row: text input
  Help slug (right-aligned): source:/section: hint
  Count line

Content:
  Groups (h2): top-level categories, optionally linked
    Sections (h3): sub-categories, optionally linked
      Items (div.skill): each with a code title, description paragraph, and find-badge span
```

### Data format

When generating content, each item needs these fields:

| Field | Element | Required | Description |
|-------|---------|----------|-------------|
| **title** | `<code>` or `<a><code>` | yes | The item name/command (e.g. `/brainstorm`, `git rebase`) |
| **description** | `<p>` | yes | One-line explanation of what it does |
| **link** | wrapping `<a>` on the code | no | URL to docs or source |
| **group** | `<h2>` | yes | Top-level category |
| **group_link** | `<a>` on h2 | no | URL for the group |
| **section** | `<h3>` | yes | Sub-category within a group |
| **section_link** | `<a>` on h3 | no | URL for the section |

Each h2 and h3 must contain a `<span class="find-badge"></span>`.
Each div.skill must contain a `<span class="find-badge"></span>`.

### Required CSS (copy exactly)

```css
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #111318; color: #d4d4d8; padding: 2rem; max-width: 960px; margin: 0 auto; line-height: 1.5; }
h1 { margin-bottom: 0.25rem; color: #e4e4e7; }
.subtitle { color: #71717a; margin-bottom: 2rem; }
.subtitle code { background: #1e1e24; padding: 0.1em 0.35em; border-radius: 3px; color: #22d3ee; }
h2 { position: relative; margin-top: 2.5rem; margin-bottom: 0.5rem; padding-bottom: 0.25rem; border-bottom: 2px solid #27272a; color: #e4e4e7; }
h2 a { color: inherit; text-decoration: none; }
h2 a:hover { text-decoration: underline; color: #22d3ee; }
h3 { position: relative; margin-top: 1.25rem; margin-bottom: 0.5rem; font-size: 1rem; color: #a1a1aa; }
h3 a { color: #22d3ee; text-decoration: none; }
h3 a:hover { text-decoration: underline; }
.skill { position: relative; margin-bottom: 0.75rem; padding: 0.6rem 1rem; background: #1a1a22; border-radius: 6px; border-left: 4px solid #0891b2; }
.skill code { font-size: 0.95rem; font-weight: 600; color: #22d3ee; }
.skill > a { text-decoration: none; }
.skill > a:hover code { text-decoration: underline; }
.skill p { margin-top: 0.2rem; font-size: 0.9rem; color: #a1a1aa; }
.skill p code { font-size: 0.85em; background: #27272a; padding: 0.1em 0.3em; border-radius: 3px; }
.toolbar { position: sticky; top: 0; background: #111318; padding: 1rem 0 0.5rem; z-index: 10; }
.toolbar .row { display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.4rem; }
.toolbar label { font-size: 0.8rem; font-weight: 600; color: #71717a; white-space: nowrap; min-width: 2.5rem; }
.toolbar input[type="text"] { flex: 1; padding: 0.5rem 1.8rem 0.5rem 0.75rem; font-size: 0.95rem; border: 2px solid #27272a; border-radius: 6px; outline: none; background: #1a1a22; color: #d4d4d8; }
.toolbar input[type="text"]::placeholder { color: #52525b; }
.toolbar input[type="text"]:focus { border-color: #0891b2; }
.toolbar .count { font-size: 0.8rem; color: #52525b; margin-top: 0.1rem; }
.help-slug { font-size: 0.75rem; color: #3f3f46; margin: -0.15rem 0 0.4rem 0; text-align: right; }
.help-slug kbd { background: #27272a; padding: 0.1em 0.35em; border-radius: 3px; font-family: inherit; font-size: 0.9em; color: #71717a; }
.help-slug code { background: #27272a; padding: 0.1em 0.35em; border-radius: 3px; font-size: 0.9em; color: #0891b2; }
.nav-btn { background: none; border: 2px solid #27272a; border-radius: 6px; padding: 0.4rem 0.6rem; cursor: pointer; font-size: 1rem; color: #71717a; line-height: 1; }
.nav-btn:hover { border-color: #0891b2; color: #22d3ee; }
.nav-btn:disabled { opacity: 0.3; cursor: default; border-color: #27272a; color: #3f3f46; }
.find-pos { font-size: 0.8rem; color: #52525b; min-width: 3.5rem; text-align: center; }
.hidden { display: none !important; }
.find-highlight { border-left-color: #f59e0b !important; box-shadow: 0 0 0 2px #f59e0b; }
h2.find-highlight, h3.find-highlight { border-radius: 4px; padding: 0.25rem 0.5rem; border-left: 4px solid #f59e0b; }
.find-badge { display: none; position: absolute; top: 0.5rem; right: 0.5rem; background: #f59e0b; color: #111318; font-size: 0.7rem; font-weight: 700; padding: 0.15rem 0.45rem; border-radius: 4px; }
.find-highlight .find-badge { display: block; }
mark.find-mark { background: #f59e0b; color: #111318; border-radius: 2px; padding: 0 0.1em; }
mark.filter-mark { background: #0891b2; color: #111318; border-radius: 2px; padding: 0 0.1em; }
.ac-wrap { position: relative; flex: 1; display: flex; }
.ac-wrap input { flex: 1; }
.clear-btn { display: none; position: absolute; right: 0.5rem; top: 50%; transform: translateY(-50%); background: none; border: none; color: #52525b; cursor: pointer; font-size: 1rem; line-height: 1; padding: 0.15rem; z-index: 2; }
.clear-btn:hover { color: #d4d4d8; }
.ac-wrap.has-value .clear-btn { display: block; }
.ac-list { display: none; position: absolute; top: 100%; left: 0; right: 0; max-height: 10rem; overflow-y: auto; background: #1a1a22; border: 2px solid #27272a; border-top: none; border-radius: 0 0 6px 6px; z-index: 20; }
.ac-list.open { display: block; }
.ac-list div { padding: 0.35rem 0.75rem; font-size: 0.9rem; color: #a1a1aa; cursor: pointer; }
.ac-list div:hover, .ac-list div.ac-active { background: #27272a; color: #22d3ee; }
footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #27272a; color: #3f3f46; font-size: 0.8rem; }
footer a { color: #0891b2; }
```

### Required toolbar HTML (copy exactly)

```html
<div class="toolbar">
  <div class="row">
    <label>Find</label>
    <div class="ac-wrap" id="find-wrap">
      <input type="text" id="find" placeholder="Search..." autofocus autocomplete="off">
      <button class="clear-btn" tabindex="-1" id="find-clear" title="Clear (Esc)">&times;</button>
      <div class="ac-list" id="find-ac"></div>
    </div>
    <button class="nav-btn" id="prev-btn" title="Previous (Up / Shift+Enter)" tabindex="-1" disabled>&larr;</button>
    <span class="find-pos" id="find-pos"></span>
    <button class="nav-btn" id="next-btn" title="Next (Down / Enter)" tabindex="-1" disabled>&rarr;</button>
  </div>
  <div class="help-slug"><kbd>&uarr;</kbd> <kbd>&darr;</kbd> prev / next &middot; <kbd>Enter</kbd> next &middot; <kbd>Shift+Enter</kbd> prev</div>
  <div class="row">
    <label>Filter</label>
    <div class="ac-wrap" id="filter-wrap">
      <input type="text" id="filter" placeholder="source: or section: or text" autocomplete="off">
      <button class="clear-btn" tabindex="-1" id="filter-clear" title="Clear (Esc)">&times;</button>
      <div class="ac-list" id="filter-ac"></div>
    </div>
  </div>
  <div class="help-slug"><code>source:</code> filter by group &middot; <code>section:</code> filter by section</div>
  <div class="count" id="count"></div>
</div>
```

### Required JavaScript

Copy the full JavaScript from `${CLAUDE_SKILL_DIR}/references/quick-ref.js` into a `<script>` tag at the end of the body. Read that file to get the script content.

### Item HTML pattern

For an item with a link:
```html
<div class="skill">
  <a href="URL" target="_blank" rel="noopener" tabindex="-1"><code>Title</code></a>
  <p>Description text here.</p>
  <span class="find-badge"></span>
</div>
```

For an item without a link:
```html
<div class="skill">
  <code>Title</code>
  <p>Description text here.</p>
  <span class="find-badge"></span>
</div>
```

### Section/group HTML pattern

With link: `<h2><a href="URL">Group Name</a><span class="find-badge"></span></h2>`
Without link: `<h2>Group Name<span class="find-badge"></span></h2>`

Same pattern for h3.

### Footer

```html
<footer>Generated YYYY-MM-DD with /quick-ref</footer>
```

## Output

1. Write the complete HTML to `~/.local-server/sites/<slug>.html` (slug derived from the topic/preset name)
2. Tell the user the page is live at `http://localhost:2080/<slug>.html` and briefly describe what's on it
