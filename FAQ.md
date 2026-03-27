# Frequently Asked Questions — ICEpicks

---

## General

### What is ICEpicks?

ICEpicks is a local automation utility that monitors the ICE Online Detainee
Locator for a specific person by alien registration number (A-number) and
country of origin. It runs multiple fresh search attempts per scheduled check
to reduce false negatives caused by the site's unreliable behavior.

### Is this an official ICE tool?

No. ICEpicks is an independent tool created by advocates and attorneys to work
*with* the ICE locator website. It has no affiliation with or endorsement by
ICE, DHS, CBP, or any government agency.

### Does ICEpicks store personal information in the cloud?

No. ICEpicks is a local-first tool. All data, including screenshots, HTML
artifacts, and run logs, is stored on your local machine. Nothing is sent
externally except the optional Teams webhook notification (which you
control).

---

## Licensing

### What license does ICEpicks use?

ICEpicks is licensed under the **ICE Advocacy Public License (IAPL) v1.0**,
a custom source-available license. This is **not** an OSI-approved open-source
license.

### Is ICEpicks free to use?

For qualifying non-commercial uses — including personal use, legal aid,
academic research, and civil-rights oversight — yes, ICEpicks is free.

Commercial use, and systematic use by commercial media organizations, requires
a separate paid license.

### Can my public defender office use ICEpicks?

Yes. Public Defender Offices, Federal Defender Organizations, and court-
appointed counsel operating under state or municipal authority are covered
by the automatic license path in Section 6 of the IAPL v1.0.

You do not need to obtain permission in advance, but you must:
- Use the Software solely for non-commercial legal representation
- Comply with all restrictions (especially the prohibition on enforcement use)
- Complete verification if requested

To receive a formal License Reference ID, submit a verification request
to `licensing.icepicks@rqn.com`.

### Can my nonprofit legal aid organization use ICEpicks?

Yes. Nonprofit legal services providers whose primary mission is representing
immigrants or persons in immigration proceedings are covered by the automatic
license path. The same conditions apply as for public defenders above.

### Can a private law firm use ICEpicks?

Private law firms are not covered by the automatic license. However, a firm
may request **case-specific written permission** for genuine pro bono
immigration representation. Contact `licensing.icepicks@rqn.com` with:
- Firm name and website
- Description of the specific pro bono matter(s)
- Confirmation that the use is non-commercial and for client benefit only

### Can I use ICEpicks for journalism or news reporting?

Occasional, non-commercial journalistic reference use (e.g., testing the tool
to write an article about ICE locator reliability) is permitted under the
general non-commercial terms.

Systematic or recurring use by commercial news or media organizations for
revenue-generating purposes requires a **separate paid license**.
Contact `licensing.icepicks@rqn.com`.

### Can government agencies use ICEpicks?

Very narrowly. Government employees may use ICEpicks only for non-operational
purposes such as:
- Legislative policy analysis
- Civil-rights oversight
- Academic or compliance review
- Court-ordered use limited to the scope of the order

**Categorical prohibition:** ICEpicks may never be used by ICE, CBP, DHS, or
any agency for immigration enforcement, detention operations, or surveillance.
This prohibition is absolute and cannot be waived.

### Can I fork ICEpicks?

Yes, under these conditions:
- Your fork must use the IAPL v1.0 (or a later version designated by the Licensor)
- Your fork must use clearly distinct branding (not "ICEpicks")
- You must include a prominent disclaimer (see TRADEMARKS.md)
- Your fork must be non-commercial and source-available
- You must include attribution to the original ICEpicks project

### Can I sell a commercial product based on ICEpicks?

Not without a separate commercial license. Contact
`licensing.icepicks@rqn.com`.

---

## Verification

### How do I get a License Reference ID?

Send a verification request to `licensing.icepicks@rqn.com` with:
- Organization name and type
- Official website
- Primary contact name and institutional email
- Description of intended use
- Confirmation of non-commercial use
- Confirmation that use does not fall within any prohibited category

You will receive a one-time verification code and link. After completing
verification, you will receive a License Reference ID that formally documents
your permitted use.

### How long does verification take?

The Licensor aims to process complete requests within 10 business days.
Incomplete requests may be returned for additional information.

### What happens if my license is revoked?

You will be notified by email. You must immediately cease all use and
distribution of the Software and destroy all copies. See Section 8 of
the LICENSE.md for details.

---

## Technical

### Why does the ICE locator return false "0 Search Results"?

The ICE locator is a flaky single-page application that intermittently fails
to return results for persons who are actively detained. This appears to be a
site reliability issue, not a confirmation of absence. ICEpicks addresses this
by running multiple independent fresh attempts per scheduled check.

### What does each result state mean?

- **`ZERO_RESULT`**: The site explicitly returned "0 Search Results." This
  does *not* confirm the person is not detained; re-run later.
- **`LIKELY_POSITIVE`**: The page contains indicators consistent with a
  detainee record. Verify manually before acting.
- **`AMBIGUOUS_REVIEW`**: The page loaded but the content is unclear or
  partially loaded. Review the saved artifacts.
- **`BOT_CHALLENGE_OR_BLOCKED`**: The site presented a CAPTCHA or blocked
  the request. Wait before retrying.
- **`ERROR`**: The browser or network failed. Check logs and artifacts.

### How does deduplication work?

ICEpicks computes a SHA-256 hash of the normalised page text. If the same
hash was already sent as a notification in a recent run, no new notification
is dispatched. This prevents repeated alerts for the same record.

### Where are artifacts stored?

By default, in the `artifacts/` directory within your working directory.
Each run gets its own subdirectory named by timestamp. See the README for the
full layout.

### How do I tune selectors if the ICE site changes?

Edit `src/findICE/selectors.py`. Selectors are organized in priority order
(label-based → placeholder → role → CSS fallback). Add or modify candidates
as needed after inspecting the saved HTML artifacts.

---

*For licensing: licensing.icepicks@rqn.com*  
*For trademarks: trademarks.icepicks@rqn.com*
