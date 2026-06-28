from pathlib import Path


FILTERS_DIR = Path("filters")


def get_rules(path):

    rules = []

    with open(path, encoding="utf-8") as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            if line.startswith("!"):
                continue

            rules.append(line)

    return rules


def test_no_duplicate_rules():

    duplicates = []

    for file in FILTERS_DIR.glob("*.txt"):

        rules = get_rules(file)

        seen = set()

        for rule in rules:

            if rule in seen:
                duplicates.append(
                    f"{file.name}: {rule}"
                )

            seen.add(rule)

    assert not duplicates, "\n".join(duplicates)


def test_rules_are_sorted():

    for file in FILTERS_DIR.glob("*.txt"):

        rules = get_rules(file)

        assert rules == sorted(rules), \
            f"{file.name} contains unsorted rules."