# System Architecture

LyricVibe is built around an event-driven, decoupled pipeline designed for low resource consumption, zero-latency audio tracking, and 165Hz hardware-accelerated rendering.

---

## High-Level Architecture

```mermaid
flowchart TD
    Spotify["Spotify Desktop Client"] -->|WinRT SMTC Events| Listener["spotify_listener.ps1"]
    Listener -->|JSON over Stdout Pipe (250ms)| Client["spotify_client.py"]
    Client -->|Playback State Signal| Overlay["main.py (Overlay Window)"]
    
    Overlay -->|Track Change Event| Fetcher["lyrics_fetcher.py"]
    Fetcher -->|Clean Title & Artist| LRCLIB["LRCLIB Open API"]
    LRCLIB -->|Synced LRC Text| Translit["hinglish_converter.py"]
    Translit -->|Devanagari & Urdu Transliteration| Overlay
    
    Overlay -->|Timestamp Updates (6ms)| Engine["animation_engine.py"]
    Engine -->|Sub-frame Easing & Motion Vectors| Painter["QPainter Direct Draw"]
    Painter -->|Direct2D / OpenGL Surface| Screen["165Hz Transparent Desktop Surface"]
```

---

## Core Components & Modular Architecture

### 1. Media Telemetry Engine (`src/lyricvibe/media/`)
- **`spotify_listener.ps1`**: Background WinRT script reading Windows SMTC sessions with fault-tolerant state recovery.
- **`client.py`**: Non-blocking Python subprocess reader and state deserializer.
- **Zero API Authentication**: Intercepts local Windows SMTC media sessions. It requires no Spotify developer account, client IDs, or Spotify Premium subscriptions.
- **IPC Streaming**: Streams compressed JSON packets over stdout at 250ms intervals containing `is_playing`, `track`, `artist`, `album`, `position`, `updated_at`, and `duration`.

### 2. Lyrics Ingestion & Caching (`src/lyricvibe/lyrics/`)
- **`fetcher.py`**: Query engine for [LRCLIB](https://lrclib.net) with in-memory caching (`_LYRICS_CACHE`).
- **Metadata Sanitization**: Cleans Spotify track metadata using aggressive regex pipelines to strip noise that breaks exact-match lookups:
  - Strips movie tags: `From "Movie"`, `Soundtrack Version`, `Original Motion Picture`
  - Strips remaster tags: `Remastered 2011`, `2024 Remaster`, `Deluxe Edition`
  - Strips featured artists: `feat.`, `ft.`, `with ...`
- **Race Condition Prevention**: Employs monotonically incrementing request tags (`_current_fetch_id`) to discard stale responses when tracks are skipped rapidly.

### 3. Core Physics & Transliteration (`src/lyricvibe/core/`)
- **`transliteration.py`**: Converts Devanagari (Hindi) and Perso-Arabic (Urdu) scripts into clean phonetic Roman Hinglish with schwa deletion and nukta handling.
- **`animation.py`**: 165Hz physics engine, sub-millisecond continuous lift-out easing, and clamped motion blur vectors.
- **`paths.py`**: Centralized asset and directory resolution supporting both source and PyInstaller environments.
- **`config.py`**: Static defaults for overlay dimensions and chroma keying.

### 4. User Interface & Settings (`src/lyricvibe/ui/` & `src/lyricvibe/utils/`)
- **`ui/overlay.py`**: Frameless, transparent 165Hz PyQt6 overlay with Direct2D hardware acceleration and single-instance IPC server.
- **`ui/settings.py`**: Material Design 3 dark-themed settings customizer with live interactive animation preview.
- **`utils/settings.py`**: Persistent JSON settings management and 16-color ultra-bright neon palette definitions.
