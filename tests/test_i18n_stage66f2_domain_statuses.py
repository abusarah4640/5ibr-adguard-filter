from pathlib import Path


TEMPLATES = Path(__file__).resolve().parents[1] / "web" / "templates"


def test_domain_status_options_keep_internal_values_and_translate_labels():
    for template_name in ("domains.html", "domain_form.html"):
        body = (TEMPLATES / template_name).read_text(encoding="utf-8")
        assert 'value="Approved"' in body
        assert 'value="Pending"' in body
        assert 'value="Rejected"' in body
        assert "{{ t('approved') }}" in body
        assert "{{ t('pending') }}" in body
        assert "{{ t('rejected') }}" in body
        assert ">Approved</option>" not in body
        assert ">Pending</option>" not in body
        assert ">Rejected</option>" not in body


def test_domains_table_translates_known_statuses_without_changing_unknown_values():
    body = (TEMPLATES / "domains.html").read_text(encoding="utf-8")
    assert "{% set display_status = row.Status or 'Approved' %}" in body
    assert "t(display_status|lower)" in body
    assert "else display_status" in body
    assert "<td>{{ row.Status or 'Approved' }}</td>" not in body
