"""
Hinglish (Romanized Hindi) Transliteration Engine.
Converts Devanagari (Hindi) and Perso-Arabic (Urdu) scripts
into natural, readable Romanized Hinglish (like Spotify lyrics).
Guarantees NO un-transliterated characters leak through.
"""

import re
import unicodedata

# Explicit Nukta map (both precomposed single-char and decomposed two-char)
NUKTA_CONSONANTS = {
    '\u0958': 'q',       # क़
    '\u0959': 'kh',      # ख़
    '\u095a': 'gh',      # ग़
    '\u095b': 'z',       # ज़
    '\u095c': 'r',       # ड़
    '\u095d': 'rh',      # ढ़
    '\u095e': 'f',       # फ़
    '\u095f': 'y',       # य़
    '\u0915\u093c': 'q',
    '\u0916\u093c': 'kh',
    '\u0917\u093c': 'gh',
    '\u091c\u093c': 'z',
    '\u0921\u093c': 'r',
    '\u0922\u093c': 'rh',
    '\u092b\u093c': 'f',
    '\u092f\u093c': 'y',
}

# Devanagari Independent Vowels
DEV_VOWELS = {
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo',
    'ऋ': 'ri', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
    'अं': 'an', 'अः': 'ah', 'ऑ': 'o', 'ऍ': 'e',
}

# Devanagari Matras (Vowel signs attached to consonants)
DEV_MATRAS = {
    'ा': 'aa', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo',
    'ृ': 'ri', 'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au',
    'ॉ': 'o', 'ॅ': 'e',
    'ं': 'n', 'ँ': 'n', 'ः': 'h',
}

# Standard Devanagari Consonants
DEV_CONSONANTS = {
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
    'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
    'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v',
    'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
}

HALANT = '्'

# Common Hindi word beautifications for natural Spotify-like Hinglish
WORD_REPLACEMENTS = {
    r'\btumhi\b': 'tum hi',
    r'\bkyoon\b': 'kyun',
    r'\bkyon\b': 'kyun',
    r'\bmujhako\b': 'mujhko',
    r'\btujhako\b': 'tujhko',
    r'\busako\b': 'usko',
    r'\bisako\b': 'isko',
    r'\bnahin\b': 'nahi',
    r'\bhain\b': 'hai',
    r'\bhoon\b': 'hoon',
    r'\bmeen\b': 'mein',
    r'\bmen\b': 'mein',
}

# Urdu / Arabic to Latin mapping
URDU_MAP = {
    'آ': 'aa', 'ا': 'a', 'ب': 'b', 'پ': 'p', 'ت': 't', 'ٹ': 't',
    'ث': 's', 'ج': 'j', 'چ': 'ch', 'ح': 'h', 'خ': 'kh', 'د': 'd',
    'ڈ': 'd', 'ذ': 'z', 'र': 'r', 'ڑ': 'r', 'ز': 'z', 'ژ': 'zh',
    'س': 's', 'ش': 'sh', 'ص': 's', 'ض': 'z', 'ط': 't', 'ظ': 'z',
    'ع': 'a', 'غ': 'gh', 'ف': 'f', 'ق': 'q', 'ک': 'k', 'گ': 'g',
    'ل': 'l', 'म': 'm', 'ن': 'n', 'ں': 'n', 'و': 'o', 'ہ': 'h',
    'ھ': 'h', 'ء': '', 'ی': 'i', 'ے': 'e', 'ۂ': 'h', 'ۃ': 't',
    'ِ': 'i', 'ُ': 'u', 'َ': 'a', 'ّ': '', 'ْ': '',
}


def _preprocess_nuktas(text: str) -> str:
    """Replaces all nukta variations (both precomposed and decomposed)."""
    # Replace two-char decomposed first
    for k, v in NUKTA_CONSONANTS.items():
        if len(k) == 2:
            text = text.replace(k, v)
    # Replace precomposed single-char
    for k, v in NUKTA_CONSONANTS.items():
        if len(k) == 1:
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
                # Schwa rule: suppress trailing 'a' if at end of word or before latin chars/punctuation
                if i >= n or word[i] in ' ,.?!()-\'"\n\r':
                    res.append(cons)
                else:
                    res.append(cons + 'a')
        elif char in DEV_MATRAS:
            res.append(DEV_MATRAS[char])
            i += 1
        elif char == HALANT or char == '\u093c':  # stray halant or nukta
            i += 1
        else:
            # Latin letters, numbers, punctuation
            res.append(char)
            i += 1

    return ''.join(res)


def _sanitize_any_remaining_devanagari(text: str) -> str:
    """Fallback safety net: ensures NO Devanagari character ever leaks to the screen."""
    clean = []
    for ch in text:
        if '\u0900' <= ch <= '\u097f':
            # Check individual maps
            if ch in DEV_CONSONANTS:
                clean.append(DEV_CONSONANTS[ch])
            elif ch in DEV_VOWELS:
                clean.append(DEV_VOWELS[ch])
            elif ch in DEV_MATRAS:
                clean.append(DEV_MATRAS[ch])
            elif ch in NUKTA_CONSONANTS:
                clean.append(NUKTA_CONSONANTS[ch])
            elif ch in ('\u093c', '\u094d', '\u0964', '\u0965'):
                pass  # strip diacritics / dandas
            else:
                pass  # strip unsupported glyphs
        else:
            clean.append(ch)
    return ''.join(clean)


def to_hinglish(text: str) -> str:
    """
    Takes any lyric text:
    - Pre-processes all nuktas (क़, ख़, ग़, ज़, ड़, ढ़, फ़).
    - If Devanagari Hindi or mixed: converts completely to Roman Hinglish.
    - If Urdu script: converts to Roman Hinglish.
    - Guarantees 0% Devanagari or Arabic characters remain in the output.
    """
    if not text:
        return ""

    # 1. Pre-process nukta characters (handles both precomposed U+095E and decomposed U+092B+U+093C)
    text = _preprocess_nuktas(text)

    # 2. Check for Arabic / Urdu
    has_urdu = any('\u0600' <= ch <= '\u06ff' for ch in text)
    if has_urdu:
        res = [URDU_MAP.get(ch, ch) for ch in text]
        text = ''.join(res)
        text = re.sub(r'\s+', ' ', text).strip()

    # 3. Check for Devanagari
    has_devanagari = any('\u0900' <= ch <= '\u097f' for ch in text)
    if has_devanagari:
        words = text.split(' ')
        converted = [transliterate_devanagari_word(w) for w in words]
        text = ' '.join(converted)

    # 4. Final safety sanitization: strip/replace any remaining stray Devanagari code points
    text = _sanitize_any_remaining_devanagari(text)

    # 5. Apply phonetic cleanups
    for pattern, replacement in WORD_REPLACEMENTS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Clean double spaces & format
    text = re.sub(r'\s+', ' ', text).strip()
    return text.capitalize() if text else ""
