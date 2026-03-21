# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅        |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly. **Do not open a public issue.**

1. Email **jawwadali.work@gmail.com** with the subject line: `[SECURITY] ai-customer-support-agent — <brief description>`
2. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: within 48 hours
- **Initial assessment**: within 7 days
- **Fix or mitigation**: depends on severity, typically within 30 days

## Scope

This policy covers:
- The `agent/`, `api/`, `database/`, and `web/` source code
- Docker and Kubernetes configuration files
- Dependencies listed in `pyproject.toml` and `web/package.json`

## Important Note

This project is designed as a demonstration and hackathon submission. The default configuration does not handle real customer PII. If you deploy this in production with real data, ensure you implement appropriate data protection measures beyond what is included here.
