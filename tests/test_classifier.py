from scripts.classifier import DomainClassifier


def test_signature():

    classifier = DomainClassifier()

    result = classifier.classify(
        "mobile.events.data.microsoft.com"
    )

    assert result["category"] == "telemetry"

    assert result["confidence"] == 100


def test_unknown():

    classifier = DomainClassifier()

    result = classifier.classify(
        "unknown.example.com"
    )

    assert result["category"] == "unknown"