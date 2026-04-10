# Claude Code Usage Limits, Pricing & Weekly Budget

Research conducted 2026-04-02.

## Plan Tiers

| Plan | Price | Usage Multiplier |
|------|-------|-----------------|
| Pro | $20/mo | 1x |
| Max 5x | $100/mo | 5x |
| Max 20x | $200/mo | 20x |

Usage is shared across Claude (web) and Claude Code — both count against the same limits.

## Rate Limit Windows

Two concurrent windows:

- **5-hour window**: Short-term burst limit. Resets every 5 hours.
- **7-day window**: Weekly budget. Reset day/time is per-account (not universal). Check your account's specific reset time in Settings > Usage.

Both windows have separate limits. Hitting either one throttles you.

## Weekly Reset Schedule

The 7-day reset is **per-account**, not a global day. It's tied to when your account's billing cycle started. There is no universal "Wednesday" reset — though individual accounts may happen to reset on Wednesday. Verify your reset time at claude.ai Settings > Usage.

## What the % Means

`rate_limits.seven_day.used_percentage` from the Claude Code status JSON is your consumption against your plan's weekly token cap. At 100% you're throttled unless you've enabled pay-as-you-go overage.

## Overage Pricing

When you exceed your weekly limit with pay-as-you-go enabled, you're charged at standard API rates:

| Model | Input (per M tokens) | Output (per M tokens) |
|-------|---------------------|----------------------|
| Opus 4.6 | $5.00 | $25.00 |
| Sonnet 4.6 | $3.00 | $15.00 |

### Long Context Premium (>200K input tokens)

There are conflicting reports on whether this surcharge is still active for Opus/Sonnet 4.6:

- Some sources say the surcharge was **removed** — flat per-token rates regardless of context size
- Others still reference 2x pricing when input exceeds 200K tokens per request:
  - Opus 4.6: $10.00 input / $37.50 output per M tokens
  - Sonnet 4.6: $6.00 input / $22.50 output per M tokens

**Status as of April 2026: unclear.** Check [API pricing page](https://platform.claude.com/docs/en/about-claude/pricing) for current rates.

## Context Window and Token Burn Rate

The weekly budget is measured in **tokens consumed**, not dollars. Larger context = more tokens per interaction = faster budget depletion.

Claude Code re-sends the full conversation context with each turn. This means:

| Context Usage | Approx Input Tokens/Turn | Relative Burn Rate |
|--------------|-------------------------|-------------------|
| 10% (100K) | ~100K+ | 1x (baseline) |
| 20% (200K) | ~200K+ | 2x |
| 50% (500K) | ~500K+ | 5x |

**Key insight:** It's not that tokens "cost more" at higher context — it's that you're *using more of them* per interaction. A session at 50% context burns through your weekly quota ~5x faster per turn than a session at 10% context.

### Recommendation

Keep context under ~20% to maximize weekly quota longevity. When approaching 18-20%:
- Compact the conversation (`/compact`)
- Start a new session
- Use subagents for isolated tasks (they have separate context)

The status line already warns at 18% (yellow) and 20% (red) for Opus 1M context.

## Estimating Overage Cost from Usage %

The status line estimates overage as `(projected_percentage - 100) * $2`. This assumes roughly $200 worth of API usage equals 100% of the Max 20x weekly budget. This is a rough heuristic — actual cost depends on:

- Input vs output token ratio (output tokens cost 5x more)
- Whether the long-context surcharge applies
- Which model is used (Opus vs Sonnet)
- Average context window size during the week

The `~$` prefix indicates this is an estimate, not a precise figure.

## Typical Usage Benchmarks

From Anthropic's published data:
- Average cost: ~$6/developer/day
- Team average: $100-200/developer/month (with Sonnet 4.6)
- 90% of users stay below $12/day
- Max 20x provides 24-40 hours of Opus 4 usage per week

## Sources

- [What is the Max plan?](https://support.claude.com/en/articles/11049741-what-is-the-max-plan)
- [Using Claude Code with your Pro or Max plan](https://support.claude.com/en/articles/11145838-using-claude-code-with-your-pro-or-max-plan)
- [Understanding usage and length limits](https://support.claude.com/en/articles/11647753-understanding-usage-and-length-limits)
- [Pricing - Claude API Docs](https://platform.claude.com/docs/en/about-claude/pricing)
- [Claude million-token pricing change](https://thenewstack.io/claude-million-token-pricing/)
- [Claude Code Limits Guide](https://www.truefoundry.com/blog/claude-code-limits-explained)
- [The Token Guide: How Claude's Limits Actually Work](https://limitededitionjonathan.substack.com/p/why-you-keep-hitting-claudes-usage)
- [Anthropic admits Claude Code quotas running out too fast](https://www.theregister.com/2026/03/31/anthropic_claude_code_limits/)
- [Weekly reset bug report (per-account reset behavior)](https://github.com/anthropics/claude-code/issues/29680)
