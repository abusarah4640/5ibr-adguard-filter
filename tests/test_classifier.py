from scripts.classifier import DomainClassifier


classifier = DomainClassifier()


def test_google():

    result = classifier.classify(
        "firebaseinstallations.googleapis.com"
    )

    assert result["vendor"] == "Google"

    assert result["category"] == "telemetry"

    assert result["confidence"] == 100


def test_microsoft():

    result = classifier.classify(
        "mobile.events.data.microsoft.com"
    )

    assert result["vendor"] == "Microsoft"

    assert result["category"] == "telemetry"

    assert result["confidence"] == 100


def test_unknown():

    result = classifier.classify(
        "example.org"
    )

    assert result["vendor"] == "Unknown"

    assert result["category"] == "unknown"