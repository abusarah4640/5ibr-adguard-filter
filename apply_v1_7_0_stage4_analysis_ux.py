from pathlib import Path

template = Path("web/templates/analysis.html")

template.write_text(r'''{% extends "base.html" %}
{% block content %}
<h1 class="mb-2">{{ t('analysis') if t else 'Analysis' }}</h1>
<p class="text-muted mb-4">Analyze and filter suggestions generated from the latest query log report.</p>

<div class="row g-3 mb-4">
  <div class="col-md-3">
    <div class="card"><div class="card-body">
      <h5>Total Suggestions</h5>
      <div class="display-6">{{ stats.total }}</div>
      <small class="text-muted">After filter: {{ rows|length }}</small>
    </div></div>
  </div>
  <div class="col-md-3">
    <div class="card"><div class="card-body">
      <h5>Review</h5>
      <div class="display-6">{{ stats.review }}</div>
      <small class="text-muted">Needs human review</small>
    </div></div>
  </div>
  <div class="col-md-3">
    <div class="card"><div class="card-body">
      <h5>Unknown</h5>
      <div class="display-6">{{ stats.unknown }}</div>
      <small class="text-muted">Needs rules</small>
    </div></div>
  </div>
  <div class="col-md-3">
    <div class="card"><div class="card-body">
      <h5>Average Confidence</h5>
      <div class="display-6">{{ stats.avg_confidence }}</div>
      <small class="text-muted">High: {{ stats.high_confidence }}</small>
    </div></div>
  </div>
</div>

<form class="card card-body mb-4" method="get">
  <div class="row g-2">
    <div class="col-md-3">
      <input class="form-control" name="q" value="{{ request.args.get('q','') }}" placeholder="Search domain, vendor, text">
    </div>
    <div class="col-md-2">
      <select class="form-select" name="vendor">
        <option value="">Vendor</option>
        {% for v in vendors %}
        <option value="{{ v }}" {% if request.args.get('vendor') == v %}selected{% endif %}>{{ v }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="col-md-2">
      <select class="form-select" name="category">
        <option value="">Category</option>
        {% for c in categories %}
        <option value="{{ c }}" {% if request.args.get('category') == c %}selected{% endif %}>{{ c }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="col-md-2">
      <select class="form-select" name="recommendation">
        <option value="">Recommendation</option>
        {% for r in recommendations %}
        <option value="{{ r }}" {% if request.args.get('recommendation') == r %}selected{% endif %}>{{ r }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="col-md-1">
      <input class="form-control" name="min_confidence" value="{{ request.args.get('min_confidence','') }}" placeholder="Min">
    </div>
    <div class="col-md-2">
      <button class="btn btn-primary w-100">Filter</button>
    </div>
  </div>
</form>

<div class="row g-3 mb-4">
  <div class="col-md-3"><div class="card"><div class="card-body"><h5>Top Vendors</h5>{% for k,v in top_vendors %}<div class="d-flex justify-content-between"><span>{{ k }}</span><strong>{{ v }}</strong></div>{% endfor %}</div></div></div>
  <div class="col-md-3"><div class="card"><div class="card-body"><h5>Top Categories</h5>{% for k,v in top_categories %}<div class="d-flex justify-content-between"><span>{{ k }}</span><strong>{{ v }}</strong></div>{% endfor %}</div></div></div>
  <div class="col-md-3"><div class="card"><div class="card-body"><h5>Top Filters</h5>{% for k,v in top_filters %}<div class="d-flex justify-content-between"><span>{{ k }}</span><strong>{{ v }}</strong></div>{% endfor %}</div></div></div>
  <div class="col-md-3"><div class="card"><div class="card-body"><h5>Recommendations</h5>{% for k,v in top_recommendations %}<div class="d-flex justify-content-between"><span class="badge bg-{{ recommendation_badge(k) }}">{{ k }}</span><strong>{{ v }}</strong></div>{% endfor %}</div></div></div>
</div>

<div class="card">
  <div class="card-header d-flex justify-content-between">
    <strong>Suggestions</strong>
    <span>{{ rows|length }} shown</span>
  </div>
  <div class="table-responsive">
    <table class="table table-striped table-hover align-middle mb-0">
      <thead>
        <tr>
          <th>Domain</th>
          <th>Seen</th>
          <th>Vendor</th>
          <th>Category</th>
          <th>Filter</th>
          <th>Confidence</th>
          <th>Recommendation</th>
          <th>Reasons</th>
        </tr>
      </thead>
      <tbody>
        {% for row in rows %}
        {% set conf = row.get('Confidence', 0)|int %}
        <tr>
          <td><strong>{{ row.get('Domain','') }}</strong><br><small class="text-muted">{{ row.get('Root','') }}</small></td>
          <td>{{ row.get('Seen','') }}</td>
          <td>{{ normalize_unknown(row.get('Suggested Vendor'), 'Needs selection') }}</td>
          <td>{{ normalize_unknown(row.get('Suggested Category'), 'Needs selection') }}</td>
          <td>{{ normalize_unknown(row.get('Suggested Filter'), 'Needs selection') }}</td>
          <td style="min-width:140px">
            <div>{{ conf }} / 100</div>
            <div class="progress" style="height:8px">
              <div class="progress-bar" style="width: {{ conf }}%"></div>
            </div>
          </td>
          <td><span class="badge bg-{{ recommendation_badge(row.get('Recommendation')) }}">{{ row.get('Recommendation','unknown') }}</span></td>
          <td>
            <details>
              <summary>Explain</summary>
              <ul class="mb-0">
                {% for reason in explain_suggestion(row) %}
                <li>{{ reason }}</li>
                {% endfor %}
              </ul>
            </details>
          </td>
        </tr>
        {% else %}
        <tr><td colspan="8" class="text-center text-muted">No suggestions found.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
''', encoding="utf-8")

test = Path("tests/test_web_v170_stage4_analysis_ux.py")
test.write_text(r'''from web.app import app


def test_v170_stage4_analysis_template_uses_badges_and_explain():
    row = {
        "Domain": "beacons2.gvt2.com",
        "Seen": "10",
        "Root": "gvt2.com",
        "Suggested Vendor": "Google",
        "Suggested Category": "Telemetry",
        "Suggested Filter": "telemetry",
        "Confidence": "65",
        "Recommendation": "review",
        "Reasons": "matched vendor; matched telemetry keyword",
    }

    with app.test_request_context("/analysis"):
        html = app.jinja_env.get_template("analysis.html").render(
            t=lambda key: key,
            rows=[row],
            stats={
                "total": 1,
                "review": 1,
                "unknown": 0,
                "avg_confidence": 65,
                "high_confidence": 0,
            },
            vendors=["Google"],
            categories=["Telemetry"],
            recommendations=["review"],
            top_vendors=[("Google", 1)],
            top_categories=[("Telemetry", 1)],
            top_filters=[("telemetry", 1)],
            top_recommendations=[("review", 1)],
        )

    assert "65 / 100" in html
    assert "Explain" in html
    assert "matched vendor" in html
    assert "bg-warning" in html
''', encoding="utf-8")

print("OK: v1.7.0-stage4 Analysis Dashboard UX applied")
