"""Tests for lyrics fetching, cleaning, and LRC parsing."""

from unittest.mock import MagicMock, patch

from lyricvibe.lyrics.fetcher import (
    _LYRICS_CACHE,
    LyricLine,
    _parse_plain_lyrics,
    clean_lyric_line,
    clean_track_title,
    fetch_lyrics_smart,
    get_primary_artist,
    parse_lrc,
)


def test_clean_track_title_removes_noise():
    cases = [
        ("Tere Vaaste (From \"Zara Hatke Zara Bachke\")", "Tere Vaaste"),
        ("Blinding Lights [Official Music Video]", "Blinding Lights"),
        ("Starboy (feat. Daft Punk)", "Starboy"),
        ("Stay (with Justin Bieber)", "Stay"),
        ("Bad Habits (Remix)", "Bad Habits"),
        ("Shape of You (Radio Edit)", "Shape of You"),
        ("Levitating (feat. DaBaby) [Visualizer]", "Levitating"),
        ("Midnight City - Original Soundtrack", "Midnight City"),
        ("Hotel California - 2013 Remaster", "Hotel California"),
        ("Something Just Like This [Lyric Video]", "Something Just Like This"),
    ]
    for raw, expected in cases:
        cleaned = clean_track_title(raw)
        assert cleaned == expected, f"Expected '{expected}', got '{cleaned}' for input '{raw}'"


def test_clean_track_title_edge_cases():
    assert clean_track_title("") == ""
    assert clean_track_title("   ") == ""
    # Should not destroy pure titles without tags
    assert clean_track_title("Bohemian Rhapsody") == "Bohemian Rhapsody"
    assert clean_track_title("Just The Way You Are") == "Just The Way You Are"


def test_get_primary_artist():
    assert get_primary_artist("Arijit Singh, Sachin-Jigar") == "Arijit Singh"
    assert get_primary_artist("The Weeknd & Daft Punk") == "The Weeknd"
    assert get_primary_artist("Drake feat. Rihanna") == "Drake"
    assert get_primary_artist("Marshmello x Khalid") == "Marshmello"
    assert get_primary_artist("Taylor Swift") == "Taylor Swift"
    assert get_primary_artist("") == ""


def test_parse_lrc_standard():
    lrc = """
    [ti:Test Track]
    [ar:Test Artist]
    [00:04.50]Line one starts here
    [00:12.30]Line two follows next
    [01:05.123]Line three with three digit millis
    [02:10:45]Line four with colon separator
    """
    lines = parse_lrc(lrc)
    assert len(lines) == 4
    assert lines[0].time_sec == 4.5
    assert lines[0].text == "Line one starts here"
    assert lines[1].time_sec == 12.3
    assert lines[2].time_sec == 65.123
    assert abs(lines[3].time_sec - 130.45) < 0.01


def test_parse_lrc_multi_tag_and_sorting():
    # Multi-tag line where the same lyrics appear at multiple timestamps
    lrc = """
    [00:30.00]Second verse
    [00:10.00][00:50.00]Repeated chorus
    [00:01.00]Intro line
    """
    lines = parse_lrc(lrc)
    assert len(lines) == 4
    # Ensure lines are strictly sorted chronologically by time_sec
    timestamps = [line.time_sec for line in lines]
    assert timestamps == sorted(timestamps)
    assert lines[0].time_sec == 1.0
    assert lines[1].time_sec == 10.0
    assert lines[1].text == "Repeated chorus"
    assert lines[2].time_sec == 30.0
    assert lines[3].time_sec == 50.0
    assert lines[3].text == "Repeated chorus"


def test_parse_lrc_transliterates_devanagari():
    lrc = """
    [00:05.00]क़रीब आओ ना
    [00:10.00]ज़रा सुनो तो
    """
    lines = parse_lrc(lrc)
    assert len(lines) == 2
    # Ensure transliteration to Hinglish was applied
    assert "qareeb" in lines[0].text.lower()
    assert "zara" in lines[1].text.lower()
    assert all(ord(c) < 128 for c in lines[0].text)


def test_lyrics_caching():
    _LYRICS_CACHE.clear()

    # Pre-populate cache (key is {track_name}||{artist_name})
    fake_lines = [LyricLine(1.0, "Cached lyric line")]
    _LYRICS_CACHE["song||artist"] = fake_lines

    # Should immediately return cached result without hitting network
    res = fetch_lyrics_smart("Song", "Artist", duration_sec=180)
    assert res == fake_lines


@patch("lyricvibe.lyrics.fetcher._HTTP_SESSION.get")
def test_fetch_lyrics_network_fallback(mock_get):
    _LYRICS_CACHE.clear()

    # Mock LRCLIB returning 200 with synced lyrics
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "syncedLyrics": "[00:05.00]Mocked online lyric line",
        "plainLyrics": "",
    }
    mock_get.return_value = mock_resp

    lines = fetch_lyrics_smart("Online Song", "Online Artist", duration_sec=200)
    assert lines is not None
    assert len(lines) == 1
    assert lines[0].text == "Mocked online lyric line"
    assert lines[0].time_sec == 5.0


def test_clean_lyric_line_structural_headers():
    assert clean_lyric_line("[Chorus]") == ""
    assert clean_lyric_line("(Verse 1)") == ""
    assert clean_lyric_line("[Intro]") == ""
    assert clean_lyric_line("[Outro]") == ""
    assert clean_lyric_line("[Bridge]") == ""
    assert clean_lyric_line("[Guitar Solo]") == ""
    assert clean_lyric_line("(Instrumental)") == ""


def test_clean_lyric_line_chords_and_symbols():
    assert clean_lyric_line("♪ I see trees of green ♪") == "I see trees of green"
    assert clean_lyric_line("Hello [C] world [G#m7] from here") == "Hello world from here"
    assert clean_lyric_line("♫ Lalala ~ ♫") == "Lalala"


def test_parse_lrc_filters_structural_headers():
    lrc = """
    [00:05.00][Intro]
    [00:10.00]Here comes the real vocal
    [00:25.00][Chorus]
    [00:30.00]♪ Singing the chorus line ♪
    """
    lines = parse_lrc(lrc)
    assert len(lines) == 2
    assert lines[0].text == "Here comes the real vocal"
    assert lines[1].text == "Singing the chorus line"


def test_parse_plain_lyrics_duration_pacing():
    plain = """
    [Intro]
    First verse line
    Second verse line
    [Chorus]
    Third verse line
    """
    # 3 valid vocal lines over 120-second duration
    lines = _parse_plain_lyrics(plain, duration_sec=120.0)
    assert len(lines) == 3
    assert lines[0].text == "First verse line"
    assert lines[1].text == "Second verse line"
    assert lines[2].text == "Third verse line"
    # Check that pacing scaled to duration: step = 120 * 0.9 / 3 = 36.0s
    assert lines[0].time_sec == 0.0
    assert lines[1].time_sec == 36.0
    assert lines[2].time_sec == 72.0


def test_parse_plain_lyrics_empty():
    assert _parse_plain_lyrics("") == []
    assert _parse_plain_lyrics("   ") == []
    assert _parse_plain_lyrics("[Chorus]\n[Intro]\n") == []
