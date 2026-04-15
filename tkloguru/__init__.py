from __future__ import annotations

import logging
import queue
import sys
import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Any, Literal

from loguru import logger
from pydantic import BaseModel, Field

LEVELS = ["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]
LEVEL_NO_TO_NAME = {
    5: "TRACE",
    10: "DEBUG",
    20: "INFO",
    25: "SUCCESS",
    30: "WARNING",
    40: "ERROR",
    50: "CRITICAL",
}

ColorType = str | tuple[str, str]


class LogRecord(BaseModel):
    time: datetime
    level: str
    message: str


class WidgetConfig(BaseModel):
    show_scrollbar: bool = True
    color_mode: Literal["level", "message", "full"] = "level"
    max_lines: int = Field(default=1000, ge=1)
    intercept_logging: bool = False


class LoggingInterceptHandler(logging.Handler):
    """
    Intercepts standard logging messages and forwards them to a LoguruWidget.

    Args:
        widget: Widget instance receiving formatted log records.
    """

    def __init__(self, widget: LoguruWidget):
        super().__init__()
        self.widget = widget

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            normalized = LogRecord(
                time=datetime.fromtimestamp(record.created),
                level=record.levelname,
                message=msg,
            )
            self.widget.queue.put(normalized.model_dump())
        except Exception:
            self.handleError(record)


class LoguruWidget(ttk.Frame):
    """
    A custom tkinter widget for displaying log messages using loguru.

    Args:
        master: Parent widget.
        show_scrollbar: Whether to show a scrollbar.
        color_mode: One of "level", "message", or "full".
        max_lines: Maximum number of lines retained in the text widget.
        intercept_logging: Whether to intercept stdlib logging records.
        **kwargs: Extra ttk.Frame keyword arguments.
    """

    def __init__(
        self,
        master: tk.Widget | None = None,
        show_scrollbar: bool = True,
        color_mode: str = "level",
        max_lines: int = 1000,
        intercept_logging: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, **kwargs)
        self.master = master
        self.queue: queue.Queue[dict[str, Any]] = queue.Queue()

        config = WidgetConfig(
            show_scrollbar=show_scrollbar,
            color_mode=color_mode,
            max_lines=max_lines,
            intercept_logging=intercept_logging,
        )

        self.show_scrollbar = config.show_scrollbar
        self.color_mode = config.color_mode
        self.max_lines = config.max_lines
        self.intercept_logging = config.intercept_logging

        self.log_colors: dict[str, ColorType] = {
            "TRACE": "#999999",
            "DEBUG": "#4a4a4a",
            "INFO": "#3498db",
            "SUCCESS": "#2ecc71",
            "WARNING": "#f39c12",
            "ERROR": "#e74c3c",
            "CRITICAL": ("#ffffff", "#c0392b"),
        }

        self._layout_manager: str | None = None
        self._is_destroyed = False

        self.create_widgets()
        self.after(100, self.check_queue)

    def create_widgets(self) -> None:
        """Create and configure the text widget and optional scrollbar."""
        self.text = tk.Text(self, wrap=tk.WORD, state=tk.DISABLED)

        if self.show_scrollbar:
            self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
            self.text.configure(yscrollcommand=self.scrollbar.set)

        self.update_tag_colors()

    def _configure_layout(self) -> None:
        """Configure children based on the selected geometry manager."""
        if self._layout_manager == "pack":
            if self.show_scrollbar:
                self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.text.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        elif self._layout_manager == "grid":
            self.grid_rowconfigure(0, weight=1)
            self.grid_columnconfigure(0, weight=1)
            self.text.grid(row=0, column=0, sticky="nsew")
            if self.show_scrollbar:
                self.scrollbar.grid(row=0, column=1, sticky="ns")
                self.grid_columnconfigure(1, weight=0)

    def update_tag_colors(self) -> None:
        """Update text tags for all configured log levels."""
        for level, color in self.log_colors.items():
            if isinstance(color, tuple):
                self.text.tag_configure(level, foreground=color[0], background=color[1])
            else:
                self.text.tag_configure(level, foreground=color)

    def check_queue(self) -> None:
        """Consume queued records and schedule the next check."""
        if self._is_destroyed:
            return

        try:
            while True:
                record = self.queue.get_nowait()
                self.update_widget(record)
        except queue.Empty:
            pass
        finally:
            if not self._is_destroyed:
                self.after(100, self.check_queue)

    def update_widget(self, record: dict[str, Any] | LogRecord) -> None:
        """Render a single log record in the text widget."""
        normalized = record if isinstance(record, LogRecord) else LogRecord.model_validate(record)

        self.text.configure(state=tk.NORMAL)

        time_str = normalized.time.strftime("%Y-%m-%d %H:%M:%S")
        level = normalized.level
        message = normalized.message

        if self.color_mode == "full":
            self.text.insert(tk.END, f"{time_str} | {level:8} | {message}\n", level)
        elif self.color_mode == "message":
            self.text.insert(tk.END, f"{time_str} | {level:8} | ", "")
            self.text.insert(tk.END, f"{message}\n", level)
        else:
            self.text.insert(tk.END, f"{time_str} | ", "")
            self.text.insert(tk.END, f"{level:8}", level)
            self.text.insert(tk.END, f" | {message}\n", "")

        if int(self.text.index("end-1c").split(".")[0]) > self.max_lines:
            self.text.delete("1.0", "2.0")

        self.text.see(tk.END)
        self.text.configure(state=tk.DISABLED)

    def sink(self, message: Any) -> None:
        """Loguru sink function used to push messages to the UI queue."""
        record = message.record
        normalized = LogRecord(
            time=record["time"],
            level=record["level"].name,
            message=record["message"],
        )
        self.queue.put(normalized.model_dump())

    def set_color(self, level: str, color: ColorType) -> None:
        """Set the color mapping for a log level and refresh tags."""
        if level not in LEVELS:
            valid_levels = ", ".join(LEVELS)
            raise ValueError(f"Unknown level '{level}'. Expected one of: {valid_levels}")

        if not isinstance(color, str | tuple):
            raise TypeError("Color must be a color string or (foreground, background) tuple.")

        if isinstance(color, tuple) and len(color) != 2:
            raise ValueError("Color tuple must contain exactly (foreground, background).")

        self.log_colors[level] = color
        self.update_tag_colors()

    @staticmethod
    def get_logging_level() -> str:
        """Get the currently configured Loguru minimum level name."""
        current_level_no = logger._core.min_level
        return LEVEL_NO_TO_NAME.get(current_level_no, "INFO")

    def set_logging_level(self, level: str) -> None:
        """Set the Loguru sink level for this widget."""
        logger.remove()
        logger.add(self.sink, level=level)

    def pack(self, **kwargs: Any) -> None:
        """Pack the widget and initialize child layout on first call."""
        if self._layout_manager is None:
            self._layout_manager = "pack"
            self._configure_layout()
        super().pack(**kwargs)

    def grid(self, **kwargs: Any) -> None:
        """Grid the widget and initialize child layout on first call."""
        if self._layout_manager is None:
            self._layout_manager = "grid"
            self._configure_layout()
        super().grid(**kwargs)

    def place(self, **kwargs: Any) -> None:
        """Place the widget and default child layout to pack semantics."""
        if self._layout_manager is None:
            self._layout_manager = "pack"
            self._configure_layout()
        super().place(**kwargs)

    def destroy(self) -> None:
        """Destroy the widget and stop queue polling."""
        self._is_destroyed = True
        super().destroy()

    def process_all_events(self) -> None:
        """Process all pending Tkinter events immediately."""
        while self.master.dooneevent(tk._tkinter.ALL_EVENTS | tk._tkinter.DONT_WAIT):
            pass
        self.update()


def setup_logger(widget: LoguruWidget) -> None:
    """
    Configure Loguru to send logs to the widget sink.

    If intercept_logging is enabled on the widget, stdlib logging is also intercepted.
    """
    logger.remove()
    logger.add(widget.sink, backtrace=True, diagnose=True)

    if widget.intercept_logging:
        logging.getLogger().addHandler(LoggingInterceptHandler(widget))
        logging.getLogger().setLevel(logging.DEBUG)


if __name__ == "__main__":
    root = tk.Tk()
    root.title("LoguruWidget Example")
    root.geometry("800x600")

    log_widget = LoguruWidget(
        root,
        show_scrollbar=True,
        color_mode="level",
        max_lines=1000,
        intercept_logging=True,
    )
    log_widget.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    setup_logger(log_widget)

    logger.add(sys.stdout, level="DEBUG")

    def generate_sample_logs() -> None:
        logger.debug("This is a debug message")
        logger.info("This is an info message")
        logger.success("This is a success message")
        logger.warning("This is a warning message")
        logger.error("This is an error message")
        logger.critical("This is a critical message")

        logging.debug("Standard logging: debug message")
        logging.info("Standard logging: info message")
        logging.warning("Standard logging: warning message")
        logging.error("Standard logging: error message")
        logging.critical("Standard logging: critical message")

    button_frame = ttk.Frame(root)
    button_frame.pack(fill=tk.X, padx=10, pady=5)

    generate_logs_button = ttk.Button(
        button_frame, text="Generate Sample Logs", command=generate_sample_logs
    )
    generate_logs_button.pack(side=tk.LEFT, padx=5)

    def change_color_mode() -> None:
        current_mode = log_widget.color_mode
        new_mode = (
            "full"
            if current_mode == "level"
            else "level"
            if current_mode == "message"
            else "message"
        )
        log_widget.color_mode = new_mode

        current_level = log_widget.get_logging_level()
        log_func = getattr(logger, current_level.lower())
        log_func(f"Changed color mode to: {new_mode}")

    color_mode_button = ttk.Button(
        button_frame, text="Change Color Mode", command=change_color_mode
    )
    color_mode_button.pack(side=tk.LEFT, padx=5)

    def change_log_level() -> None:
        current_level = log_widget.get_logging_level()
        current_index = LEVELS.index(current_level)
        new_index = (current_index + 1) % len(LEVELS)
        new_level = LEVELS[new_index]

        log_widget.set_logging_level(new_level)
        log_func = getattr(logger, new_level.lower())
        log_func(f"Changed logging level from {current_level} to: {new_level}")

    log_level_button = ttk.Button(
        button_frame, text="Change Log Level", command=change_log_level
    )
    log_level_button.pack(side=tk.LEFT, padx=5)

    root.mainloop()


__all__ = ["LoguruWidget", "setup_logger", "LEVELS", "LEVEL_NO_TO_NAME"]
