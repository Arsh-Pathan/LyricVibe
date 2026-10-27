"""Tests for Hinglish transliteration engine."""

import re

from lyricvibe.core.transliteration import to_hinglish


def is_pure_ascii(text: str) -> bool:
    """Returns True if the text contains only ASCII characters and standard punctuation."""
    return all(ord(c) < 128 for c in text)


def test_devanagari_basic():
    cases = [
        ("दिलबर", "Dilabar"),
        ("तुम्हारी", "Tumhaaree"),
        ("मोहब्बत", "Mohabbat"),
        ("आसमान", "Aasamaan"),
        ("प्यार", "Pyaar"),
    ]
    for dev, expected in cases:
        out = to_hinglish(dev)
        assert is_pure_ascii(out), f"Output contains non-ASCII characters: {out}"
        assert out.lower().startswith(expected.lower()[:3]), f"Expected {expected}, got {out}"


def test_nukta_consonants():
    # Test both composed and decomposed Devanagari nuktas
    decomposed_qareeb = "\u0915\u093c\u0930\u0940\u092c"  # क़रीब
    composed_qareeb = "\u0958\u0930\u0940\u092c"          # क़रीब
    assert to_hinglish(decomposed_qareeb) == "Qareeb"
    assert to_hinglish(composed_qareeb) == "Qareeb"

    decomposed_zara = "\u091c\u093c\u0930\u093e"          # ज़रा
    composed_zara = "\u095b\u0930\u093e"                  # ज़रा
    assert to_hinglish(decomposed_zara) == "Zaraa"
    assert to_hinglish(composed_zara) == "Zaraa"

    decomposed_faasle = "\u092b\u093c\u093e\u0938\u0932\u0947"  # फ़ासले
    composed_faasle = "\u095e\u093e\u0938\u0932\u0947"          # फ़ासले
    assert to_hinglish(decomposed_faasle).startswith("F")
    assert to_hinglish(composed_faasle).startswith("F")


def test_urdu_script():
    urdu_samples = [
        "اگر",
        "محبت",
        "زندگی",
        "دل",
        "خواب",
    ]
    for sample in urdu_samples:
        out = to_hinglish(sample)
        assert len(out) > 0
        assert is_pure_ascii(out), f"Urdu transliteration leaked foreign characters: {out}"


def test_zero_leak_guarantee():
    # Complex mixed string with Devanagari, Urdu, and punctuation
    text = "ज़िंदगी ग़म का दरिया है... اور پھر ہار گئے (2024)"
    out = to_hinglish(text)
    assert is_pure_ascii(out)
    assert not re.search(r"[\u0600-\u06FF\u0900-\u097F]", out)


def test_phonetic_cleanups():
    assert "phir" in to_hinglish("ph r").lower()
    assert "bikharna" in to_hinglish("bkhrna").lower()
    assert "zaroori" in to_hinglish("zrori").lower()
    assert "kyun" in to_hinglish("kyoon").lower()
    assert "mein" in to_hinglish("meen").lower()


def test_pure_english_preservation():
    english_line = "Cause you knew that I'd be at one"
    out = to_hinglish(english_line)
    assert out == english_line


def test_empty_and_whitespace():
    assert to_hinglish("") == ""
    assert to_hinglish("   ") == ""
    assert to_hinglish(None) == ""
