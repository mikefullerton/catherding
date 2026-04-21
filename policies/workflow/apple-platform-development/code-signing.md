---
title: "Apple Code Signing"
summary: "Signing team is mikefullerton; entitlements preserved; no certs or provisioning profiles in the repo."
triggers: [configuring-signing, entitlements-change, xcode-team-setup, creating-xcode-project]
tags: [signing, entitlements, apple, security]
---

# Apple Code Signing

Signing team is `mikefullerton`; entitlements preserved; no certs or provisioning profiles in the repo.

- The signing team MUST be `mikefullerton` (Temporal Apple Developer account).
- You MUST preserve all entitlements when modifying project settings or converting projects.
- Provisioning profiles and certificates MUST be managed on the local machine only — you MUST NOT check them into the repo.
- You SHOULD use Xcode's automatic signing where possible.

**Derived from cookbook:** [explicit-over-implicit](../../../agenticcookbook/principles/explicit-over-implicit.md), [fail-fast](../../../agenticcookbook/principles/fail-fast.md)
