# 5ibr Filter Guidelines

## Purpose

These guidelines define the quality standards for all filter rules included in the 5ibr project.

---

# Rule Requirements

A rule MUST:

- Be verified before inclusion.
- Not break login services.
- Not block software updates.
- Not block operating system services.
- Not block DNS providers.
- Not block CDN providers unless necessary.

---

# Rule Sources

Rules may be added from:

- Real AdGuard Home query logs
- Vendor documentation
- Security research
- Malware reports
- Public bug reports

Rules should NOT be copied blindly from other filter projects.

---

# Categories

Rules must belong to one of the following categories:

- Ads
- Telemetry
- Privacy
- Social
- Mobile
- Gaming
- Smart TV
- Whitelist
- Family

---

# Validation

Every new rule must pass:

- validate.py
- duplicate check
- syntax validation

---

# Rule Format

Preferred format:

||example.com^

Exception:

@@||example.com^

Comments:

! Example comment

---

# Performance

Avoid duplicate rules.

Avoid wildcard rules when a specific rule is sufficient.

Prefer domain-based blocking over URL-based blocking.

---

# Stability

Never block:

- Login domains
- Update servers
- Authentication services

unless there is strong evidence and an explicit decision.

---

# Philosophy

5ibr prioritizes:

- Stability
- Performance
- Privacy
- Accuracy

instead of simply having the largest number of rules.