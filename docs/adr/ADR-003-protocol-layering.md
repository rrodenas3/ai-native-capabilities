# ADR-003: MCP Stateless Migration + Protocol Layering (MCP + A2A + ACP)

**Date:** 2026-06-17
**Status:** Accepted
**Research basis:** Frontier Agentic AI Engineering Patterns Deep Research (June 2026)

---

## Context

Three protocol developments in 2026 require architectural decisions:

1. **MCP 2026-07-28 RC** (final July 28, 2026): removes `initialize` handshake and
   `Mcp-Session-Id` (SEP-2567, SEP-2575). MCP servers become stateless HTTP services.
   `Mcp-Method`/`Mcp-Name` routing headers added. Tasks extension replaces experimental
   core tasks. `ttlMs`/`cacheScope` client caching. Roots/Sampling/Logging deprecated
   (12-month window). This enables hosting MCP servers as Cloudflare Workers / Vercel
   edge / AWS Lambda — no sticky sessions required.

2. **A2A v1.0** (Linux Foundation, GA March 2026, 150+ orgs): Signed Agent Cards,
   multi-tenancy, gRPC + JSON-RPC, version negotiation. Supported natively in Azure
   AI Foundry, Amazon Bedrock AgentCore, Google Cloud. Now the standard for
   agent-to-agent coordination distinct from model-to-tool (MCP).

3. **Commerce protocol stack** (relevant to Cap-03): UCP (Universal Commerce Protocol,
   Google + Shopify, Apache 2.0, Jan 2026), ACP (OpenAI + Stripe, Sept 2025),
   AP2 (Google, W3C Verifiable Credentials payment mandates, v0.2.0 Apr 2026).

---

## Decision

### Protocol responsibilities (clear separation)

```
Tool access:          MCP 2025-11-25 → migrate to 2026-07-28 on RC final
Agent coordination:   A2A v1.0 (Linux Foundation) — agent cards + signed tasks
Commerce checkout:    ACP (OpenAI+Stripe) + UCP (Google+Shopify) — Cap-03 only
Payment mandates:     AP2 (Google, W3C VC) — Cap-03 only
Web tool surfaces:    WebMCP (W3C, Chrome preview) — Cap-03 optional
```

Note: "Universal Context Protocol" does not exist as a published standard.
UCP = Universal **Commerce** Protocol. MCP is the context/tool protocol.

### MCP server migration plan (2025-11-25 → 2026-07-28)

**Phase 1 (now — implement with 2025-11-25, flag migration points):**
- All MCP servers implement stateless request handlers (no server-side session state)
- Session state moves to explicit state handles passed per-request
- Mark: `# MCP-MIGRATE: session-to-handle` comments at every session-state usage

**Phase 2 (after July 28, 2026 final):**
- Drop `Mcp-Session-Id` — route instead on `Mcp-Method` + `Mcp-Name` headers
- Replace experimental `tasks/*` with Tasks extension polling model
- Enable `ttlMs`/`cacheScope` on read-only tools (product catalog, policy docs)
- Add remote MCP deployment manifests (Cloudflare Workers, Vercel, Lambda)

**Phase 3 (12-month deprecation window):**
- Remove Roots, Sampling, Logging usage

### A2A integration (Cap-03, Cap-04)

- Cap-03: Sparky super-agent publishes an Agent Card (signed, versioned)
- Cap-03: Marty supplier agent communicates with third-party supplier agents via A2A
- Cap-04: Exception Handler publishes events via A2A to downstream systems
- All A2A Agent Cards stored in `core/a2a/cards/`

### Commerce protocol stack (Cap-03 only)

```
Layer 1 — Discovery:   MCP product-catalog connector
Layer 2 — Session:     A2A agent coordination (Sparky ↔ Marty ↔ third-party)
Layer 3 — Checkout:    ACP (Stripe) or UCP (Shopify) — configurable
Layer 4 — Payment:     AP2 signed mandates (W3C Verifiable Credentials)
```

Human approval required before any AP2 mandate is generated (financial action
above `AUTONOMOUS_ACTION_THRESHOLD_USD`).

---

## Consequences

**Positive:**
- MCP servers become ordinary stateless services (deployable anywhere, scalable)
- A2A gives inter-agent coordination a governance layer (signed cards, versioning)
- Commerce protocols future-proof Cap-03 for agentic shopping infrastructure

**Negative:**
- Migration cost: existing MCP servers built with 2025-11-25 need Phase 2 update
- A2A adds deployment complexity for agent card management
- Commerce protocol stack is three separate specs (learning curve)

**Risk:** MCP 2026-07-28 is an RC as of June 2026 (final July 28). Do not depend
on RC-specific features in production. Build against 2025-11-25 stable today;
annotate migration points for Phase 2.

---

## References
- MCP SEP-2567 (stateless), SEP-2575 (no initialize), SEP-1865 (MCP Apps)
- A2A v1.0 Linux Foundation GA (March 2026): a2aprotocol.org
- UCP: Universal Commerce Protocol, Apache 2.0 (Google + Shopify, Jan 2026)
- ACP: Agent Commerce Protocol (OpenAI + Stripe, Sept 2025)
- AP2: Google Agent Payment Protocol v0.2.0 (April 2026)
- WebMCP: W3C Web ML Community Group, `navigator.modelContext` (Feb 2026)
