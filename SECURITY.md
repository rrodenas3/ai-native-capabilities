# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| `main` | ✅ Yes |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report security issues by email to: **raul@global-freaks.com**

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You will receive a response within 48 hours. If the issue is confirmed, a fix will be prioritized and you will be credited in the release notes (unless you prefer to remain anonymous).

## Scope

This project is a local development tool and reference implementation. The primary security considerations are:

- **Prompt injection defense** — The SSGM A-MemGuard layer in `core/harness/memory.py` scans all external inputs before governed memory writes. Any bypass of this layer is in scope.
- **Dependency vulnerabilities** — Report outdated or vulnerable dependencies.
- **Credential exposure** — If any API keys or secrets are accidentally committed to history.
- **Agent action boundaries** — If an agent can be prompted to take actions outside its defined scope (financial writes, destructive operations).

## Out of Scope

- Theoretical attacks with no practical exploit path
- Issues in development-only dependencies (pytest, ruff, mypy)
- Social engineering
