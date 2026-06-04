from engine.progress import ProgressEvent, emit


def test_progress_event_fields_and_percent():
    ev = ProgressEvent(stage="download", current=3, total=12, message="Annual Report 2024")
    assert ev.percent == 25
    assert "Annual Report 2024" in ev.message


def test_percent_is_zero_when_total_zero():
    assert ProgressEvent(stage="resolve", current=0, total=0, message="").percent == 0


def test_emit_is_noop_when_callback_is_none():
    emit(None, ProgressEvent("download", 1, 2, "x"))  # must not raise


def test_emit_calls_callback():
    seen = []
    emit(seen.append, ProgressEvent("download", 1, 2, "x"))
    assert seen and seen[0].current == 1
