# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security problems.

Email the maintainer privately or open a private security advisory on GitHub:
**Settings → Security → Advisories** for this repository.

Include:
- Description and impact
- Steps to reproduce
- Affected component (API route, agent graph, frontend)

We aim to acknowledge within 72 hours.

## Production hardening checklist

- [ ] `SECRET_KEY` set via secrets manager (`openssl rand -hex 32`), never committed
- [ ] `ENVIRONMENT=production`, `DEBUG=false`
- [ ] `CORS_ORIGINS` limited to real frontend origins (no `*`)
- [ ] Postgres not exposed publicly; strong `POSTGRES_PASSWORD`
- [ ] TLS terminated at load balancer / reverse proxy
- [ ] Rate limiting enabled (in-app or edge: Cloudflare / nginx)
- [ ] HITL thresholds reviewed for financial / write actions
- [ ] PII sanitizer entities reviewed for your jurisdiction
- [ ] Audit logs retained per compliance policy
- [ ] Dependabot / CI green before release tags

## Known threat model notes

- JWT tokens are bearer tokens; store only in memory or secure httpOnly cookies on the frontend in production.
- In-memory rate limiter and HITL thread store are **single-instance**. For horizontal scale, replace with Redis / Postgres checkpointer.
- LLM tool adapters are stubs — production integrations must use least-privilege credentials and outbound allowlists.
