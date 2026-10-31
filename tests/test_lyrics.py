"""Tests for lyrics fetching, cleaning, and LRC parsing."""

import time
from unittest.mock import MagicMock, patch

from lyricvibe.lyrics.fetcher import (
    _LYRICS_CACHE,
    _NEGATIVE_CACHE_TTL,
    LyricLine,
    _cache_put,
    _parse_plain_lyrics,
    clean_lyric_line,
    clean_track_title,
    fetch_lyrics_smart,
    get_primary_artist,
    is_romanized,
    parse_lrc,
)


def test_clean_track_title_removes_noise():
    cases = [
        ('Tere Vaaste (From "Zara Hatke Zara Bachke")', "Tere Vaaste"),
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
        assert cleaned == expected, (
            f"Expected '{expected}', got '{cleaned}' for input '{raw}'"
        )


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
    assert (
        clean_lyric_line("Hello [C] world [G#m7] from here") == "Hello world from here"
    )
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


def test_clean_track_title_expanded_mix_tags():
    cases = [
        ("Titanium (Club Mix)", "Titanium"),
        ("Yesterday (Mono)", "Yesterday"),
        ("Lose Yourself [Explicit]", "Lose Yourself"),
        ("Levels - Club Mix", "Levels"),
        ("Midnight City - Extended Mix", "Midnight City"),
        ("Smooth - Single Version", "Smooth"),
        ("Thriller - Album Version", "Thriller"),
        ("Love Story (Stereo)", "Love Story"),
    ]
    for raw, expected in cases:
        cleaned = clean_track_title(raw)
        assert cleaned == expected, (
            f"Expected '{expected}', got '{cleaned}' for input '{raw}'"
        )


def test_parse_lrc_fractional_and_hour_timestamps():
    lrc = """
    [00:04.5]One digit millisecond fraction
    [00:10.50]Two digit centisecond fraction
    [00:20.123]Three digit millisecond fraction
    [01:05:30.50]One hour five minutes thirty seconds
    """
    lines = parse_lrc(lrc)
    assert len(lines) == 4
    assert lines[0].time_sec == 4.5
    assert lines[0].text == "One digit millisecond fraction"
    assert lines[1].time_sec == 10.5
    assert lines[1].text == "Two digit centisecond fraction"
    assert lines[2].time_sec == 20.123
    assert lines[2].text == "Three digit millisecond fraction"
    assert abs(lines[3].time_sec - 3930.5) < 0.01
    assert lines[3].text == "One hour five minutes thirty seconds"


def test_parse_lrc_integer_seconds_without_fraction():
    # Integer timestamps without fractions: [mm:ss]
    lrc = """
    [00:15]First integer line
    [01:05]Second integer line at 65 seconds
    """
    lines = parse_lrc(lrc)
    assert len(lines) == 2
    assert lines[0].time_sec == 15.0
    assert lines[0].text == "First integer line"
    assert lines[1].time_sec == 65.0
    assert lines[1].text == "Second integer line at 65 seconds"


def test_clean_lyric_line_section_headers_with_artists():
    assert clean_lyric_line("[Chorus: The Weeknd]") == ""
    assert clean_lyric_line("[Verse 2 - Drake]") == ""
    assert clean_lyric_line("[Pre-Chorus: Taylor Swift]") == ""
    assert clean_lyric_line("(Outro by Post Malone)") == ""
    assert clean_lyric_line("[Guitar Solo]") == ""
    assert clean_lyric_line("[Instrumental]") == ""
    # Should not strip actual lyrics containing words like chorus or verse
    assert (
        clean_lyric_line("Chorus of the angels singing high")
        == "Chorus of the angels singing high"
    )
    assert (
        clean_lyric_line("In every verse you write for me")
        == "In every verse you write for me"
    )


def test_lyrics_cache_thread_safety():
    import threading

    _LYRICS_CACHE.clear()
    errors = []

    def worker(worker_id: int):
        try:
            for i in range(50):
                track = f"Song_{worker_id}_{i}"
                artist = f"Artist_{worker_id}"
                sample_lines = [LyricLine(float(i), f"Line {i}")]
                from lyricvibe.lyrics.fetcher import _cache_put

                _cache_put(f"{track}||{artist}", sample_lines)
                # Read from cache concurrently
                fetch_lyrics_smart(track, artist, duration_sec=180)
        except (KeyError, ValueError, RuntimeError, AttributeError) as e:
            errors.append(e)

    with patch("lyricvibe.lyrics.fetcher._HTTP_SESSION.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    assert len(errors) == 0, f"Thread errors encountered: {errors}"


def test_clean_track_title_square_bracketed_suffix():
    assert (
        clean_track_title("Bohemian Rhapsody [Live at Wembley]") == "Bohemian Rhapsody"
    )
    assert clean_track_title("Hotel California [Acoustic 1994]") == "Hotel California"
    assert clean_track_title("Song Name [Bonus Track]") == "Song Name"


@patch("lyricvibe.lyrics.fetcher._HTTP_SESSION.get")
def test_search_metadata_scoring_prioritizes_authentic_artist(mock_get):
    _LYRICS_CACHE.clear()

    # Exact GET returns 404, search returns both cover and authentic versions
    def mock_side_effect(url, **kwargs):
        resp = MagicMock()
        if "api/get" in url:
            resp.status_code = 404
            resp.json.return_value = {}
        else:
            resp.status_code = 200
            resp.json.return_value = [
                {
                    "trackName": "Starboy",
                    "artistName": "Cover Band",
                    "duration": 230.0,
                    "syncedLyrics": "[00:05.00]Cover band lyrics",
                },
                {
                    "trackName": "Starboy",
                    "artistName": "The Weeknd",
                    "duration": 230.0,
                    "syncedLyrics": "[00:05.00]Authentic The Weeknd lyrics",
                },
            ]
        return resp

    mock_get.side_effect = mock_side_effect

    lyrics = fetch_lyrics_smart("Starboy", "The Weeknd", duration_sec=230.0)
    assert lyrics is not None
    assert len(lyrics) == 1
    # Ensure the authentic artist's lyrics were selected
    assert lyrics[0].text == "Authentic The Weeknd lyrics"


def test_negative_cache_expiration():
    _LYRICS_CACHE.clear()

    # 1. Put negative result into cache
    _cache_put("unknown_track||unknown_artist", None)

    # Within TTL, it should return None without querying network
    with patch("lyricvibe.lyrics.fetcher._HTTP_SESSION.get") as mock_get:
        assert fetch_lyrics_smart("unknown_track", "unknown_artist") is None
        mock_get.assert_not_called()

    # 2. Simulate expired cache entry by modifying timestamp
    _LYRICS_CACHE["unknown_track||unknown_artist"] = (
        None,
        time.time() - (_NEGATIVE_CACHE_TTL + 5.0),
    )

    # After TTL, it must attempt fresh network lookup
    with patch("lyricvibe.lyrics.fetcher._HTTP_SESSION.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "syncedLyrics": "[00:03.00]Freshly found lyrics",
            "plainLyrics": "",
        }
        mock_get.return_value = mock_resp

        fresh = fetch_lyrics_smart(
            "unknown_track", "unknown_artist", duration_sec=180.0
        )
        assert fresh is not None
        assert fresh[0].text == "Freshly found lyrics"
        mock_get.assert_called()


def test_is_romanized_detects_scripts():
    assert is_romanized("Cause you knew that I'd be at one") is True
    assert is_romanized("Dilbar tere vaaste") is True
    assert is_romanized("क़रीब आओ ना") is False  # Devanagari
    assert is_romanized("اگر تم ساتھ ہو") is False  # Urdu
    assert is_romanized("ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ") is False  # Gurmukhi
    assert is_romanized("তুমি কেমন আছো") is False  # Bengali
    assert is_romanized("તમે કેમ છો") is False  # Gujarati
    assert is_romanized("") is True


def test_clean_track_title_producers_and_viral_tags():
    cases = [
        ("Praise God (Prod. Kanye West)", "Praise God"),
        ("Escapism. (Sped Up)", "Escapism."),
        ("Middle of the Night (Nightcore)", "Middle of the Night"),
        ("Die For You (Slowed + Reverb)", "Die For You"),
        ("Rockstar [Produced by Tank God]", "Rockstar"),
        ("Industry Baby (Clean Version)", "Industry Baby"),
        ("Day 'N' Nite (Nightcore)", "Day 'N' Nite"),
        ("Bad Guy (TikTok Version)", "Bad Guy"),
    ]
    for raw, expected in cases:
        cleaned = clean_track_title(raw)
        assert cleaned == expected, (
            f"Expected '{expected}', got '{cleaned}' for input '{raw}'"
        )


def test_get_primary_artist_extended_delimiters():
    assert get_primary_artist("Calvin Harris with Dua Lipa") == "Calvin Harris"
    assert get_primary_artist("David Guetta vs Benny Benassi") == "David Guetta"
    assert (
        get_primary_artist("Swedish House Mafia vs. Tinie Tempah")
        == "Swedish House Mafia"
    )
