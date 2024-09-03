import tkinter as tk
from tkinter import ttk
import queue
from loguru import logger
import sys
import threading
import logging
from datetime import datetime

LEVELS = ["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]
LEVEL_NO_TO_NAME = {5: "TRACE", 10: "DEBUG", 20: "INFO", 25: "SUCCESS", 30: "WARNING", 40: "ERROR", 50: "CRITICAL"}

class LoggingInterceptHandler(logging.Handler):
    """
    A custom logging handler that intercepts standard logging messages and redirects them to a tkinter widget.

    This handler is used to capture messages from the standard logging module and display them in a custom tkinter widget.

    Args:
        widget (LoguruWidget): The tkinter widget to which the log messages will be sent.
    """

    def __init__(self, widget):
        super().__init__()
        self.widget = widget

    def emit(self, record):
        """
        Emit a log record by formatting it and sending it to the associated widget.

        Args:
            record (logging.LogRecord): The log record to be emitted.
        """
        try:
            msg = self.format(record)
            level = record.levelname
            self.widget.queue.put({"time": datetime.fromtimestamp(record.created), "level": level, "message": msg})
        except Exception:
            self.handleError(record)

class LoguruWidget(ttk.Frame):
    """
    A custom tkinter widget for displaying log messages using the loguru library.

    This widget creates a text area where log messages are displayed with customizable colors and formatting.

    Args:
        master (tk.Widget, optional): The parent widget. Defaults to None.
        show_scrollbar (bool, optional): Whether to show a scrollbar. Defaults to True.
        color_mode (str, optional): The coloring mode for log messages. Can be 'level', 'message', or 'full'. Defaults to 'level'.
        max_lines (int, optional): Maximum number of lines to display before starting to remove old ones. Defaults to 1000.
        intercept_logging (bool, optional): Whether to intercept messages from the standard logging module. Defaults to False.
        **kwargs: Additional keyword arguments to pass to the ttk.Frame constructor.
    """

    def __init__(self, master=None, show_scrollbar=True, color_mode='level', max_lines=1000, intercept_logging=False, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master
        self.queue = queue.Queue()
        self.show_scrollbar = show_scrollbar
        self.color_mode = color_mode
        self.max_lines = max_lines
        self.intercept_logging = intercept_logging
        self.log_colors = {
            "TRACE": "#999999",
            "DEBUG": "#4a4a4a",
            "INFO": "#3498db",
            "SUCCESS": "#2ecc71",
            "WARNING": "#f39c12",
            "ERROR": "#e74c3c",
            "CRITICAL": ("#ffffff", "#c0392b")
        }
        self._layout_manager = None
        self.create_widgets()
        self._is_destroyed = False
        self.after(100, self.check_queue)

    def create_widgets(self):
        """Create and configure the text widget and scrollbar."""
        self.text = tk.Text(self, wrap=tk.WORD, state=tk.DISABLED)
        
        if self.show_scrollbar:
            self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
            self.text.configure(yscrollcommand=self.scrollbar.set)
        
        self.update_tag_colors()
    
    def _configure_layout(self):
        """Configure the layout of child widgets based on the chosen geometry manager."""
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

    def update_tag_colors(self):
        """Update the color tags for different log levels in the text widget."""
        for level, color in self.log_colors.items():
            if isinstance(color, tuple):
                self.text.tag_configure(level, foreground=color[0], background=color[1])
            else:
                self.text.tag_configure(level, foreground=color)

    def check_queue(self):
        """Check the queue for new log messages and update the widget."""
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

    def update_widget(self, record):
        """
        Update the text widget with a new log message.

        Args:
            record (dict): A dictionary containing the log record information.
        """
        self.text.configure(state=tk.NORMAL)
        
        time_str = record["time"].strftime("%Y-%m-%d %H:%M:%S")
        level = record["level"]
        message = record["message"]
        
        if self.color_mode == 'full':
            self.text.insert(tk.END, f"{time_str} | {level:8} | {message}\n", level)
        elif self.color_mode == 'message':
            self.text.insert(tk.END, f"{time_str} | {level:8} | ", "")
            self.text.insert(tk.END, f"{message}\n", level)
        else:  # 'level' mode (default)
            self.text.insert(tk.END, f"{time_str} | ", "")
            self.text.insert(tk.END, f"{level:8}", level)
            self.text.insert(tk.END, f" | {message}\n", "")
        
        if int(self.text.index('end-1c').split('.')[0]) > self.max_lines:
            self.text.delete('1.0', '2.0')
        
        self.text.see(tk.END)
        self.text.configure(state=tk.DISABLED)

    def sink(self, message):
        """
        A sink function to be used with loguru.

        This method is called by loguru for each log message and puts the message into the queue.

        Args:
            message (loguru.Message): The log message object from loguru.
        """
        record = message.record
        self.queue.put({
            "time": record["time"],
            "level": record["level"].name,
            "message": record["message"]
        })

    def set_color(self, level, color):
        """
        Set the color for a specific log level.

        Args:
            level (str): The log level to set the color for.
            color (str or tuple): The color to set. Can be a string for foreground color only,
                                  or a tuple of (foreground, background) colors.
        """
        self.log_colors[level] = color
        self.update_tag_colors()
    
    @staticmethod
    def get_logging_level():
        """
        Get the current logging level.

        Returns:
            str: The name of the current logging level.
        """
        current_level_no = logger._core.min_level
        current_level = LEVEL_NO_TO_NAME.get(current_level_no, "INFO")  # Default to INFO if level is not found
        return current_level

    def set_logging_level(self, level):
        """
        Set the logging level for the loguru logger.

        Args:
            level (str): The name of the logging level to set.
        """
        logger.remove()
        logger.add(self.sink, level=level)

    def pack(self, **kwargs):
        """Pack the widget and its children."""
        if self._layout_manager is None:
            self._layout_manager = "pack"
            self._configure_layout()
        super().pack(**kwargs)

    def grid(self, **kwargs):
        """Grid the widget and its children."""
        if self._layout_manager is None:
            self._layout_manager = "grid"
            self._configure_layout()
        super().grid(**kwargs)
    
    def place(self, **kwargs):
        """Place the widget and configure its children for pack layout."""
        if self._layout_manager is None:
            self._layout_manager = "pack"
            self._configure_layout()
        super().place(**kwargs)

    def destroy(self):
        """Destroy the widget and stop the queue checking."""
        self._is_destroyed = True
        super().destroy()

    def process_all_events(self):
        """Process all pending events in the Tkinter event loop."""
        while self.master.dooneevent(tk._tkinter.ALL_EVENTS | tk._tkinter.DONT_WAIT):
            pass
        self.update()

def setup_logger(widget):
    """
    Set up the loguru logger to use the custom widget as a sink.

    If intercept_logging is True, also set up interception of standard logging messages.

    Args:
        widget (LoguruWidget): The widget to use as a sink for log messages.
    """
    logger.remove()
    logger.add(widget.sink, backtrace=True, diagnose=True)
    
    if widget.intercept_logging:
        logging.getLogger().addHandler(LoggingInterceptHandler(widget))
        logging.getLogger().setLevel(logging.DEBUG)


# Example usage
if __name__ == "__main__":
    root = tk.Tk()
    root.title("LoguruWidget Example")
    root.geometry("800x600")

    log_widget = LoguruWidget(root, show_scrollbar=True, color_mode='level', max_lines=1000, intercept_logging=True)
    log_widget.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    setup_logger(log_widget)

    # Add console handler for debugging
    logger.add(sys.stdout, level="DEBUG")

    def generate_sample_logs():
        """Generate sample log messages for demonstration purposes."""
        logger.debug("This is a debug message")
        logger.info("This is an info message")
        logger.success("This is a success message")
        logger.warning("This is a warning message")
        logger.error("This is an error message")
        logger.critical("This is a critical message")
        
        # Test standard logging
        logging.debug("Standard logging: debug message")
        logging.info("Standard logging: info message")
        logging.warning("Standard logging: warning message")
        logging.error("Standard logging: error message")
        logging.critical("Standard logging: critical message")

    # Create buttons to generate logs and change settings
    button_frame = ttk.Frame(root)
    button_frame.pack(fill=tk.X, padx=10, pady=5)

    generate_logs_button = ttk.Button(button_frame, text="Generate Sample Logs", command=generate_sample_logs)
    generate_logs_button.pack(side=tk.LEFT, padx=5)

    def change_color_mode():
        """Change the color mode of the log widget."""
        current_mode = log_widget.color_mode
        new_mode = 'full' if current_mode == 'level' else 'level' if current_mode == 'message' else 'message'
        log_widget.color_mode = new_mode
        
        current_level = log_widget.get_logging_level()
        log_func = getattr(logger, current_level.lower())
        log_func(f"Changed color mode to: {new_mode}")

    color_mode_button = ttk.Button(button_frame, text="Change Color Mode", command=change_color_mode)
    color_mode_button.pack(side=tk.LEFT, padx=5)

    def change_log_level():
        """Change the logging level of the log widget."""
        current_level = log_widget.get_logging_level()
        current_index = LEVELS.index(current_level)
        new_index = (current_index + 1) % len(LEVELS)
        new_level = LEVELS[new_index]
        
        log_widget.set_logging_level(new_level)
        log_func = getattr(logger, new_level.lower())
        log_func(f"Changed logging level from {current_level} to: {new_level}")

    log_level_button = ttk.Button(button_frame, text="Change Log Level", command=change_log_level)
    log_level_button.pack(side=tk.LEFT, padx=5)

    root.mainloop()