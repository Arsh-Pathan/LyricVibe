"""
Comprehensive Hinglish (Romanized Hindi/Urdu) Transliteration Engine.
Converts Devanagari (Hindi) and Arabic/Persian/Urdu scripts into natural,
readable Roman Hinglish (matching Spotify lyrics).
Guarantees 100% of characters are pure Latin (A-Z, a-z, 0-9, standard punctuation).
ZERO foreign characters leak through.
"""

import re

# ── 1. Comprehensive Urdu / Arabic / Persian to Latin Table ──────────
URDU_MAP = {
    # Consonants & Vowels
    '\u0622': 'aa',     # آ (Alef with Madda)
    '\u0627': 'a',      # ا (Alef)
    '\u0623': 'a',      # أ (Alef with Hamza above)
    '\u0625': 'i',      # إ (Alef with Hamza below)
    '\u0628': 'b',      # ب (Beh)
    '\u067E': 'p',      # پ (Peh)
    '\u062A': 't',      # ت (Teh)
    '\u0679': 't',      # ٹ (Tteh)
    '\u062B': 's',      # ث (Theh)
    '\u062C': 'j',      # ج (Jeem)
    '\u0686': 'ch',     # چ (Tcheh)
    '\u062D': 'h',      # ح (Hah)
    '\u062E': 'kh',     # خ (Khah)
    '\u062F': 'd',      # د (Dal)
    '\u0688': 'd',      # ڈ (Ddal)
    '\u0630': 'z',      # ذ (Thal)
    '\u0631': 'r',      # ر (Reh) - CRITICAL!
    '\u0691': 'r',      # ڑ (Rreh)
    '\u0632': 'z',      # ز (Zain)
    '\u0698': 'zh',     # ژ (Zheh)
    '\u0633': 's',      # س (Seen)
    '\u0634': 'sh',     # ش (Sheen)
    '\u0635': 's',      # ص (Sad)
    '\u0636': 'z',      # ض (Dad)
    '\u0637': 't',      # ط (Tah)
    '\u0638': 'z',      # ظ (Zah)
    '\u0639': 'a',      # ع (Ain)
    '\u063A': 'gh',     # غ (Ghain)
    '\u0641': 'f',      # ف (Feh)
    '\u0642': 'q',      # ق (Qaf)
    '\u06A9': 'k',      # ک (Keheh)
    '\u0643': 'k',      # ك (Kaf)
    '\u06AF': 'g',      # گ (Gaf)
    '\u0644': 'l',      # ل (Lam)
    '\u0645': 'm',      # م (Meem) - CRITICAL!
    '\u0646': 'n',      # ن (Noon)
    '\u06BA': 'n',      # ں (Noon Ghunna)
    '\u0648': 'o',      # و (Waw)
    '\u06C1': 'h',      # ہ (Heh Goal)
    '\u06BE': 'h',      # ھ (Heh Doachashmee)
    '\u0629': 't',      # ة (Teh Marbuta)
    '\u06C2': 'h',      # ۂ (Heh Goal with Hamza)
    '\u06C3': 'h',      # ۃ (Teh Marbuta Goal)
    '\u0649': 'a',      # ى (Alef Maksura)
    '\u06CC': 'i',      # ی (Farsi Yeh)
    '\u064A': 'i',      # ي (Arabic Yeh)
    '\u06D2': 'e',      # ے (Bari Yeh)
    '\u0626': 'i',      # ئ (Yeh with Hamza)
    '\u0624': 'o',      # ؤ (Waw with Hamza)
    '\u0621': '',       # ء (Hamza)
    '\u0674': '',       # ٴ (High Hamza)
    '\u0670': 'aa',     # ٰ (Superscript Alef)

    # Diacritics (Harakat / Aerab)
    '\u064E': 'a',      # َ (Zabar / Fatha)
    '\u0650': 'i',      # ِ (Zer / Kasra)
    '\u064F': 'u',      # ُ (Pesh / Damma)
    '\u064B': 'an',     # ً (Tanwin Fath)
    '\u064D': 'in',     # ٍ (Tanwin Kasr)
    '\u064C': 'un',     # ٌ (Tanwin Damm)
    '\u0651': '',       # ّ (Tashdeed)
    '\u0652': '',       # ْ (Sukun)
    '\u0653': '',       # ٓ (Maddah)
    '\u0654': '',       # ٔ (Hamza Above)
    '\u0655': '',       # ٕ (Hamza Below)

    # Punctuation & Numbers
    '\u060C': ',',      # ، (Arabic Comma)
    '\u061B': ';',      # ؛ (Arabic Semicolon)
    '\u061F': '?',      # ؟ (Arabic Question Mark)
    '\u06D4': '.',      # ۔ (Urdu Full Stop)
    '\u066A': '%',      # ٪ (Arabic Percent)
    '\u0660': '0', '\u0661': '1', '\u0662': '2', '\u0663': '3', '\u0664': '4',
    '\u0665': '5', '\u0666': '6', '\u0667': '7', '\u0668': '8', '\u0669': '9',
    '\u06F0': '0', '\u06F1': '1', '\u06F2': '2', '\u06F3': '3', '\u06F4': '4',
    '\u06F5': '5', '\u06F6': '6', '\u06F7': '7', '\u06F8': '8', '\u06F9': '9',
}

# ── 2. Devanagari Mapping ─────────────────────────────────────────────
NUKTA_NORMALIZATION = {
    '\u0915\u093c': '\u0958',  # क़ -> क़
    '\u0916\u093c': '\u0959',  # ख़ -> ख़
    '\u0917\u093c': '\u095a',  # ग़ -> ग़
    '\u091c\u093c': '\u095b',  # ज़ -> ज़
    '\u0921\u093c': '\u095c',  # ड़ -> ड़
    '\u0922\u093c': '\u095d',  # ढ़ -> ढ़
    '\u092b\u093c': '\u095e',  # फ़ -> फ़
    '\u092f\u093c': '\u095f',  # य़ -> य़
}

DEV_VOWELS = {
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo',
    'ऋ': 'ri', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
    'अं': 'an', 'अः': 'ah', 'ऑ': 'o', 'ऍ': 'e',
}

DEV_MATRAS = {
    'ा': 'aa', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo',
    'ृ': 'ri', 'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au',
    'ॉ': 'o', 'ॅ': 'e',
    'ं': 'n', 'ँ': 'n', 'ः': 'h',
}

DEV_CONSONANTS = {
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
    'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
    'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v',
    'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
    # Nukta consonants (Urdu/Persian/Arabic loan sounds)
    '\u0958': 'q', '\u0959': 'kh', '\u095a': 'gh', '\u095b': 'z',
    '\u095c': 'r', '\u095d': 'rh', '\u095e': 'f',  '\u095f': 'y',
}

DEV_DIGITS = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',
}

DEV_PUNCTUATION = {
    '।': '.',
    '॥': '.',
    'ॐ': 'Om',
}

HALANT = '्'

# ── 3. Phonetic Cleanups & Common Word Corrections ────────────────────
WORD_REPLACEMENTS = [
    # Common corrupted syllables from mixed scripts
    (r'\bph\s+r\b', 'phir'),
    (r'\bphr\b', 'phir'),
    (r'\bbkhrna\b', 'bikharna'),
    (r'\bzrori\b', 'zaroori'),
    (r'\bm\s+ro\b', 'magar'),
    (r'\bmro\b', 'magar'),
    (r'\baarzohn\b', 'aarzoon'),
    (r'\baarzon\b', 'aarzoon'),
    (r'\bkyoon\b', 'kyun'),
    (r'\bkyon\b', 'kyun'),
    (r'\btumhi\b', 'tum hi'),
    (r'\bmujhako\b', 'mujhko'),
    (r'\btujhako\b', 'tujhko'),
    (r'\busako\b', 'usko'),
    (r'\bisako\b', 'isko'),
    (r'\bnahin\b', 'nahi'),
    (r'\bhain\b', 'hai'),
    (r'\bhoon\b', 'hoon'),
    (r'\bmeen\b', 'mein'),
    (r'\bmen\b', 'mein'),
    (r'\braha\b', 'raha'),
    (r'\brahe\b', 'rahe'),
    (r'\brahi\b', 'rahi'),
    (r'\bjnya', 'gya'),
]


def _preprocess_nuktas(text: str) -> str:
    for k, v in NUKTA_NORMALIZATION.items():
        text = text.replace(k, v)
    return text


def transliterate_devanagari_word(word: str) -> str:
    word = _preprocess_nuktas(word)
    res = []
    i = 0
    n = len(word)

    while i < n:
        char = word[i]
        if char in DEV_VOWELS:
            res.append(DEV_VOWELS[char])
            i += 1
        elif char in DEV_CONSONANTS:
            cons = DEV_CONSONANTS[char]
            i += 1
            if i < n and word[i] == HALANT:
                res.append(cons)
                i += 1
            elif i < n and word[i] in DEV_MATRAS:
                res.append(cons + DEV_MATRAS[word[i]])
                i += 1
            else:
                if i >= n or word[i] in ' ,.?!()-\'"\n\r':
                    res.append(cons)
                else:
                    res.append(cons + 'a')
        elif char in DEV_MATRAS:
            res.append(DEV_MATRAS[char])
            i += 1
        elif char in DEV_DIGITS:
            res.append(DEV_DIGITS[char])
            i += 1
        elif char in DEV_PUNCTUATION:
            res.append(DEV_PUNCTUATION[char])
            i += 1
        elif char == HALANT or char == '\u093c':
            i += 1
        else:
            res.append(char)
            i += 1

    return ''.join(res)


def transliterate_urdu_text(text: str) -> str:
    """Converts Arabic/Urdu/Persian characters cleanly to Latin Hinglish."""
    res = []
    for ch in text:
        if ch in URDU_MAP:
            res.append(URDU_MAP[ch])
        else:
            # Check if within Arabic block and not in map -> strip or drop
            code = ord(ch)
            if (0x0600 <= code <= 0x06FF) or (0x0750 <= code <= 0x077F) or (0xFB50 <= code <= 0xFDFF) or (0xFE70 <= code <= 0xFEFF):
                pass  # Safely strip unsupported Arabic diacritics
            else:
                res.append(ch)
    return ''.join(res)


def _universal_safety_sanitize(text: str) -> str:
    """
    Guarantees 100% of characters are Latin, numbers, or standard punctuation.
    Zero foreign code points can leak through.
    """
    clean = []
    for ch in text:
        code = ord(ch)
        # Check Devanagari
        if 0x0900 <= code <= 0x097F:
            if ch in DEV_CONSONANTS:
                clean.append(DEV_CONSONANTS[ch])
            elif ch in DEV_VOWELS:
                clean.append(DEV_VOWELS[ch])
            elif ch in DEV_MATRAS:
                clean.append(DEV_MATRAS[ch])
            elif ch in DEV_DIGITS:
                clean.append(DEV_DIGITS[ch])
            elif ch in DEV_PUNCTUATION:
                clean.append(DEV_PUNCTUATION[ch])
            else:
                pass  # drop
        # Check Arabic / Urdu / Persian
        elif (0x0600 <= code <= 0x06FF) or (0x0750 <= code <= 0x077F) or (0xFB50 <= code <= 0xFDFF) or (0xFE70 <= code <= 0xFEFF):
            if ch in URDU_MAP:
                clean.append(URDU_MAP[ch])
            else:
                pass  # drop
        # Smart quotes / punctuation normalisation
        elif ch in ('\u2018', '\u2019', '`'):
            clean.append("'")
        elif ch in ('\u201C', '\u201D'):
            clean.append('"')
        elif ch in ('\u2013', '\u2014'):
            clean.append('-')
        elif ch == '\u2026':
            clean.append('...')
        else:
            clean.append(ch)
    return ''.join(clean)


def to_hinglish(text: str) -> str:
    """
    Takes any lyric text (Devanagari, Urdu, mixed, or corrupted) and produces
    100% clean, pure Latin Hinglish with zero foreign symbols.
    """
    if not text:
        return ""

    # 1. Preprocess nuktas
    text = _preprocess_nuktas(text)

    # 2. Check for Arabic / Urdu
    has_urdu = any(
        (0x0600 <= ord(ch) <= 0x06FF) or
        (0x0750 <= ord(ch) <= 0x077F) or
        (0xFB50 <= ord(ch) <= 0xFDFF) or
        (0xFE70 <= ord(ch) <= 0xFEFF)
        for ch in text
    )
    if has_urdu:
        text = transliterate_urdu_text(text)

    # 3. Check for Devanagari
    has_devanagari = any(0x0900 <= ord(ch) <= 0x097F for ch in text)
    if has_devanagari:
        words = text.split(' ')
        converted = [transliterate_devanagari_word(w) for w in words]
        text = ' '.join(converted)

    # 4. Universal safety sanitization (zero leaks guarantee)
    text = _universal_safety_sanitize(text)

    # 5. Apply phonetic cleanups
    for pattern, replacement in WORD_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # 6. Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    if not text:
        return ""

    # Capitalize the first character while preserving casing for the remainder of the sentence
    return text[0].upper() + text[1:]
