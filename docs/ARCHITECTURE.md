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

## Core Components

### 1. Media Telemetry Engine (`spotify_listener.ps1` & `spotify_client.py`)
- **WinRT Integration**: Interacts directly with Windows 10/11 `GlobalSystemMediaTransportControlsSessionManager` via PowerShell WinRT bindings.
- **Zero API Authentication**: Intercepts local Windows SMTC media sessions. It requires no Spotify developer account, client IDs, or Spotify Premium subscriptions.
- **Fault-Tolerant State Recovery**: Automatically retains metadata across transient Windows audio handoffs with a 1200ms task timeout to eliminate single-frame dropouts when switching tracks.
- **IPC Streaming**: Streams compressed JSON packets over stdout at 250ms intervals containing `is_playing`, `track`, `artist`, `album`, `position`, `updated_at`, and `duration`.

### 2. Lyrics Fetcher & Normalizer (`lyrics_fetcher.py`)
- **Metadata Sanitization**: Cleans Spotify track metadata using aggressive regex pipelines to strip noise that breaks exact-match lookups:
  - Strips movie tags: `From "Movie"`, `Soundtrack Version`, `Original Motion Picture`
  - Strips remaster tags: `Remastered 2011`, `2024 Remaster`, `Deluxe Edition`
  - Strips featured artists: `feat.`, `ft.`, `with ...`
- **LRCLIB Integration**: Fetches time-synced `.lrc` strings from [LRCLIB](https://lrclib.net).
- **In-Memory Caching**: Caches parsed timestamp arrays in memory (`_LYRICS_CACHE`) to provide instant 0ms retrieval on repeated or back-tracked songs.
- **Race Condition Prevention**: Employs monotonically incrementing request tags (`_current_fetch_id`) to discard stale responses when tracks are skipped rapidly.

### 3. Transliteration Engine (`hinglish_converter.py`)
- **Devanagari to Roman Hinglish**: Maps vowels, consonants, conjuncts, matras, and nuktas (`क़`, `ख़`, `ग़`, `ज़`, `फ़`) to natural phonetic Latin text.
- **Schwa Deletion**: Implements Hindi phonetic rules to drop trailing schwas (`raama` -> `ram`, `namaste` preservation).
- **Perso-Arabic Urdu Support**: Converts Urdu alphabet characters and ligature forms into readable Roman script.
- **Sanitization Safety Net**: Ensures non-Latin characters are converted or removed before sending text to the renderer.

### 4. 165Hz Animation & Rendering Engine (`animation_engine.py` & `main.py`)
- **Sub-Millisecond Interpolation**: Calculates progress using `time.perf_counter()` to achieve silky 60–240Hz rendering aligned with monitor refresh rates.
- **Continuous Lift-Out Physics**: Outgoing lines start strictly at `0.0px` vertical offset and glide smoothly upward to `-22.0px` via `math.pow(t_out, 1.3) * 22.0`, eliminating sudden position snap glitches.
- **Clamped Motion Blur**: Computes sub-frame velocity vectors with momentum decay, strictly clamped to a tight spread (`[-4.0px, +4.0px]`) to prevent ghost text duplicates.
- **Precision Text Anchoring**: Pre-measures full line widths and character positions with preserved typographic kerning to avoid horizontal jitter during word transitions.

### 5. Settings & IPC Control (`settings_window.py` & `settings_manager.py`)
- **Single-Instance Enforcement**: Utilizes a local named pipe / socket IPC mechanism. Running a second instance acts as a trigger to immediately unhide and focus the dark-themed settings customizer.
- **JSON Persistence**: Persists user preferences (font family, font size, vertical position, highlight mode, motion blur length, and timing offsets) in `settings.json`.
