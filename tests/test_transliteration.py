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
        assert out.lower().startswith(expected.lower()[:3]), (
            f"Expected {expected}, got {out}"
        )


def test_nukta_consonants():
    # Test both composed and decomposed Devanagari nuktas
    decomposed_qareeb = "\u0915\u093c\u0930\u0940\u092c"  # क़रीब
    composed_qareeb = "\u0958\u0930\u0940\u092c"  # क़रीब
    assert to_hinglish(decomposed_qareeb) == "Qareeb"
    assert to_hinglish(composed_qareeb) == "Qareeb"

    decomposed_zara = "\u091c\u093c\u0930\u093e"  # ज़रा
    composed_zara = "\u095b\u0930\u093e"  # ज़रा
    assert to_hinglish(decomposed_zara) == "Zaraa"
    assert to_hinglish(composed_zara) == "Zaraa"

    decomposed_faasle = "\u092b\u093c\u093e\u0938\u0932\u0947"  # फ़ासले
    composed_faasle = "\u095e\u093e\u0938\u0932\u0947"  # फ़ासले
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
        assert is_pure_ascii(out), (
            f"Urdu transliteration leaked foreign characters: {out}"
        )


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


def test_devanagari_digits():
    out = to_hinglish("गीत १२३ और २०2४")
    assert "123" in out
    assert "20" in out
    assert is_pure_ascii(out)


def test_devanagari_punctuation_danda():
    out = to_hinglish("दिलबर जानी।")
    assert out.endswith(".")
    assert is_pure_ascii(out)


def test_devanagari_ligatures_and_om():
    assert to_hinglish("ज्ञान").startswith("Gya")
    assert "Om" in to_hinglish("ॐ नमः शिवाय")
    assert is_pure_ascii(to_hinglish("ॐ नमः शिवाय"))


def test_devanagari_common_bollywood_words():
    assert to_hinglish("नहीं") == "Nahi"
    assert to_hinglish("ज़िंदगी") == "Zindagi"
    assert to_hinglish("कभी") == "Kabhi"
    assert to_hinglish("भी") == "Bhi"
    assert to_hinglish("की") == "Ki"
    assert to_hinglish("मेरी") == "Meri"
    assert to_hinglish("तेरी") == "Teri"


def test_devanagari_multiline_whitespace():
    out = to_hinglish("दिल\nदीवाना")
    assert "Dil" in out
    assert "deevaanaa" in out.lower()
    assert is_pure_ascii(out)


def test_gurmukhi_punjabi_transliteration():
    # Gurmukhi script transliterates cleanly to 100% pure Latin ASCII
    samples = [
        ("ਦਿਲਬਰ", "Dilabar"),
        ("ਤੇਰੇ ਵਾਸਤੇ", "Tere vaasate"),
        ("ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ", "Sati sree akaal"),
        ("ਪਿਆਰ", "Piaar"),
    ]
    for gur, expected in samples:
        out = to_hinglish(gur)
        assert is_pure_ascii(out), f"Gurmukhi transliteration leaked non-ASCII: {out}"
        assert out.lower().startswith(expected.lower()[:4]), (
            f"Expected {expected}, got {out}"
        )


def test_invisible_zero_width_and_bidi_characters():
    # Devanagari and Urdu lyrics with ZWNJ, ZWJ, LRM, RLM, and BOM
    contaminated = "ਦਿਲ\u200cਬਰ ਅਤੇ \u200eਜ਼ਿੰਦਗੀ\u200d \ufeffप्यार"
    out = to_hinglish(contaminated)
    assert is_pure_ascii(out)
    assert "\u200c" not in out
    assert "\u200d" not in out
    assert "\u200e" not in out


def test_bengali_transliteration():
    # Bengali lyrics transliterate cleanly to 100% pure Latin ASCII
    samples = [
        ("তুমি", "Tumi"),
        ("ভালোবাসা", "Bhaalobaasaa"),
        ("আমার পরাণ", "Aamaar paraan"),
        ("গান", "Gaan"),
    ]
    for ben, expected in samples:
        out = to_hinglish(ben)
        assert is_pure_ascii(out), f"Bengali transliteration leaked non-ASCII: {out}"
        assert out.lower().startswith(expected.lower()[:3]), (
            f"Expected {expected}, got {out}"
        )


def test_gujarati_transliteration():
    # Gujarati lyrics transliterate cleanly to 100% pure Latin ASCII
    samples = [
        ("તમે", "Tame"),
        ("પ્રેમ", "Prem"),
        ("મારી જિંદગી", "Maari jindagee"),
        ("ગીત", "Geet"),
    ]
    for guj, expected in samples:
        out = to_hinglish(guj)
        assert is_pure_ascii(out), f"Gujarati transliteration leaked non-ASCII: {out}"
        assert out.lower().startswith(expected.lower()[:3]), (
            f"Expected {expected}, got {out}"
        )


def test_tamil_transliteration():
    # Tamil lyrics transliterate cleanly to 100% pure Latin ASCII
    samples = [
        ("அன்பு", "Anbu"),
        ("காதல்", "Kaathal"),
        ("பாடல்", "Paadal"),
        ("வணக்கம்", "Vanakam"),
    ]
    for tam, expected in samples:
        out = to_hinglish(tam)
        assert is_pure_ascii(out), f"Tamil transliteration leaked non-ASCII: {out}"
        assert out.lower().startswith(expected.lower()[:2]), (
            f"Expected {expected}, got {out}"
        )


def test_telugu_transliteration():
    # Telugu lyrics transliterate cleanly to 100% pure Latin ASCII
    samples = [
        ("ప్రేమ", "Prema"),
        ("పాట", "Paata"),
        ("మనసు", "Manasu"),
        ("హృదయం", "Hrudayam"),
    ]
    for tel, expected in samples:
        out = to_hinglish(tel)
        assert is_pure_ascii(out), f"Telugu transliteration leaked non-ASCII: {out}"
        assert out.lower().startswith(expected.lower()[:2]), (
            f"Expected {expected}, got {out}"
        )
    assert "\ufeff" not in out
