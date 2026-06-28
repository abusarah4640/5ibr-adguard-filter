from scripts.filter_loader import load_existing_rules


def test_loader():

    rules = load_existing_rules()

    assert isinstance(rules, set)