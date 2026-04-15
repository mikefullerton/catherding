# Zsh Completion Configuration

## Current Setup

Oh My Zsh default completion with one override (in `~/.zshrc`):

```zsh
bindkey -M menuselect '^I' send-break
```

**Tab exits the completion menu without accepting.** Navigate with arrow keys, accept with Enter.

## Why

Reduces friction between zsh and Claude Code's autocomplete UIs:

| Context | Navigate | Accept |
|---|---|---|
| zsh menuselect | arrows | Enter |
| Claude autocomplete | arrows | Tab |

Without this change, zsh used Tab to cycle through completions — the opposite of Claude's model where Tab accepts. The override aligns zsh's accept gesture (Enter) and removes Tab cycling, so arrows+Enter works consistently in both UIs.

## Default OMZ Completion Behavior (for reference)

- Case-insensitive matching
- `auto_menu`: first Tab shows list, second Tab enters menu
- `complete_in_word`: can complete from middle of a word
- `always_to_end`: cursor moves to end after completion
- Caching enabled
- `.` and `..` shown in directory completions
