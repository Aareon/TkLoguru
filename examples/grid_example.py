import tkinter as tk
from tkinter import ttk
from loguru import logger
import sys

# Assuming the LoguruWidget class is in a file named loguru_widget.py
from tkloguru import LoguruWidget, setup_logger

class LoguruWidgetGridExample:
    """
    An example application demonstrating the use of LoguruWidget with grid layout.
    """

    def __init__(self, root):
        """
        Initialize the example application.

        Args:
            root (tk.Tk): The root window of the application.
        """
        self.root = root
        self.root.title("LoguruWidget Grid Example")
        self.root.geometry("800x600")

        self.create_widgets()
        self.setup_logging()

    def create_widgets(self):
        """Create and arrange the widgets using grid layout."""
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0)

        # Create a frame for the log widget
        log_frame = ttk.Frame(self.root)
        log_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 5))
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)

        # Create the LoguruWidget
        self.log_widget = LoguruWidget(log_frame, show_scrollbar=True, color_mode='level', max_lines=1000)
        self.log_widget.grid(row=0, column=0, sticky="nsew")

        # Create a frame for buttons
        button_frame = ttk.Frame(self.root)
        button_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        button_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Create buttons
        generate_logs_button = ttk.Button(button_frame, text="Generate Sample Logs", command=self.generate_sample_logs)
        generate_logs_button.grid(row=0, column=0, padx=5)

        change_color_mode_button = ttk.Button(button_frame, text="Change Color Mode", command=self.change_color_mode)
        change_color_mode_button.grid(row=0, column=1, padx=5)

        change_log_level_button = ttk.Button(button_frame, text="Change Log Level", command=self.change_log_level)
        change_log_level_button.grid(row=0, column=2, padx=5)

    def setup_logging(self):
        """Set up the logger to use the LoguruWidget."""
        setup_logger(self.log_widget)
        logger.add(sys.stdout, level="DEBUG")  # Add console handler for debugging

    def generate_sample_logs(self):
        """Generate sample log messages for demonstration purposes."""
        logger.debug("This is a debug message")
        logger.info("This is an info message")
        logger.success("This is a success message")
        logger.warning("This is a warning message")
        logger.error("This is an error message")
        logger.critical("This is a critical message")

    def change_color_mode(self):
        """Change the color mode of the log widget."""
        current_mode = self.log_widget.color_mode
        new_mode = 'full' if current_mode == 'level' else 'level' if current_mode == 'message' else 'message'
        self.log_widget.color_mode = new_mode
        
        logger.info(f"Changed color mode to: {new_mode}")

    def change_log_level(self):
        """Change the logging level of the log widget."""
        current_level = self.log_widget.get_logging_level()
        levels = ["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]
        current_index = levels.index(current_level)
        new_index = (current_index + 1) % len(levels)
        new_level = levels[new_index]
        
        self.log_widget.set_logging_level(new_level)
        logger.log(new_level, f"Changed logging level from {current_level} to: {new_level}")

def main():
    root = tk.Tk()
    app = LoguruWidgetGridExample(root)
    root.mainloop()

if __name__ == "__main__":
    main()