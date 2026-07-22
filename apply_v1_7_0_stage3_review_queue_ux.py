from pathlib import Path

ROOT = Path.cwd()
tpl = ROOT / "web" / "templates" / "review_queue.html"
test = ROOT / "tests" / "test_web_v170_stage3_review_queue_ux.py"
version = ROOT / "VERSION"

if not tpl.exists():
    raise SystemExit("web/templates/review_queue.html not found. Run from /opt/5ibr")

backup = tpl.with_suffix(".html.before-v170-stage3")
if not backup.exists():
    backup.write_text(tpl.read_text(encoding="utf-8"), encoding="utf-8")

tpl.write_text(r'''{% extends "base.html" %}
{% block content %}
<h1 class="mb-4">{{ t('review_queue') }}</h1>
<p class="text-muted">{{ t('review_queue_desc') }}</p>

{% set total = rows|length %}
{% set review_count = rows|selectattr('Recommendation', 'equalto', 'review')|list|length %}
{% set unknown_count = rows|selectattr('Recommendation', 'equalto', 'unknown')|list|length %}
{% set candidate_count = rows|selectattr('Recommendation', 'equalto', 'approved-candidate')|list|length %}

<div class="row g-3 mb-4">
  <div class="col-md-3"><div class="card"><div class="card-body"><div class="text-muted small">Total Suggestions</div><div class="fs-3 fw-bold">{{ total }}</div></div></div></div>
  <div class="col-md-3"><div class="card"><div class="card-body"><div class="text-muted small">Needs Review</div><div class="fs-3 fw-bold">{{ review_count }}</div></div></div></div>
  <div class="col-md-3"><div class="card"><div class="card-body"><div class="text-muted small">Approved Candidates</div><div class="fs-3 fw-bold">{{ candidate_count }}</div></div></div></div>
  <div class="col-md-3"><div class="card"><div class="card-body"><div class="text-muted small">Unknown</div><div class="fs-3 fw-bold">{{ unknown_count }}</div></div></div></div>
</div>

<form class="row g-2 mb-4" method="get">
  <div class="col-md-3">
    <input class="form-control" name="q" value="{{ request.args.get('q','') }}" placeholder="Search domain">
  </div>
  <div class="col-md-2">
    <select class="form-select" name="recommendation">
      <option value="">Recommendation</option>
      {% for r in ['approved-candidate','review','unknown','rejected','ignored'] %}
      <option value="{{ r }}" {% if request.args.get('recommendation') == r %}selected{% endif %}>{{ r }}</option>
      {% endfor %}
    </select>
  </div>
  <div class="col-md-2">
    <select class="form-select" name="confidence_level">
      <option value="">Confidence</option>
      {% for level in ['high','medium','low'] %}
      <option value="{{ level }}" {% if request.args.get('confidence_level') == level %}selected{% endif %}>{{ level }}</option>
      {% endfor %}
    </select>
  </div>
  <div class="col-md-2">
    <button class="btn btn-primary w-100">Filter</button>
  </div>
  <div class="col-md-2">
    <a class="btn btn-outline-secondary w-100" href="{{ url_for('review_queue') }}">Reset</a>
  </div>
</form>

<div class="table-responsive">
<table class="table table-hover align-middle">
  <thead>
    <tr>
      <th>Domain</th>
      <th>Vendor</th>
      <th>Category</th>
      <th>Filter</th>
      <th>Confidence</th>
      <th>Recommendation</th>
      <th>Explain</th>
      <th>Actions</th>
    </tr>
  </thead>
  <tbody>
    {% for row in rows %}
    {% set conf = row.get('Confidence', 0) %}
    {% set rec = row.get('Recommendation', 'unknown') %}
    <tr>
      <td><code>{{ row.get('Domain','') }}</code><div class="small text-muted">Seen: {{ row.get('Seen','') }} | Root: {{ row.get('Root','') }}</div></td>
      <td>{{ normalize_unknown(row.get('Suggested Vendor'), 'Needs selection') }}</td>
      <td><span class="badge bg-secondary">{{ normalize_unknown(row.get('Suggested Category'), 'Needs selection') }}</span></td>
      <td><span class="badge bg-light text-dark border">{{ normalize_unknown(row.get('Suggested Filter'), 'Needs selection') }}</span></td>
      <td style="min-width: 150px">
        <div class="small mb-1">{{ conf }} / 100 <span class="badge bg-secondary">{{ confidence_level(conf) }}</span></div>
        <div class="progress" style="height: 8px">
          <div class="progress-bar" role="progressbar" style="width: {{ conf }}%"></div>
        </div>
      </td>
      <td><span class="badge bg-{{ recommendation_badge(rec) }}">{{ rec }}</span></td>
      <td>
        <button class="btn btn-sm btn-outline-info" type="button" data-bs-toggle="collapse" data-bs-target="#explain-{{ loop.index }}">Explain</button>
      </td>
      <td class="text-nowrap">
        <form class="d-inline" method="post" action="{{ url_for('review_queue_action', domain=row.get('Domain',''), action='approved') }}">
          <input type="hidden" name="next" value="{{ request.full_path }}"><button class="btn btn-sm btn-success">Approve</button>
        </form>
        <form class="d-inline" method="post" action="{{ url_for('review_queue_action', domain=row.get('Domain',''), action='rejected') }}">
          <input type="hidden" name="next" value="{{ request.full_path }}"><button class="btn btn-sm btn-outline-danger">Reject</button>
        </form>
        <form class="d-inline" method="post" action="{{ url_for('review_queue_action', domain=row.get('Domain',''), action='ignored') }}">
          <input type="hidden" name="next" value="{{ request.full_path }}"><button class="btn btn-sm btn-outline-secondary">Ignore</button>
        </form>
      </td>
    </tr>
    <tr class="collapse" id="explain-{{ loop.index }}">
      <td colspan="8">
        <div class="card card-body bg-light">
          <strong>Analyzer Explanation</strong>
          <ul class="mb-0 mt-2">
            {% for reason in explain_suggestion(row) %}<li>{{ reason }}</li>{% endfor %}
          </ul>
        </div>
      </td>
    </tr>
    {% else %}
    <tr><td colspan="8" class="text-center text-muted py-4">No suggestions found.</td></tr>
    {% endfor %}
  </tbody>
</table>
</div>
{% endblock %}
''', encoding="utf-8")

test.write_text(r'''from web.app import app


def test_v170_stage3_review_queue_template_has_badges_and_explain():
    row = {
        "Domain": "example.test",
        "Seen": "10",
        "Root": "example.test",
        "Suggested Vendor": "Unknown",
        "Suggested Category": "Telemetry",
        "Suggested Filter": "telemetry",
        "Confidence": "65",
        "Recommendation": "review",
        "Reasons": "matched test; confidence test",
    }
    with app.test_request_context("/review-queue"):
        html = app.jinja_env.get_template("review_queue.html").render(
            t=lambda key: key,
            current_lang="en",
            html_dir="ltr",
            other_lang="ar",
            rows=[row],
            stats={},
            vendors=[],
            categories=[],
            filters=[],
        )
    assert "Total Suggestions" in html
    assert "Needs Review" in html
    assert "65 / 100" in html
    assert "Analyzer Explanation" in html
    assert "Needs selection" in html
''', encoding="utf-8")

version.write_text("1.7.0-stage3\n", encoding="utf-8")
print("OK: v1.7.0-stage3 Review Queue UX applied")
print("Next: python -m py_compile web/app.py && pytest -q")
