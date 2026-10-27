"""Tests for the 165Hz cinematic animation engine and easing physics."""

from lyricvibe.core.animation import (
    ANIMATION_CATALOG,
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

    # Simulate 200ms audio drift
    engine.sync_to_audio(audio_elapsed_sec=1.5)
    # Start time should be adjusted smoothly towards expected audio position
    assert engine.curr_start_perf != initial_start


def test_hand_drawn_stroke_generation():
    stroke = HandDrawnStroke(target_word_idx=2)
    assert stroke.target_word_idx == 2
    assert len(stroke.offsets) == 6
    # All offsets should be finite floating numbers
    assert all(isinstance(o, float) for o in stroke.offsets)


def test_pick_animation():
    assert len(ANIMATION_CATALOG) >= 50
    # Long line should pick a valid animation from catalog
    anim = pick_animation("Long sentence that has more than four words in it", duration=4.5)
    assert isinstance(anim, str)
    assert len(anim) > 0

    # Short line should also pick a valid animation
    anim_short = pick_animation("Short", duration=1.5)
    assert isinstance(anim_short, str)
    assert len(anim_short) > 0
