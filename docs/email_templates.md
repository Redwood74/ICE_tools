# Email Templates — ICEpicks Licensing

This document contains the canonical email templates for the ICEpicks
verification and licensing workflow.

Templates are available in:
- Plain text (below)
- HTML variants (see `email_verification.html`, `email_approval.html`,
  `email_revocation.html` in this directory)

---

## Template 1: Verification Email

**Subject:** ICEpicks License Verification – Action Required

**Plain text:**

```
Hello [APPLICANT_NAME],

Thank you for requesting a license verification for ICEpicks.

We received a verification request from:

  Organization:  [ORG_NAME]
  Website:       [ORG_WEBSITE]
  Contact:       [APPLICANT_EMAIL]
  Intended use:  [INTENDED_USE]

To complete verification, please confirm your request using the
information below.

  Verification code: [VERIFICATION_CODE]
  Verification link: [VERIFICATION_LINK]

This code and link expire in 7 days ([EXPIRY_DATE]).

By completing verification, you confirm that:

  1. [ORG_NAME] is a qualifying organization under the ICE Advocacy
     Public License (IAPL) v1.0.
  2. Your use of ICEpicks will be non-commercial and consistent with
     the license terms.
  3. You will not use ICEpicks for any purpose prohibited under
     Section 5 of the IAPL v1.0, including immigration enforcement,
     detention, or surveillance.
  4. You understand that this license is revocable upon breach or
     misrepresentation.

Please review the full license at:
  https://github.com/Redwood74/ICEpicks/blob/main/LICENSE.md

If you did not request this verification, please ignore this email or
reply to notify us.

Regards,
ICEpicks Licensing Team
Ray Quinney & Nebeker P.C.
licensing.icepicks@rqn.com
```

---

## Template 2: Approval Email

**Subject:** ICEpicks License Verification – Approved | Reference ID: [LICENSE_REF_ID]

**Plain text:**

```
Hello [APPLICANT_NAME],

Your ICEpicks license verification has been approved.

  Organization:       [ORG_NAME]
  License Reference:  [LICENSE_REF_ID]
  Approved date:      [APPROVAL_DATE]
  License type:       Non-commercial (IAPL v1.0)

Your organization is now formally on record as a verified user of
ICEpicks under the ICE Advocacy Public License (IAPL) v1.0.

Please retain this License Reference ID for your records.

KEY REMINDERS:

  - Your license is non-commercial and non-transferable.
  - Use of ICEpicks for immigration enforcement, detention, or
    surveillance is categorically prohibited and will result in
    immediate revocation.
  - The license is revocable at any time for breach or
    misrepresentation.
  - See LICENSE.md for the full terms.

Resources:
  License:     https://github.com/Redwood74/ICEpicks/blob/main/LICENSE.md
  FAQ:         https://github.com/Redwood74/ICEpicks/blob/main/FAQ.md
  Trademarks:  https://github.com/Redwood74/ICEpicks/blob/main/TRADEMARKS.md

Thank you for the work you do.

Regards,
ICEpicks Licensing Team
Ray Quinney & Nebeker P.C.
licensing.icepicks@rqn.com
```

---

## Template 3: Revocation Email

**Subject:** ICEpicks License – Notice of Revocation | Reference ID: [LICENSE_REF_ID]

**Plain text:**

```
Hello [RECIPIENT_NAME],

This notice is to inform you that the ICEpicks license issued to
[ORG_NAME] (License Reference ID: [LICENSE_REF_ID]) has been revoked,
effective [REVOCATION_DATE].

Reason: [REVOCATION_REASON]

REQUIRED ACTIONS:

  1. Immediately cease all use of ICEpicks and any derivative works.
  2. Destroy all copies of the Software in your possession or control.
  3. Cease distribution of any derivative works.

These obligations are effective immediately.

If you believe this revocation is in error, you may contact us within
10 business days at licensing.icepicks@rqn.com with supporting
information. We will review and respond in good faith.

This notice does not waive any rights or remedies available to
Ray Quinney & Nebeker P.C. under applicable law.

Regards,
ICEpicks Licensing Team
Ray Quinney & Nebeker P.C.
licensing.icepicks@rqn.com
```

---

## Template placeholders

| Placeholder | Description |
|---|---|
| `[APPLICANT_NAME]` | Full name of the applicant |
| `[ORG_NAME]` | Organization name |
| `[ORG_WEBSITE]` | Organization's official website URL |
| `[APPLICANT_EMAIL]` | Applicant's institutional email address |
| `[INTENDED_USE]` | Brief description of intended use |
| `[VERIFICATION_CODE]` | 8-character base32 code |
| `[VERIFICATION_LINK]` | Full URL including embedded token |
| `[EXPIRY_DATE]` | ISO-8601 date 7 days from issuance |
| `[LICENSE_REF_ID]` | Assigned License Reference ID |
| `[APPROVAL_DATE]` | Date of approval |
| `[RECIPIENT_NAME]` | Name of revocation notice recipient |
| `[REVOCATION_DATE]` | Effective date of revocation |
| `[REVOCATION_REASON]` | Clear statement of the reason |

---

## Verification code format

- **Encoding:** Base32 (RFC 4648), uppercase letters and digits 2–7
- **Length:** 8 characters
- **Example:** `BJTP4ZQA`
- **Expiry:** 7 days from issuance
- **Display format:** Present in the email as a human-readable code AND
  embedded in the verification link as a query parameter

---

*These templates are maintained in `docs/email_templates.md`.*
*For licensing: licensing.icepicks@rqn.com*
