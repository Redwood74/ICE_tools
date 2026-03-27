# Security Policy — ICEpicks

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅        |

---

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

To report a vulnerability:

1. Email **licensing.icepicks@rqn.com** with subject:
   `[SECURITY] ICEpicks – <brief description>`
2. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Your suggested fix (optional)
3. You will receive an acknowledgment within 5 business days.

---

## Security considerations

ICEpicks handles **sensitive personal information** including alien
registration numbers and locator search results. Contributors and users
should be aware of the following:

### What ICEpicks does NOT do

- Does not transmit personal data to any third party except the configured
  Teams webhook (which is controlled entirely by you)
- Does not store data in the cloud
- Does not log unmasked A-numbers (A-numbers are masked in logs)
- Does not require authentication credentials other than the optional
  Teams webhook URL

### What you are responsible for

- Protecting the `.env` file and `state/` directory from unauthorized access
- Ensuring the machine running ICEpicks has appropriate access controls
- Not sharing artifact directories containing screenshots or HTML that may
  include personal information
- Rotating the Teams webhook URL if it is exposed

### Secrets

- Never commit your `.env` file to version control
- Store `TEAMS_WEBHOOK_URL` in environment variables or `.env` only
- The optional keyring integration provides a more secure alternative to
  `.env` for secrets

---

## Threat model

ICEpicks is designed to run locally on a trusted machine. It is not designed
for multi-user, cloud, or shared-hosting environments.

The main security risks are:

1. **Exposed A-number in logs or artifacts** – mitigated by log redaction
   and artifact directory access controls
2. **Exposed Teams webhook URL** – mitigated by treating it as a secret in
   `.env` (which is git-ignored by default)
3. **Site content served to attackers via artifact files** – mitigated by
   keeping artifact directories private and not serving them publicly

---

*For security reports: licensing.icepicks@rqn.com*
