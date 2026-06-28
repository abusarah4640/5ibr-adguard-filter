# 5ibr Rule Review Process

## Purpose

Every rule added to the project must be reviewed before being included.

The goal is to maximize stability, privacy, and performance while minimizing false positives.

---

# Rule Sources

A rule may originate from one or more of the following sources:

- AdGuard Home query logs
- Vendor documentation
- Official telemetry documentation
- Malware analysis
- Security research
- Bug reports
- Community contributions

---

# Review Checklist

Before accepting a rule, verify:

- [ ] The domain exists.
- [ ] The rule syntax is correct.
- [ ] The domain is not already covered.
- [ ] The rule does not break authentication.
- [ ] The rule does not break updates.
- [ ] The rule does not break cloud synchronization.
- [ ] The rule does not break payment systems.

---

# Rule Metadata

Every accepted rule should have the following information recorded:

- Vendor
- Category
- Source
- Review Date
- Reviewer
- Confidence

---

# Confidence Levels

100
Known telemetry or advertising endpoint.

90
Strong evidence from multiple sources.

75
Observed frequently in query logs.

50
Requires further review.

25
Unverified.

---

# Categories

- Ads
- Telemetry
- Privacy
- Social
- Gaming
- Smart TV
- Mobile
- Whitelist
- Family

---

# Rejected Rules

Rules must be rejected if they break:

- Login
- Updates
- Purchases
- Streaming
- Cloud Sync

unless explicitly intended for a specialized filter.

---

# Philosophy

Quality is more important than quantity.

Every rule should have a clear reason to exist.

When in doubt, do not include the rule until additional evidence is available.