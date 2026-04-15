import logging
import tkinter as tk

import pytest
from loguru import logger

from tkloguru import LoggingInterceptHandler, LoguruWidget, setup_logger


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


def test_process_all_events_no_crash(widget: LoguruWidget) -> None:
    # Verify process_all_events does not raise with a normal master.
    widget.process_all_events()


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
    finally:
        logger.remove(external_sink_id)


def test_set_logging_level_routes_to_widget_queue(widget: LoguruWidget) -> None:
    setup_logger(widget)
    logger.info("routed-to-widget")

    record = widget.queue.get_nowait()
    assert record["message"] == "routed-to-widget"


# --- set_color validation ---


def test_set_color_valid_string(widget: LoguruWidget) -> None:
    widget.set_color("INFO", "#ff0000")
    assert widget.log_colors["INFO"] == "#ff0000"


def test_set_color_valid_tuple(widget: LoguruWidget) -> None:
    widget.set_color("CRITICAL", ("#ffffff", "#000000"))
    assert widget.log_colors["CRITICAL"] == ("#ffffff", "#000000")


def test_set_color_invalid_level(widget: LoguruWidget) -> None:
    with pytest.raises(ValueError, match="Unknown level"):
        widget.set_color("NOTLEVEL", "#ff0000")


def test_set_color_invalid_type(widget: LoguruWidget) -> None:
    with pytest.raises(TypeError):
        widget.set_color("INFO", 12345)


def test_set_color_wrong_tuple_length(widget: LoguruWidget) -> None:
    with pytest.raises(ValueError):
        widget.set_color("INFO", ("#fff",))


# --- LoggingInterceptHandler deduplication ---


def test_setup_logger_no_duplicate_intercept_handlers(tk_root: tk.Tk) -> None:
    instance = LoguruWidget(tk_root, intercept_logging=True)
    root_logger = logging.getLogger()

    try:
        setup_logger(instance)
        setup_logger(instance)  # second call must replace, not append

        handlers_for_widget = [
            h
            for h in root_logger.handlers
            if isinstance(h, LoggingInterceptHandler) and h.widget is instance
        ]
        assert len(handlers_for_widget) == 1, (
            "Expected exactly one handler per widget after repeated setup_logger calls."
        )
    finally:
        root_logger.handlers = [
            h
            for h in root_logger.handlers
            if not (isinstance(h, LoggingInterceptHandler) and h.widget is instance)
        ]
        if instance._sink_id is not None:
            try:
                logger.remove(instance._sink_id)
            except ValueError:
                pass
        instance.destroy()
