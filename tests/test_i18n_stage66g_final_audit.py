import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "web" / "i18n.py"
TEMPLATES = ROOT / "web" / "templates"


def _translations() -> dict[str, dict[str, str]]:
    module = ast.parse(I18N.read_text(encoding="utf-8"))
    for node in module.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "TRANSLATIONS"
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("TRANSLATIONS was not found in web/i18n.py")


def _literal_template_keys() -> set[str]:
    pattern = re.compile(r"\bt\(\s*(['\"])([a-z0-9_]+)\1")
    keys: set[str] = set()
    for template in TEMPLATES.glob("*.html"):
        body = template.read_text(encoding="utf-8")
        for match in pattern.finditer(body):
            suffix = body[match.end():]
            if re.match(r"\s*~", suffix):
                continue
            keys.add(match.group(2))
    return keys


def test_translation_catalogs_have_identical_keys():
    translations = _translations()
    assert translations["en"].keys() == translations["ar"].keys()


def test_all_literal_template_translation_keys_exist_in_every_locale():
    translations = _translations()
    used_keys = _literal_template_keys()
    for language, catalog in translations.items():
        missing = used_keys - catalog.keys()
        assert not missing, f"Missing {language} translations: {sorted(missing)}"


def test_domains_empty_state_uses_a_real_translation_key():
    translations = _translations()
    body = (TEMPLATES / "domains.html").read_text(encoding="utf-8")
    assert "{{ t('no_results') }}" in body
    assert "else 'No results'" not in body
    assert translations["en"]["no_results"] == "No results"
    assert translations["ar"]["no_results"] == "لا توجد نتائج"
