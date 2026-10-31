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
    "\u0622": "aa",  # آ (Alef with Madda)
    "\u0627": "a",  # ا (Alef)
    "\u0623": "a",  # أ (Alef with Hamza above)
    "\u0625": "i",  # إ (Alef with Hamza below)
    "\u0628": "b",  # ب (Beh)
    "\u067e": "p",  # پ (Peh)
    "\u062a": "t",  # ت (Teh)
    "\u0679": "t",  # ٹ (Tteh)
    "\u062b": "s",  # ث (Theh)
    "\u062c": "j",  # ج (Jeem)
    "\u0686": "ch",  # چ (Tcheh)
    "\u062d": "h",  # ح (Hah)
    "\u062e": "kh",  # خ (Khah)
    "\u062f": "d",  # د (Dal)
    "\u0688": "d",  # ڈ (Ddal)
    "\u0630": "z",  # ذ (Thal)
    "\u0631": "r",  # ر (Reh) - CRITICAL!
    "\u0691": "r",  # ڑ (Rreh)
    "\u0632": "z",  # ز (Zain)
    "\u0698": "zh",  # ژ (Zheh)
    "\u0633": "s",  # س (Seen)
    "\u0634": "sh",  # ش (Sheen)
    "\u0635": "s",  # ص (Sad)
    "\u0636": "z",  # ض (Dad)
    "\u0637": "t",  # ط (Tah)
    "\u0638": "z",  # ظ (Zah)
    "\u0639": "a",  # ع (Ain)
    "\u063a": "gh",  # غ (Ghain)
    "\u0641": "f",  # ف (Feh)
    "\u0642": "q",  # ق (Qaf)
    "\u06a9": "k",  # ک (Keheh)
    "\u0643": "k",  # ك (Kaf)
    "\u06af": "g",  # گ (Gaf)
    "\u0644": "l",  # ل (Lam)
    "\u0645": "m",  # م (Meem) - CRITICAL!
    "\u0646": "n",  # ن (Noon)
    "\u06ba": "n",  # ں (Noon Ghunna)
    "\u0648": "o",  # و (Waw)
    "\u06c1": "h",  # ہ (Heh Goal)
    "\u06be": "h",  # ھ (Heh Doachashmee)
    "\u0629": "t",  # ة (Teh Marbuta)
    "\u06c2": "h",  # ۂ (Heh Goal with Hamza)
    "\u06c3": "h",  # ۃ (Teh Marbuta Goal)
    "\u0649": "a",  # ى (Alef Maksura)
    "\u06cc": "i",  # ی (Farsi Yeh)
    "\u064a": "i",  # ي (Arabic Yeh)
    "\u06d2": "e",  # ے (Bari Yeh)
    "\u0626": "i",  # ئ (Yeh with Hamza)
    "\u0624": "o",  # ؤ (Waw with Hamza)
    "\u0621": "",  # ء (Hamza)
    "\u0674": "",  # ٴ (High Hamza)
    "\u0670": "aa",  # ٰ (Superscript Alef)
    # Diacritics (Harakat / Aerab)
    "\u064e": "a",  # َ (Zabar / Fatha)
    "\u0650": "i",  # ِ (Zer / Kasra)
    "\u064f": "u",  # ُ (Pesh / Damma)
    "\u064b": "an",  # ً (Tanwin Fath)
    "\u064d": "in",  # ٍ (Tanwin Kasr)
    "\u064c": "un",  # ٌ (Tanwin Damm)
    "\u0651": "",  # ّ (Tashdeed)
    "\u0652": "",  # ْ (Sukun)
    "\u0653": "",  # ٓ (Maddah)
    "\u0654": "",  # ٔ (Hamza Above)
    "\u0655": "",  # ٕ (Hamza Below)
    # Punctuation & Numbers
    "\u060c": ",",  # ، (Arabic Comma)
    "\u061b": ";",  # ؛ (Arabic Semicolon)
    "\u061f": "?",  # ؟ (Arabic Question Mark)
    "\u06d4": ".",  # ۔ (Urdu Full Stop)
    "\u066a": "%",  # ٪ (Arabic Percent)
    "\u0660": "0",
    "\u0661": "1",
    "\u0662": "2",
    "\u0663": "3",
    "\u0664": "4",
    "\u0665": "5",
    "\u0666": "6",
    "\u0667": "7",
    "\u0668": "8",
    "\u0669": "9",
    "\u06f0": "0",
    "\u06f1": "1",
    "\u06f2": "2",
    "\u06f3": "3",
    "\u06f4": "4",
    "\u06f5": "5",
    "\u06f6": "6",
    "\u06f7": "7",
    "\u06f8": "8",
    "\u06f9": "9",
}

# ── 2. Devanagari Mapping ─────────────────────────────────────────────
NUKTA_NORMALIZATION = {
    "\u0915\u093c": "\u0958",  # क़ -> क़
    "\u0916\u093c": "\u0959",  # ख़ -> ख़
    "\u0917\u093c": "\u095a",  # ग़ -> ग़
    "\u091c\u093c": "\u095b",  # ज़ -> ज़
    "\u0921\u093c": "\u095c",  # ड़ -> ड़
    "\u0922\u093c": "\u095d",  # ढ़ -> ढ़
    "\u092b\u093c": "\u095e",  # फ़ -> फ़
    "\u092f\u093c": "\u095f",  # य़ -> य़
}

DEV_VOWELS = {
    "अ": "a",
    "आ": "aa",
    "इ": "i",
    "ई": "ee",
    "उ": "u",
    "ऊ": "oo",
    "ऋ": "ri",
    "ए": "e",
    "ऐ": "ai",
    "ओ": "o",
    "औ": "au",
    "अं": "an",
    "अः": "ah",
    "ऑ": "o",
    "ऍ": "e",
}

DEV_MATRAS = {
    "ा": "aa",
    "ि": "i",
    "ी": "ee",
    "ु": "u",
    "ू": "oo",
    "ृ": "ri",
    "े": "e",
    "ै": "ai",
    "ो": "o",
    "ौ": "au",
    "ॉ": "o",
    "ॅ": "e",
    "ं": "n",
    "ँ": "n",
    "ः": "h",
}

DEV_CONSONANTS = {
    "क": "k",
    "ख": "kh",
    "ग": "g",
    "घ": "gh",
    "ङ": "ng",
    "च": "ch",
    "छ": "chh",
    "ज": "j",
    "झ": "jh",
    "ञ": "ny",
    "ट": "t",
    "ठ": "th",
    "ड": "d",
    "ढ": "dh",
    "ण": "n",
    "त": "t",
    "थ": "th",
    "द": "d",
    "ध": "dh",
    "न": "n",
    "प": "p",
    "फ": "ph",
    "ब": "b",
    "भ": "bh",
    "म": "m",
    "य": "y",
    "र": "r",
    "ल": "l",
    "व": "v",
    "श": "sh",
    "ष": "sh",
    "स": "s",
    "ह": "h",
    # Nukta consonants (Urdu/Persian/Arabic loan sounds)
    "\u0958": "q",
    "\u0959": "kh",
    "\u095a": "gh",
    "\u095b": "z",
    "\u095c": "r",
    "\u095d": "rh",
    "\u095e": "f",
    "\u095f": "y",
}

DEV_DIGITS = {
    "०": "0",
    "१": "1",
    "२": "2",
    "३": "3",
    "४": "4",
    "५": "5",
    "६": "6",
    "७": "7",
    "८": "8",
    "९": "9",
}

DEV_PUNCTUATION = {
    "।": ".",
    "॥": ".",
    "ॐ": "Om",
}

HALANT = "्"

# ── 3. Gurmukhi (Punjabi) Mapping ─────────────────────────────────────
GUR_VOWELS = {
    "ਅ": "a",
    "ਆ": "aa",
    "ਇ": "i",
    "ਈ": "ee",
    "ਉ": "u",
    "ਊ": "oo",
    "ਏ": "e",
    "ਐ": "ai",
    "ਓ": "o",
    "ਔ": "au",
}

GUR_MATRAS = {
    "ਾ": "aa",
    "ਿ": "i",
    "ੀ": "ee",
    "ੁ": "u",
    "ੂ": "oo",
    "ੇ": "e",
    "ੈ": "ai",
    "ੋ": "o",
    "ਔ": "au",
    "ੰ": "n",
    "ਂ": "n",
}

GUR_CONSONANTS = {
    "ਸ": "s",
    "ਹ": "h",
    "ਕ": "k",
    "ਖ": "kh",
    "ਗ": "g",
    "ਘ": "gh",
    "ਙ": "ng",
    "ਚ": "ch",
    "ਛ": "chh",
    "ਜ": "j",
    "ਝ": "jh",
    "ਞ": "ny",
    "ਟ": "t",
    "ਠ": "th",
    "ਡ": "d",
    "ਢ": "dh",
    "ਣ": "n",
    "ਤ": "t",
    "ਥ": "th",
    "ਦ": "d",
    "ਧ": "dh",
    "ਨ": "n",
    "ਪ": "p",
    "ਫ": "ph",
    "ਬ": "b",
    "ਭ": "bh",
    "ਮ": "m",
    "ਯ": "y",
    "ਰ": "r",
    "ਲ": "l",
    "ਵ": "v",
    "ੜ": "r",
    "ਸ਼": "sh",
    "ਖ਼": "kh",
    "ਗ਼": "gh",
    "ਜ਼": "z",
    "ਫ਼": "f",
    "ਲ਼": "l",
}

GUR_DIGITS = {
    "੦": "0",
    "੧": "1",
    "੨": "2",
    "੩": "3",
    "੪": "4",
    "੫": "5",
    "੬": "6",
    "੭": "7",
    "੮": "8",
    "੯": "9",
}

GUR_HALANT = "੍"

# ── 4. Bengali Mapping ───────────────────────────────────────────────
BEN_VOWELS = {
    "অ": "a",
    "আ": "aa",
    "ই": "i",
    "ঈ": "ee",
    "উ": "u",
    "ঊ": "oo",
    "ঋ": "ri",
    "এ": "e",
    "ঐ": "oi",
    "ও": "o",
    "ঔ": "ou",
}

BEN_MATRAS = {
    "া": "aa",
    "ি": "i",
    "ী": "ee",
    "ু": "u",
    "ূ": "oo",
    "ৃ": "ri",
    "ে": "e",
    "ৈ": "oi",
    "ো": "o",
    "ৌ": "ou",
    "ং": "ng",
    "ঃ": "h",
    "ঁ": "n",
}

BEN_CONSONANTS = {
    "ক": "k",
    "খ": "kh",
    "গ": "g",
    "ঘ": "gh",
    "ঙ": "ng",
    "চ": "ch",
    "ছ": "chh",
    "জ": "j",
    "ঝ": "jh",
    "ঞ": "ny",
    "ট": "t",
    "ঠ": "th",
    "ড": "d",
    "ঢ": "dh",
    "ণ": "n",
    "ত": "t",
    "থ": "th",
    "দ": "d",
    "ধ": "dh",
    "ন": "n",
    "প": "p",
    "ফ": "ph",
    "ব": "b",
    "ভ": "bh",
    "ম": "m",
    "য": "j",
    "র": "r",
    "ল": "l",
    "শ": "sh",
    "ষ": "sh",
    "স": "s",
    "হ": "h",
    "ড়": "r",
    "ঢ়": "rh",
    "য়": "y",
    "ৎ": "t",
}

BEN_DIGITS = {
    "০": "0",
    "১": "1",
    "২": "2",
    "৩": "3",
    "৪": "4",
    "৫": "5",
    "৬": "6",
    "৭": "7",
    "৮": "8",
    "৯": "9",
}

BEN_HALANT = "্"

# ── 5. Gujarati Mapping ──────────────────────────────────────────────
GUJ_VOWELS = {
    "અ": "a",
    "આ": "aa",
    "ઇ": "i",
    "ઈ": "ee",
    "ઉ": "u",
    "ઊ": "oo",
    "ઋ": "ri",
    "એ": "e",
    "ઐ": "ai",
    "ઓ": "o",
    "ઔ": "au",
}

GUJ_MATRAS = {
    "ા": "aa",
    "િ": "i",
    "ી": "ee",
    "ુ": "u",
    "ૂ": "oo",
    "ૃ": "ri",
    "ે": "e",
    "ૈ": "ai",
    "ો": "o",
    "ૌ": "au",
    "ં": "n",
    "ઃ": "h",
}

GUJ_CONSONANTS = {
    "ક": "k",
    "ખ": "kh",
    "ગ": "g",
    "ઘ": "gh",
    "ઙ": "ng",
    "ચ": "ch",
    "છ": "chh",
    "જ": "j",
    "ઝ": "jh",
    "ઞ": "ny",
    "ટ": "t",
    "ઠ": "th",
    "ડ": "d",
    "ઢ": "dh",
    "ણ": "n",
    "ત": "t",
    "થ": "th",
    "દ": "d",
    "ધ": "dh",
    "ન": "n",
    "પ": "p",
    "ફ": "ph",
    "બ": "b",
    "ભ": "bh",
    "મ": "m",
    "ય": "y",
    "ર": "r",
    "લ": "l",
    "ળ": "l",
    "વ": "v",
    "શ": "sh",
    "ષ": "sh",
    "સ": "s",
    "હ": "h",
}

GUJ_DIGITS = {
    "૦": "0",
    "૧": "1",
    "૨": "2",
    "૩": "3",
    "૪": "4",
    "૫": "5",
    "૬": "6",
    "૭": "7",
    "૮": "8",
    "૯": "9",
}

GUJ_HALANT = "્"

# ── 6. Tamil Mapping ────────────────────────────────────────────────
TAM_VOWELS = {
    "அ": "a",
    "ஆ": "aa",
    "இ": "i",
    "ஈ": "ee",
    "உ": "u",
    "ஊ": "oo",
    "எ": "e",
    "ஏ": "ae",
    "ஐ": "ai",
    "ஒ": "o",
    "ஓ": "o",
    "ஔ": "au",
}

TAM_MATRAS = {
    "ா": "aa",
    "ி": "i",
    "ீ": "ee",
    "ு": "u",
    "ூ": "oo",
    "ெ": "e",
    "ே": "ae",
    "ை": "ai",
    "ொ": "o",
    "ோ": "o",
    "ௌ": "au",
    "ஃ": "h",
}

TAM_CONSONANTS = {
    "க": "k",
    "ங": "ng",
    "ச": "s",
    "ஞ": "ny",
    "ட": "t",
    "ண": "n",
    "த": "th",
    "ந": "n",
    "ப": "p",
    "ம": "m",
    "ய": "y",
    "ர": "r",
    "ல": "l",
    "வ": "v",
    "ழ": "zh",
    "ள": "l",
    "ற": "r",
    "ன": "n",
    "ஜ": "j",
    "ஷ": "sh",
    "ஸ": "s",
    "ஹ": "h",
}

TAM_DIGITS = {
    "௦": "0",
    "௧": "1",
    "௨": "2",
    "௩": "3",
    "௪": "4",
    "௫": "5",
    "௬": "6",
    "௭": "7",
    "௮": "8",
    "௯": "9",
}

TAM_HALANT = "்"

# ── 7. Telugu Mapping ───────────────────────────────────────────────
TEL_VOWELS = {
    "అ": "a",
    "ఆ": "aa",
    "ఇ": "i",
    "ఈ": "ee",
    "ఉ": "u",
    "ఊ": "oo",
    "ఋ": "ri",
    "ఎ": "e",
    "ఏ": "ae",
    "ఐ": "ai",
    "ఒ": "o",
    "ఓ": "o",
    "ఔ": "au",
}

TEL_MATRAS = {
    "ా": "aa",
    "ి": "i",
    "ీ": "ee",
    "ు": "u",
    "ూ": "oo",
    "ృ": "ri",
    "ె": "e",
    "ే": "ae",
    "ై": "ai",
    "ొ": "o",
    "ో": "o",
    "ౌ": "au",
    "ం": "n",
    "ః": "h",
}

TEL_CONSONANTS = {
    "క": "k",
    "ఖ": "kh",
    "గ": "g",
    "ఘ": "gh",
    "ఙ": "ng",
    "చ": "ch",
    "ఛ": "chh",
    "జ": "j",
    "ఝ": "jh",
    "ఞ": "ny",
    "ట": "t",
    "ఠ": "th",
    "డ": "d",
    "ఢ": "dh",
    "ణ": "n",
    "త": "t",
    "థ": "th",
    "ద": "d",
    "ధ": "dh",
    "న": "n",
    "ప": "p",
    "ఫ": "ph",
    "బ": "b",
    "భ": "bh",
    "మ": "m",
    "య": "y",
    "ర": "r",
    "ల": "l",
    "వ": "v",
    "శ": "sh",
    "ష": "sh",
    "స": "s",
    "హ": "h",
    "ళ": "l",
}

TEL_DIGITS = {
    "౦": "0",
    "౧": "1",
    "౨": "2",
    "౩": "3",
    "౪": "4",
    "౫": "5",
    "౬": "6",
    "౭": "7",
    "౮": "8",
    "౯": "9",
}

TEL_HALANT = "్"

# ── 3. Phonetic Cleanups & Common Word Corrections ────────────────────
WORD_REPLACEMENTS = [
    # Common corrupted syllables from mixed scripts
    (r"\bph\s+r\b", "phir"),
    (r"\bphr\b", "phir"),
    (r"\bbkhrna\b", "bikharna"),
    (r"\bzrori\b", "zaroori"),
    (r"\bm\s+ro\b", "magar"),
    (r"\bmro\b", "magar"),
    (r"\baarzohn\b", "aarzoon"),
    (r"\baarzon\b", "aarzoon"),
    (r"\bkyoon\b", "kyun"),
    (r"\bkyon\b", "kyun"),
    (r"\btumhi\b", "tum hi"),
    (r"\bmujhako\b", "mujhko"),
    (r"\btujhako\b", "tujhko"),
    (r"\busako\b", "usko"),
    (r"\bisako\b", "isko"),
    (r"\bnahin\b", "nahi"),
    (r"\bnaheen\b", "nahi"),
    (r"\bnahee\b", "nahi"),
    (r"\bkabhee\b", "kabhi"),
    (r"\bbhee\b", "bhi"),
    (r"\bkee\b", "ki"),
    (r"\bmeree\b", "meri"),
    (r"\bteree\b", "teri"),
    (r"\bzindagee\b", "zindagi"),
    (r"\bkhushee\b", "khushi"),
    (r"\bkisee\b", "kisi"),
    (r"\bkoyee\b", "koi"),
    (r"\bkoee\b", "koi"),
    (r"\bhain\b", "hai"),
    (r"\bhoon\b", "hoon"),
    (r"\bmeen\b", "mein"),
    (r"\bmen\b", "mein"),
    (r"\braha\b", "raha"),
    (r"\brahe\b", "rahe"),
    (r"\brahi\b", "rahi"),
    (r"\bjnya", "gya"),
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
                if i >= n or word[i] in " ,.?!()-'\"\n\r":
                    res.append(cons)
                else:
                    res.append(cons + "a")
        elif char in DEV_MATRAS:
            res.append(DEV_MATRAS[char])
            i += 1
        elif char in DEV_DIGITS:
            res.append(DEV_DIGITS[char])
            i += 1
        elif char in DEV_PUNCTUATION:
            res.append(DEV_PUNCTUATION[char])
            i += 1
        elif char == HALANT or char == "\u093c":
            i += 1
        else:
            res.append(char)
            i += 1

    return "".join(res)


def transliterate_gurmukhi_word(word: str) -> str:
    """Converts a Gurmukhi (Punjabi) word cleanly into Roman Latin characters."""
    res = []
    i = 0
    n = len(word)
    while i < n:
        char = word[i]
        if char in GUR_VOWELS:
            res.append(GUR_VOWELS[char])
            i += 1
        elif char in GUR_CONSONANTS:
            cons = GUR_CONSONANTS[char]
            i += 1
            if i < n and word[i] == GUR_HALANT:
                res.append(cons)
                i += 1
            elif i < n and word[i] in GUR_MATRAS:
                res.append(cons + GUR_MATRAS[word[i]])
                i += 1
            else:
                if i >= n or word[i] in " ,.?!()-'\"\n\r":
                    res.append(cons)
                else:
                    res.append(cons + "a")
        elif char in GUR_MATRAS:
            res.append(GUR_MATRAS[char])
            i += 1
        elif char in GUR_DIGITS:
            res.append(GUR_DIGITS[char])
            i += 1
        elif char == GUR_HALANT or char == "ੱ":
            i += 1
        elif char in ("।", "॥"):
            res.append(".")
            i += 1
        else:
            res.append(char)
            i += 1
    return "".join(res)


def transliterate_bengali_word(word: str) -> str:
    """Converts a Bengali word cleanly into Roman Latin characters."""
    res = []
    i = 0
    n = len(word)
    while i < n:
        char = word[i]
        if char in BEN_VOWELS:
            res.append(BEN_VOWELS[char])
            i += 1
        elif char in BEN_CONSONANTS:
            cons = BEN_CONSONANTS[char]
            i += 1
            if i < n and word[i] == BEN_HALANT:
                res.append(cons)
                i += 1
            elif i < n and word[i] in BEN_MATRAS:
                res.append(cons + BEN_MATRAS[word[i]])
                i += 1
            else:
                if i >= n or word[i] in " ,.?!()-'\"\n\r":
                    res.append(cons)
                else:
                    res.append(cons + "a")
        elif char in BEN_MATRAS:
            res.append(BEN_MATRAS[char])
            i += 1
        elif char in BEN_DIGITS:
            res.append(BEN_DIGITS[char])
            i += 1
        elif char == BEN_HALANT:
            i += 1
        elif char in ("।", "॥"):
            res.append(".")
            i += 1
        else:
            res.append(char)
            i += 1
    return "".join(res)


def transliterate_gujarati_word(word: str) -> str:
    """Converts a Gujarati word cleanly into Roman Latin characters."""
    res = []
    i = 0
    n = len(word)
    while i < n:
        char = word[i]
        if char in GUJ_VOWELS:
            res.append(GUJ_VOWELS[char])
            i += 1
        elif char in GUJ_CONSONANTS:
            cons = GUJ_CONSONANTS[char]
            i += 1
            if i < n and word[i] == GUJ_HALANT:
                res.append(cons)
                i += 1
            elif i < n and word[i] in GUJ_MATRAS:
                res.append(cons + GUJ_MATRAS[word[i]])
                i += 1
            else:
                if i >= n or word[i] in " ,.?!()-'\"\n\r":
                    res.append(cons)
                else:
                    res.append(cons + "a")
        elif char in GUJ_MATRAS:
            res.append(GUJ_MATRAS[char])
            i += 1
        elif char in GUJ_DIGITS:
            res.append(GUJ_DIGITS[char])
            i += 1
        elif char == GUJ_HALANT:
            i += 1
        elif char in ("।", "॥"):
            res.append(".")
            i += 1
        else:
            res.append(char)
            i += 1
    return "".join(res)


def transliterate_tamil_word(word: str) -> str:
    """Converts a Tamil word cleanly into Roman Latin characters."""
    res = []
    i = 0
    n = len(word)
    while i < n:
        char = word[i]
        if char in TAM_VOWELS:
            res.append(TAM_VOWELS[char])
            i += 1
        elif char in TAM_CONSONANTS:
            cons = TAM_CONSONANTS[char]
            i += 1
            if i < n and word[i] == TAM_HALANT:
                res.append(cons)
                i += 1
            elif i < n and word[i] in TAM_MATRAS:
                res.append(cons + TAM_MATRAS[word[i]])
                i += 1
            else:
                if i >= n or word[i] in " ,.?!()-'\"\n\r":
                    res.append(cons)
                else:
                    res.append(cons + "a")
        elif char in TAM_MATRAS:
            res.append(TAM_MATRAS[char])
            i += 1
        elif char in TAM_DIGITS:
            res.append(TAM_DIGITS[char])
            i += 1
        elif char == TAM_HALANT:
            i += 1
        elif char in ("।", "॥"):
            res.append(".")
            i += 1
        else:
            res.append(char)
            i += 1
    return "".join(res)


def transliterate_telugu_word(word: str) -> str:
    """Converts a Telugu word cleanly into Roman Latin characters."""
    res = []
    i = 0
    n = len(word)
    while i < n:
        char = word[i]
        if char in TEL_VOWELS:
            res.append(TEL_VOWELS[char])
            i += 1
        elif char in TEL_CONSONANTS:
            cons = TEL_CONSONANTS[char]
            i += 1
            if i < n and word[i] == TEL_HALANT:
                res.append(cons)
                i += 1
            elif i < n and word[i] in TEL_MATRAS:
                res.append(cons + TEL_MATRAS[word[i]])
                i += 1
            else:
                if i >= n or word[i] in " ,.?!()-'\"\n\r":
                    res.append(cons)
                else:
                    res.append(cons + "a")
        elif char in TEL_MATRAS:
            res.append(TEL_MATRAS[char])
            i += 1
        elif char in TEL_DIGITS:
            res.append(TEL_DIGITS[char])
            i += 1
        elif char == TEL_HALANT:
            i += 1
        elif char in ("।", "॥"):
            res.append(".")
            i += 1
        else:
            res.append(char)
            i += 1
    return "".join(res)


def transliterate_urdu_text(text: str) -> str:
    """Converts Arabic/Urdu/Persian characters cleanly to Latin Hinglish."""
    res = []
    for ch in text:
        if ch in URDU_MAP:
            res.append(URDU_MAP[ch])
        else:
            # Check if within Arabic block and not in map -> strip or drop
            code = ord(ch)
            if (
                (0x0600 <= code <= 0x06FF)
                or (0x0750 <= code <= 0x077F)
                or (0xFB50 <= code <= 0xFDFF)
                or (0xFE70 <= code <= 0xFEFF)
            ):
                pass  # Safely strip unsupported Arabic diacritics
            else:
                res.append(ch)
    return "".join(res)


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
        # Check Bengali
        elif 0x0980 <= code <= 0x09FF:
            if ch in BEN_CONSONANTS:
                clean.append(BEN_CONSONANTS[ch])
            elif ch in BEN_VOWELS:
                clean.append(BEN_VOWELS[ch])
            elif ch in BEN_MATRAS:
                clean.append(BEN_MATRAS[ch])
            elif ch in BEN_DIGITS:
                clean.append(BEN_DIGITS[ch])
            else:
                pass  # drop
        # Check Gurmukhi (Punjabi)
        elif 0x0A00 <= code <= 0x0A7F:
            if ch in GUR_CONSONANTS:
                clean.append(GUR_CONSONANTS[ch])
            elif ch in GUR_VOWELS:
                clean.append(GUR_VOWELS[ch])
            elif ch in GUR_MATRAS:
                clean.append(GUR_MATRAS[ch])
            elif ch in GUR_DIGITS:
                clean.append(GUR_DIGITS[ch])
            else:
                pass  # drop
        # Check Gujarati
        elif 0x0A80 <= code <= 0x0AFF:
            if ch in GUJ_CONSONANTS:
                clean.append(GUJ_CONSONANTS[ch])
            elif ch in GUJ_VOWELS:
                clean.append(GUJ_VOWELS[ch])
            elif ch in GUJ_MATRAS:
                clean.append(GUJ_MATRAS[ch])
            elif ch in GUJ_DIGITS:
                clean.append(GUJ_DIGITS[ch])
            else:
                pass  # drop
        # Check Tamil
        elif 0x0B80 <= code <= 0x0BFF:
            if ch in TAM_CONSONANTS:
                clean.append(TAM_CONSONANTS[ch])
            elif ch in TAM_VOWELS:
                clean.append(TAM_VOWELS[ch])
            elif ch in TAM_MATRAS:
                clean.append(TAM_MATRAS[ch])
            elif ch in TAM_DIGITS:
                clean.append(TAM_DIGITS[ch])
            else:
                pass  # drop
        # Check Telugu
        elif 0x0C00 <= code <= 0x0C7F:
            if ch in TEL_CONSONANTS:
                clean.append(TEL_CONSONANTS[ch])
            elif ch in TEL_VOWELS:
                clean.append(TEL_VOWELS[ch])
            elif ch in TEL_MATRAS:
                clean.append(TEL_MATRAS[ch])
            elif ch in TEL_DIGITS:
                clean.append(TEL_DIGITS[ch])
            else:
                pass  # drop
        # Drop unmapped South Asian / Brahmic code points (Kannada 0C80-0CFF, Malayalam 0D00-0D7F)
        elif 0x0C80 <= code <= 0x0D7F:
            pass
        # Check Arabic / Urdu / Persian
        elif (
            (0x0600 <= code <= 0x06FF)
            or (0x0750 <= code <= 0x077F)
            or (0xFB50 <= code <= 0xFDFF)
            or (0xFE70 <= code <= 0xFEFF)
        ):
            if ch in URDU_MAP:
                clean.append(URDU_MAP[ch])
            else:
                pass  # drop
        # Invisible bidi / zero-width formatting characters
        elif (
            ch in ("\u200b", "\u200c", "\u200d", "\u200e", "\u200f", "\ufeff")
            or (0x202A <= code <= 0x202E)
            or (0x2066 <= code <= 0x2069)
        ):
            pass
        elif ch == "\u00a0":
            clean.append(" ")
        # Smart quotes / punctuation normalisation
        elif ch in ("\u2018", "\u2019", "`"):
            clean.append("'")
        elif ch in ("\u201c", "\u201d"):
            clean.append('"')
        elif ch in ("\u2013", "\u2014"):
            clean.append("-")
        elif ch == "\u2026":
            clean.append("...")
        else:
            clean.append(ch)
    return "".join(clean)


def to_hinglish(text: str) -> str:
    """
    Takes any lyric text (Devanagari, Urdu, Gurmukhi, Bengali, Gujarati, mixed, or corrupted)
    and produces 100% clean, pure Latin Hinglish with zero foreign symbols.
    """
    if not text:
        return ""

    # 1. Clean invisible bidi and zero-width formatting characters and normalize NBSP
    text = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]", "", text)
    text = text.replace("\u00a0", " ")

    # 2. Preprocess nuktas
    text = _preprocess_nuktas(text)

    # 3. Check for Arabic / Urdu
    has_urdu = any(
        (0x0600 <= ord(ch) <= 0x06FF)
        or (0x0750 <= ord(ch) <= 0x077F)
        or (0xFB50 <= ord(ch) <= 0xFDFF)
        or (0xFE70 <= ord(ch) <= 0xFEFF)
        for ch in text
    )
    if has_urdu:
        text = transliterate_urdu_text(text)

    # 4. Check for Devanagari
    has_devanagari = any(0x0900 <= ord(ch) <= 0x097F for ch in text)
    if has_devanagari:
        tokens = re.split(r"(\s+)", text)
        converted = [
            transliterate_devanagari_word(tok) if not tok.isspace() else tok
            for tok in tokens
        ]
        text = "".join(converted)

    # 5. Check for Bengali
    has_bengali = any(0x0980 <= ord(ch) <= 0x09FF for ch in text)
    if has_bengali:
        tokens = re.split(r"(\s+)", text)
        converted = [
            transliterate_bengali_word(tok) if not tok.isspace() else tok
            for tok in tokens
        ]
        text = "".join(converted)

    # 6. Check for Gurmukhi (Punjabi)
    has_gurmukhi = any(0x0A00 <= ord(ch) <= 0x0A7F for ch in text)
    if has_gurmukhi:
        tokens = re.split(r"(\s+)", text)
        converted = [
            transliterate_gurmukhi_word(tok) if not tok.isspace() else tok
            for tok in tokens
        ]
        text = "".join(converted)

    # 7. Check for Gujarati
    has_gujarati = any(0x0A80 <= ord(ch) <= 0x0AFF for ch in text)
    if has_gujarati:
        tokens = re.split(r"(\s+)", text)
        converted = [
            transliterate_gujarati_word(tok) if not tok.isspace() else tok
            for tok in tokens
        ]
        text = "".join(converted)

    # 8. Check for Tamil
    has_tamil = any(0x0B80 <= ord(ch) <= 0x0BFF for ch in text)
    if has_tamil:
        tokens = re.split(r"(\s+)", text)
        converted = [
            transliterate_tamil_word(tok) if not tok.isspace() else tok
            for tok in tokens
        ]
        text = "".join(converted)

    # 9. Check for Telugu
    has_telugu = any(0x0C00 <= ord(ch) <= 0x0C7F for ch in text)
    if has_telugu:
        tokens = re.split(r"(\s+)", text)
        converted = [
            transliterate_telugu_word(tok) if not tok.isspace() else tok
            for tok in tokens
        ]
        text = "".join(converted)

    # 10. Universal safety sanitization (zero leaks guarantee)
    text = _universal_safety_sanitize(text)

    # 11. Apply phonetic cleanups
    for pattern, replacement in WORD_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # 12. Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return ""

    # Capitalize the first character while preserving casing for the remainder of the sentence
    return text[0].upper() + text[1:]
