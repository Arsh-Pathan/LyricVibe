"""Tests for the 165Hz cinematic animation engine and easing physics."""

import math
import time

from lyricvibe.core.animation import (
    ANIMATION_CATALOG,
    ANIMATION_CATEGORIES,
    FADE_ANIMS,
    AnimationEngine,
    HandDrawnStroke,
    compute_syllable_count,
    compute_word_phonetic_weights,
    compute_word_timeline,
    pick_animation,
)


def test_animation_engine_init():
    engine = AnimationEngine()
    assert engine.curr_text == ""
    assert engine.highlight_word_idx == -1
    assert engine.words == []


def test_trigger_line_and_update():
    engine = AnimationEngine()
    text = "Magar phir aarzoon ka bikharna bhi zaroori tha"
    engine.trigger_line(text, duration=4.0)

    assert engine.curr_text == text
    assert len(engine.words) == 8
    assert engine.curr_duration == 4.0

    # Initial frame right after trigger
    state = engine.update()
    assert state is not None
    assert 0.0 <= state["curr_alpha"] <= 1.0
    assert len(state["word_alphas"]) == 8
    assert "curr_offset_y" in state
    assert "curr_scale" in state
    assert "blur_alpha" in state


def test_zero_and_negative_duration_handling():
    engine = AnimationEngine()
    # Should safely clamp to minimum duration (>= 1.2s) without crashing
    engine.trigger_line("Fast line", duration=0.0)
    assert engine.curr_duration >= 1.2

    state = engine.update()
    assert state is not None
    assert state["curr_alpha"] >= 0.0


def test_clear_line():
    engine = AnimationEngine()
    engine.trigger_line("To be cleared", duration=5.0)
    assert engine.curr_text == "To be cleared"

    engine.clear_line()
    assert engine.curr_text == ""
    assert engine.prev_text == "To be cleared"
    assert engine.highlight_word_idx == -1


def test_sync_to_audio_drift_correction():
    engine = AnimationEngine()
    engine.trigger_line("Drifting line", duration=5.0)
    initial_start = engine.curr_start_perf

    # 1. Micro-drift (0.2s drift) should adjust smoothly via low-pass filter
    engine.sync_to_audio(audio_elapsed_sec=0.2)
    assert engine.curr_start_perf != initial_start
    first_adjust = engine.curr_start_perf

    # 2. Large seek/scrub (> 0.75s drift) should snap immediately
    engine.sync_to_audio(audio_elapsed_sec=3.0)
    assert abs((time.perf_counter() - 3.0) - engine.curr_start_perf) < 0.05
    assert engine.curr_start_perf != first_adjust


def test_hand_drawn_stroke_generation():
    stroke = HandDrawnStroke(target_word_idx=2)
    assert stroke.target_word_idx == 2
    assert len(stroke.offsets) == 6
    # All offsets should be finite floating numbers
    assert all(isinstance(o, float) for o in stroke.offsets)


def test_pick_animation():
    assert len(ANIMATION_CATALOG) >= 50
    # Long line should pick a valid animation from catalog
    anim = pick_animation(
        "Long sentence that has more than four words in it", duration=4.5
    )
    assert isinstance(anim, str)
    assert len(anim) > 0

    # Short line should also pick a valid animation
    anim_short = pick_animation("Short", duration=1.5)
    assert isinstance(anim_short, str)
    assert len(anim_short) > 0


def test_all_catalog_animations_execute_cleanly():
    engine = AnimationEngine()
    for anim_name, _ in ANIMATION_CATALOG:
        engine.trigger_line(
            "Testing animation integrity: " + anim_name,
            duration=3.0,
            anim_type=anim_name,
        )
        assert engine.curr_anim_type == anim_name
        for _ in range(5):
            state = engine.update()
            assert state is not None
            assert isinstance(state["curr_alpha"], float)
            assert not math.isnan(state["curr_alpha"])
            assert not math.isnan(state["curr_scale"])
            assert not math.isnan(state["curr_offset_y"])


def test_animation_catalog_count_exceeds_seventy():
    assert len(ANIMATION_CATALOG) >= 70


def test_fade_animations_disable_motion_blur():
    engine = AnimationEngine()
    for fade_anim in FADE_ANIMS:
        engine.trigger_line("Fade test: " + fade_anim, duration=3.0, anim_type=fade_anim)
        state = engine.update()
        assert state["blur_alpha"] == 0.0
        assert state["blur_dist"] == 0.0


def test_new_cinematic_animations_properties():
    engine = AnimationEngine()

    # Prism refract should exhibit subtle horizontal displacement and skew
    engine.trigger_line("Prism refract test", duration=3.0, anim_type="prism_refract")
    state = engine.update()
    assert "curr_offset_x" in state
    assert "skew_x" in state

    # Card flip 3D should have pitch/yaw rotation and vertical drop
    engine.trigger_line("Card flip test", duration=3.0, anim_type="card_flip_3d")
    state = engine.update()
    assert "rotation" in state
    assert "curr_scale" in state

    # Isometric slide should have concurrent X and Y translation with skew
    engine.trigger_line("Isometric slide test", duration=3.0, anim_type="isometric_slide")
    state = engine.update()
    assert "curr_offset_x" in state
    assert "curr_offset_y" in state
    assert "skew_x" in state

    # Cinema scope unfold should exhibit scale expansion
    engine.trigger_line("Cinemascope test", duration=3.0, anim_type="cinema_scope_unfold")
    state = engine.update()
    assert state["curr_scale"] >= 0.90


def test_pick_animation_by_category():
    assert "smooth" in ANIMATION_CATEGORIES
    assert "kinetic" in ANIMATION_CATEGORIES
    assert "cinematic" in ANIMATION_CATEGORIES
    assert "vocal" in ANIMATION_CATEGORIES

    for cat in ["smooth", "kinetic", "cinematic", "vocal"]:
        for _ in range(10):
            anim = pick_animation("Test line for category selection", duration=3.0, category=cat)
            assert anim in ANIMATION_CATEGORIES[cat]


def test_animation_engine_style_selection():
    engine = AnimationEngine()

    engine.trigger_line("Smooth line", duration=3.0, anim_style="smooth")
    assert engine.curr_anim_type in ANIMATION_CATEGORIES["smooth"]

    engine.trigger_line("Kinetic line", duration=3.0, anim_style="kinetic")
    assert engine.curr_anim_type in ANIMATION_CATEGORIES["kinetic"]

    engine.trigger_line("Cinematic line", duration=3.0, anim_style="cinematic")
    assert engine.curr_anim_type in ANIMATION_CATEGORIES["cinematic"]


def test_syllable_counting():
    assert compute_syllable_count("I") == 1
    assert compute_syllable_count("love") == 1
    assert compute_syllable_count("baby") == 2
    assert compute_syllable_count("beautiful") == 3
    assert compute_syllable_count("forever") == 3
    assert compute_syllable_count("little") == 2
    assert compute_syllable_count("waited") == 2
    assert compute_syllable_count("walked") == 1
    assert compute_syllable_count("zindagi") == 3
    assert compute_syllable_count("tere") == 2
    assert compute_syllable_count("vaaste") == 2


def test_phonetic_weights_function_word_and_terminal_hold():
    words = ["I", "love", "you", "forever"]
    weights = compute_word_phonetic_weights(words)
    assert len(weights) == 4
    # "I" is a function word (discounted), "love" is content word
    assert weights[0] < weights[1]
    # "forever" is 3 syllables and terminal word (sustained)
    assert weights[3] > weights[1]


def test_compute_word_timeline():
    words = ["I", "love", "you"]
    starts, ends = compute_word_timeline(words, total_duration=3.0)
    assert len(starts) == 3
    assert len(ends) == 3
    assert starts[0] == 0.0
    for i in range(2):
        assert starts[i] < ends[i]
        assert ends[i] <= starts[i + 1]
    assert ends[-1] <= 3.0


def test_animation_engine_word_by_word_enhanced_lrc_sync():
    engine = AnimationEngine()
    # 3 words: "The club isn't" with timestamps at 10.0, 10.4, 11.0 and durations 0.4, 0.6, 0.5
    engine.trigger_line(
        "The club isn't",
        duration=3.0,
        word_times=[10.0, 10.4, 11.0],
        word_durations=[0.4, 0.6, 0.5],
    )
    assert engine.word_starts == [0.0, 0.4, 1.0]
    assert engine.word_ends == [0.4, 1.0, 1.5]

    # At elapsed 0.1s: word 0 ("The")
    engine.curr_start_perf = time.perf_counter() - 0.1
    state = engine.update()
    assert state["highlight_word_idx"] == 0

    # At elapsed 0.6s: word 1 ("club")
    engine.curr_start_perf = time.perf_counter() - 0.6
    state = engine.update()
    assert state["highlight_word_idx"] == 1

    # At elapsed 1.2s: word 2 ("isn't")
    engine.curr_start_perf = time.perf_counter() - 1.2
    state = engine.update()
    assert state["highlight_word_idx"] == 2

    # At elapsed 2.5s: vocal phrase finished, holds highlight on last word (idx 2)
    engine.curr_start_perf = time.perf_counter() - 2.5
    state = engine.update()
    assert state["highlight_word_idx"] == 2
