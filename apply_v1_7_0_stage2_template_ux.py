from pathlib import Path
import re
import subprocess
import sys

ROOT = Path.cwd()
TEMPLATE = ROOT / "web" / "templates" / "suggestion_form.html"
TEST = ROOT / "tests" / "test_web_v170_stage2_template_ux.py"

if not TEMPLATE.exists():
    raise SystemExit(f"Missing template: {TEMPLATE}")

original = TEMPLATE.read_text(encoding="utf-8")
backup = TEMPLATE.with_suffix(".html.before-v1.7.0-stage2")
if not backup.exists():
    backup.write_text(original, encoding="utf-8")

new_template = r'''{% extends "base.html" %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-3">
  <div>
    <h1 class="h3 mb-1">Approve Suggestion</h1>
    <div class="text-muted small">Review analyzer evidence before adding this domain to the database.</div>
  </div>
  <a class="btn btn-outline-secondary btn-sm" href="{{ url_for('suggestions') }}">Back to Suggestions</a>
</div>

{% set domain_value = row.get('Domain', '') %}
{% set vendor_value = normalize_unknown(row.get('Suggested Vendor', ''), '') %}
{% set category_value = normalize_unknown(row.get('Suggested Category', ''), '') %}
{% set filter_value = normalize_unknown(row.get('Suggested Filter', ''), '') %}
{% set confidence_value = row.get('Confidence', 0) | int %}
{% set recommendation_value = row.get('Recommendation', 'unknown') %}
{% set level = confidence_level(confidence_value) %}
{% set badge = recommendation_badge(recommendation_value) %}

<div class="row g-3 mb-3">
  <div class="col-md-3">
    <div class="card h-100">
      <div class="card-body">
        <div class="text-muted small">Domain</div>
        <div class="fw-semibold text-break">{{ domain_value }}</div>
      </div>
    </div>
  </div>
  <div class="col-md-3">
    <div class="card h-100">
      <div class="card-body">
        <div class="text-muted small">Recommendation</div>
        <span class="badge text-bg-{{ badge }}">{{ recommendation_value }}</span>
      </div>
    </div>
  </div>
  <div class="col-md-3">
    <div class="card h-100">
      <div class="card-body">
        <div class="text-muted small">Confidence</div>
        <div class="fw-semibold">{{ confidence_value }} / 100</div>
        <div class="progress mt-2" role="progressbar" aria-valuenow="{{ confidence_value }}" aria-valuemin="0" aria-valuemax="100">
          <div class="progress-bar {% if level == 'high' %}bg-success{% elif level == 'medium' %}bg-warning{% else %}bg-danger{% endif %}" style="width: {{ confidence_value }}%"></div>
        </div>
      </div>
    </div>
  </div>
  <div class="col-md-3">
    <div class="card h-100">
      <div class="card-body">
        <div class="text-muted small">Seen</div>
        <div class="fw-semibold">{{ row.get('Seen', '') }}</div>
      </div>
    </div>
  </div>
</div>

{% if not vendor_value or not category_value or not filter_value %}
<div class="alert alert-warning">
  <div class="fw-semibold mb-1">This suggestion needs manual review before approval.</div>
  <ul class="mb-0">
    {% if not vendor_value %}<li>Vendor needs selection.</li>{% endif %}
    {% if not category_value %}<li>Category needs selection.</li>{% endif %}
    {% if not filter_value %}<li>Filter needs selection.</li>{% endif %}
  </ul>
</div>
{% endif %}

<div class="row g-3">
  <div class="col-lg-7">
    <div class="card">
      <div class="card-header fw-semibold">Approval Details</div>
      <div class="card-body">
        <form method="post">
          <div class="mb-3">
            <label class="form-label">Domain</label>
            <input class="form-control" name="domain" value="{{ domain_value }}" required>
          </div>

          <div class="row g-3">
            <div class="col-md-4">
              <label class="form-label">Vendor</label>
              <select class="form-select" name="vendor" required>
                <option value="">Select vendor</option>
                {% for value in vendors %}
                <option value="{{ value }}" {% if value == vendor_value %}selected{% endif %}>{{ value }}</option>
                {% endfor %}
              </select>
            </div>
            <div class="col-md-4">
              <label class="form-label">Category</label>
              <select class="form-select" name="category" required>
                <option value="">Select category</option>
                {% for value in categories %}
                <option value="{{ value }}" {% if value == category_value %}selected{% endif %}>{{ value }}</option>
                {% endfor %}
              </select>
            </div>
            <div class="col-md-4">
              <label class="form-label">Filter</label>
              <select class="form-select" name="filter" required>
                <option value="">Select filter</option>
                {% for value in filters %}
                <option value="{{ value }}" {% if value == filter_value %}selected{% endif %}>{{ value }}</option>
                {% endfor %}
              </select>
            </div>
          </div>

          <div class="row g-3 mt-1">
            <div class="col-md-4">
              <label class="form-label">Confidence</label>
              <input class="form-control" type="number" min="0" max="100" name="confidence" value="{{ confidence_value }}">
            </div>
            <div class="col-md-8">
              <label class="form-label">Root</label>
              <input class="form-control" value="{{ row.get('Root', '') }}" disabled>
            </div>
          </div>

          <div class="mt-4 d-flex gap-2">
            <button class="btn btn-success" type="submit">Approve and Add</button>
            <a class="btn btn-outline-secondary" href="{{ url_for('suggestions') }}">Cancel</a>
          </div>
        </form>
      </div>
    </div>
  </div>

  <div class="col-lg-5">
    <div class="card mb-3">
      <div class="card-header fw-semibold">Analyzer Explanation</div>
      <div class="card-body">
        <ul class="list-group list-group-flush">
          {% for reason in explain_suggestion(row) %}
          <li class="list-group-item px-0">✓ {{ reason }}</li>
          {% endfor %}
        </ul>
      </div>
    </div>

    <div class="card">
      <div class="card-header fw-semibold">Raw Suggestion</div>
      <div class="card-body small">
        <dl class="row mb-0">
          {% for key, value in row.items() %}
          <dt class="col-sm-5 text-muted">{{ key }}</dt>
          <dd class="col-sm-7 text-break">{{ value }}</dd>
          {% endfor %}
        </dl>
      </div>
    </div>
  </div>
</div>
{% endblock %}
'''

TEMPLATE.write_text(new_template, encoding="utf-8")

TEST.write_text(r'''from web.app import app


def test_v170_stage2_suggestion_form_template_uses_ux_helpers():
    with app.app_context():
        template = app.jinja_env.get_template("suggestion_form.html")
        rendered = template.render(
            row={
                "Domain": "unknown.example.test",
                "Seen": "5",
                "Root": "example.test",
                "Suggested Vendor": "Unknown",
                "Suggested Category": "Unknown",
                "Suggested Filter": "unknown",
                "Confidence": "0",
                "Recommendation": "unknown",
                "Reasons": "no local analyzer rules matched",
            },
            suggestion={},
            vendors=["Example"],
            categories=["Telemetry"],
            filters=["telemetry"],
        )
    assert "Vendor needs selection" in rendered
    assert "Category needs selection" in rendered
    assert "Filter needs selection" in rendered
    assert "0 / 100" in rendered
    assert "Analyzer Explanation" in rendered
    assert "no local analyzer rules matched" in rendered
''', encoding="utf-8")

try:
    subprocess.run([sys.executable, "-m", "py_compile", "web/app.py"], cwd=ROOT, check=True)
except subprocess.CalledProcessError:
    TEMPLATE.write_text(original, encoding="utf-8")
    raise SystemExit("compile failed; restored template")

print("OK: v1.7.0 Stage 2 template UX applied")
