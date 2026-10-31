"""Tests for the 165Hz cinematic animation engine and easing physics."""

import math
import time

from lyricvibe.core.animation import (
    ANIMATION_CATALOG,
    FADE_ANIMS,
    AnimationEngine,
    HandDrawnStroke,
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
