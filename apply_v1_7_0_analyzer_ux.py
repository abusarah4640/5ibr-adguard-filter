from pathlib import Path

BASE = Path.cwd()

# -------------------------------------------------------------------
# v1.7.0 Analyzer UX patch for 5ibr Filter Toolkit
# Safe, template-focused upgrade. Does not change database semantics.
# -------------------------------------------------------------------

# 1) Add UX helpers to web/app.py
app_path = BASE / 'web' / 'app.py'
s = app_path.read_text(encoding='utf-8')

helpers = r'''

def normalize_unknown(value):
    """Return empty string for Unknown/unknown placeholder values."""
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"unknown", "none", "null", "-", "—"}:
        return ""
    return text


def confidence_level(value):
    try:
        score = int(float(value or 0))
    except (TypeError, ValueError):
        score = 0
    if score >= 80:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def recommendation_badge(value):
    rec = (value or "unknown").strip().lower()
    if rec in {"approved-candidate", "approved"}:
        return "success"
    if rec in {"review", "needs-review"}:
        return "warning"
    if rec in {"rejected", "reject"}:
        return "danger"
    if rec in {"ignored", "ignore"}:
        return "secondary"
    return "light"


def explain_suggestion(row):
    """Build a simple human-readable analyzer trace from a suggestion row."""
    reasons_raw = row.get("Reasons", "") or row.get("reasons", "") or ""
    reasons = [part.strip() for part in reasons_raw.replace(";", "\n").splitlines() if part.strip()]
    vendor = normalize_unknown(row.get("Suggested Vendor") or row.get("Vendor"))
    category = normalize_unknown(row.get("Suggested Category") or row.get("Category"))
    filter_name = normalize_unknown(row.get("Suggested Filter") or row.get("Filter"))
    return {
        "root": row.get("Root", ""),
        "domain": row.get("Domain", ""),
        "vendor_ok": bool(vendor),
        "category_ok": bool(category),
        "filter_ok": bool(filter_name),
        "vendor": vendor or "No match",
        "category": category or "Needs selection",
        "filter": filter_name or "Needs selection",
        "reasons": reasons or ["No local analyzer rules matched"],
    }
'''

if 'def normalize_unknown(' not in s:
    marker = '\napp = Flask(__name__)'
    if marker in s:
        s = s.replace(marker, helpers + marker, 1)
    else:
        s += helpers

# Ensure Jinja globals/filters are registered after app creation
registration = r'''
app.jinja_env.globals.update(
    normalize_unknown=normalize_unknown,
    confidence_level=confidence_level,
    recommendation_badge=recommendation_badge,
    explain_suggestion=explain_suggestion,
)
'''
if 'normalize_unknown=normalize_unknown' not in s:
    marker = 'app = Flask(__name__)'
    idx = s.find(marker)
    if idx != -1:
        end = s.find('\n', idx)
        s = s[:end+1] + registration + s[end+1:]
    else:
        s += '\n' + registration

app_path.write_text(s, encoding='utf-8')

# 2) Replace suggestion_form.html with UX-improved form
suggestion_form = BASE / 'web' / 'templates' / 'suggestion_form.html'
suggestion_form.write_text(r'''{% extends "base.html" %}
{% block content %}
{% set vendor_value = normalize_unknown(row.get('Suggested Vendor') or row.get('Vendor')) %}
{% set category_value = normalize_unknown(row.get('Suggested Category') or row.get('Category')) %}
{% set filter_value = normalize_unknown(row.get('Suggested Filter') or row.get('Filter')) %}
{% set confidence_value = row.get('Confidence') or 0 %}
{% set level = confidence_level(confidence_value) %}
{% set exp = explain_suggestion(row) %}

<div class="d-flex justify-content-between align-items-center mb-3">
  <div>
    <h1 class="mb-1">{{ t('approve_suggestion') if t else 'Approve Suggestion' }}</h1>
    <div class="text-muted">{{ row.get('Domain', '') }}</div>
  </div>
  <a class="btn btn-outline-secondary" href="{{ url_for('suggestions') }}">{{ t('cancel') if t else 'Cancel' }}</a>
</div>

{% if not category_value %}
<div class="alert alert-warning">⚠ يحتاج هذا الاقتراح اختيار التصنيف قبل الاعتماد.</div>
{% endif %}
{% if not filter_value %}
<div class="alert alert-warning">⚠ يحتاج هذا الاقتراح اختيار الفلتر قبل الاعتماد.</div>
{% endif %}
{% if not vendor_value %}
<div class="alert alert-info">ℹ لم يتم التعرف على المزود تلقائيًا. اختر المزود أو اكتب اسمًا جديدًا.</div>
{% endif %}

<div class="row g-3">
  <div class="col-lg-7">
    <div class="card">
      <div class="card-body">
        <form method="post">
          <div class="mb-3">
            <label class="form-label">{{ t('domain') if t else 'Domain' }}</label>
            <input class="form-control" name="domain" value="{{ row.get('Domain', '') }}" required>
          </div>

          <div class="mb-3">
            <label class="form-label">{{ t('vendor') if t else 'Vendor' }}</label>
            <input class="form-control" name="vendor" list="vendor-options" value="{{ vendor_value }}" placeholder="اختر المزود أو اكتب اسمًا جديدًا" required>
            <datalist id="vendor-options">
              {% for item in vendors or [] %}
                {% if normalize_unknown(item) %}<option value="{{ item }}">{% endif %}
              {% endfor %}
            </datalist>
          </div>

          <div class="mb-3">
            <label class="form-label">{{ t('category') if t else 'Category' }}</label>
            <select class="form-select" name="category" required>
              <option value="">— اختر التصنيف —</option>
              {% for item in categories or [] %}
                {% if normalize_unknown(item) %}
                <option value="{{ item }}" {% if item == category_value %}selected{% endif %}>{{ item }}</option>
                {% endif %}
              {% endfor %}
            </select>
          </div>

          <div class="mb-3">
            <label class="form-label">{{ t('filter') if t else 'Filter' }}</label>
            <select class="form-select" name="filter" required>
              <option value="">— اختر الفلتر —</option>
              {% for item in filters or [] %}
                {% if normalize_unknown(item) %}
                <option value="{{ item }}" {% if item == filter_value %}selected{% endif %}>{{ item }}</option>
                {% endif %}
              {% endfor %}
            </select>
          </div>

          <div class="mb-3">
            <label class="form-label">{{ t('confidence') if t else 'Confidence' }}</label>
            <input class="form-control" type="number" min="0" max="100" name="confidence" value="{{ confidence_value }}">
            <div class="progress mt-2" style="height: 8px;">
              <div class="progress-bar {% if level == 'high' %}bg-success{% elif level == 'medium' %}bg-warning{% else %}bg-danger{% endif %}" style="width: {{ confidence_value|int }}%"></div>
            </div>
            <div class="form-text">{{ confidence_value }} / 100</div>
          </div>

          <div class="d-flex gap-2 justify-content-end">
            <a class="btn btn-secondary" href="{{ url_for('suggestions') }}">{{ t('cancel') if t else 'Cancel' }}</a>
            <button class="btn btn-success" type="submit">{{ t('approve') if t else 'Approve' }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>

  <div class="col-lg-5">
    <div class="card mb-3">
      <div class="card-header fw-bold">Explain Analyzer</div>
      <div class="card-body">
        <div class="mb-2"><strong>Domain:</strong> {{ exp.domain }}</div>
        <div class="mb-2"><strong>Root:</strong> {{ exp.root or '-' }}</div>
        <hr>
        <div class="mb-2">{% if exp.vendor_ok %}✓{% else %}✗{% endif %} <strong>Vendor:</strong> {{ exp.vendor }}</div>
        <div class="mb-2">{% if exp.category_ok %}✓{% else %}✗{% endif %} <strong>Category:</strong> {{ exp.category }}</div>
        <div class="mb-2">{% if exp.filter_ok %}✓{% else %}✗{% endif %} <strong>Filter:</strong> {{ exp.filter }}</div>
        <hr>
        <strong>Reasons</strong>
        <ul class="mt-2 mb-0">
          {% for reason in exp.reasons %}
          <li>{{ reason }}</li>
          {% endfor %}
        </ul>
      </div>
    </div>

    <div class="card">
      <div class="card-header fw-bold">Recommendation</div>
      <div class="card-body">
        {% set rec = row.get('Recommendation', 'unknown') %}
        <span class="badge text-bg-{{ recommendation_badge(rec) }}">{{ rec }}</span>
      </div>
    </div>
  </div>
</div>
{% endblock %}
''', encoding='utf-8')

# 3) Improve analysis template badges if file exists; conservative replacement/additions
analysis = BASE / 'web' / 'templates' / 'analysis.html'
if analysis.exists():
    a = analysis.read_text(encoding='utf-8')
    # Add a small style block if not present
    if 'v170-badge-ux' not in a:
        a = a.replace('{% block content %}', '{% block content %}\n<style id="v170-badge-ux">.confidence-pill{min-width:64px;display:inline-block}.table td{vertical-align:middle}</style>', 1)
    # Best-effort: add link to review queue already likely exists, no risky full rewrite.
    analysis.write_text(a, encoding='utf-8')

# 4) Add tests for helpers and template rendering
ptest = BASE / 'tests' / 'test_web_v170_analyzer_ux.py'
ptest.write_text(r'''def test_v170_unknown_helpers():
    import web.app as webapp

    assert webapp.normalize_unknown('Unknown') == ''
    assert webapp.normalize_unknown('unknown') == ''
    assert webapp.normalize_unknown('Google') == 'Google'
    assert webapp.confidence_level(90) == 'high'
    assert webapp.confidence_level(60) == 'medium'
    assert webapp.confidence_level(10) == 'low'
    assert webapp.recommendation_badge('review') == 'warning'


def test_v170_suggestion_form_renders_unknown_as_guidance():
    import web.app as webapp

    row = {
        'Domain': 'unknown.example.test',
        'Root': 'example.test',
        'Suggested Vendor': 'Unknown',
        'Suggested Category': 'Unknown',
        'Suggested Filter': 'unknown',
        'Confidence': '0',
        'Recommendation': 'unknown',
        'Reasons': 'no local analyzer rules matched',
        'Seen': '1',
    }

    with webapp.app.test_request_context('/suggestions/unknown.example.test/approve'):
        html = webapp.render_template(
            'suggestion_form.html',
            row=row,
            suggestion=row,
            vendors=['Google', 'Meta'],
            categories=['Ads', 'Telemetry', 'Unknown'],
            filters=['ads', 'telemetry', 'unknown'],
        )

    assert 'Explain Analyzer' in html
    assert 'يحتاج هذا الاقتراح اختيار التصنيف' in html
    assert 'يحتاج هذا الاقتراح اختيار الفلتر' in html
    assert '0 / 100' in html
''', encoding='utf-8')

# 5) Version marker
version = BASE / 'VERSION'
if version.exists():
    version.write_text('1.7.0\n', encoding='utf-8')

print('OK: applied v1.7.0 Analyzer UX patch')
print('Next: pip install -e . && pytest -q && sudo systemctl restart fivebr-web')
