from pathlib import Path

from PIL import Image

from aries.classifier import ImageClassifier
from aries.config_loader import load_config


def _image(path: Path) -> Path:
    Image.new("RGB", (8, 8), color=(10, 20, 30)).save(path)
    return path


def test_mock_classification_loads(tmp_path):
    config = load_config()
    classifier = ImageClassifier(config)
    result = classifier.classify(_image(tmp_path / "random_object.jpg"), "mock")
    assert result.entity_type == "non_threat_object"


def test_puppy_non_threat(tmp_path):
    result = ImageClassifier(load_config()).classify(_image(tmp_path / "puppy.jpg"), "mock")
    assert result.threat_level == 1
    assert result.entity_type == "non_threat_animal"


def test_friendly_soldier_not_enemy(tmp_path):
    result = ImageClassifier(load_config()).classify(_image(tmp_path / "friendly_soldier.jpg"), "mock")
    assert result.allegiance == "friendly"
    assert result.threat_level == 1


def test_enemy_drone_high_threat(tmp_path):
    result = ImageClassifier(load_config()).classify(_image(tmp_path / "enemy_drone.jpg"), "mock")
    assert result.entity_type == "enemy_drone"
    assert result.threat_level >= 6


def test_invalid_input_falls_back():
    result = ImageClassifier(load_config()).classify(Path("does_not_exist.jpg"), "mock")
    assert result.entity_type == "unknown_contact"
    assert result.confidence == 0.2

