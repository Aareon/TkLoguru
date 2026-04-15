import tkinter as tk
from queue import Empty

import pytest
from loguru import logger

from tkloguru import LoguruWidget, setup_logger


@pytest.fixture
def tk_root() -> tk.Tk:
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk is unavailable in this environment: {exc}")

    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def widget(tk_root: tk.Tk) -> LoguruWidget:
    instance = LoguruWidget(tk_root)
    yield instance
    if instance._sink_id is not None:
        try:
            logger.remove(instance._sink_id)
        except ValueError:
            pass
    instance.destroy()


def test_setup_logger_keeps_existing_sinks(widget: LoguruWidget) -> None:
    captured: list[str] = []
    external_sink_id = logger.add(lambda message: captured.append(str(message)), level="DEBUG")

    try:
        setup_logger(widget)
        logger.info("sink-preservation-check")

        assert captured, "Expected external sink to remain active after setup_logger()."
        record = widget.queue.get_nowait()
        assert record["message"] == "sink-preservation-check"
    finally:
        logger.remove(external_sink_id)


def test_process_all_events_handles_missing_master() -> None:
    try:
        instance = LoguruWidget(master=None)
    except tk.TclError as exc:
        pytest.skip(f"Tk is unavailable in this environment: {exc}")

    try:
        instance.process_all_events()
    finally:
        if instance._sink_id is not None:
            try:
                logger.remove(instance._sink_id)
            except ValueError:
                pass
        instance.destroy()


def test_set_logging_level_tracks_widget_state(widget: LoguruWidget) -> None:
    widget.set_logging_level("warning")

    assert widget.get_logging_level() == "WARNING"


def test_set_logging_level_rejects_unknown_level(widget: LoguruWidget) -> None:
    with pytest.raises(ValueError):
        widget.set_logging_level("UNKNOWN")


def test_set_logging_level_keeps_external_sinks(widget: LoguruWidget) -> None:
    captured: list[str] = []
    external_sink_id = logger.add(lambda message: captured.append(str(message)), level="DEBUG")

    try:
        widget.set_logging_level("INFO")
        logger.info("external-sink-still-active")

        assert captured, "Expected external sink to remain active after set_logging_level()."

        queued = []
        while True:
            queued.append(widget.queue.get_nowait())
    except Empty:
        pass
    finally:
        logger.remove(external_sink_id)

    assert any(item["message"] == "external-sink-still-active" for item in queued)
