import warnings
warnings.filterwarnings("ignore", category=SyntaxWarning, module="ttkbootstrap.localization.msgs")
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkloguru import LoguruWidget, setup_logger
from loguru import logger
import threading
import time

class TkLoguruDemo(ttk.Window):
    def __init__(self):
        super().__init__(themename="darkly")
        self.title("TkLoguru with ttkbootstrap Demo")
        self.geometry("800x600")

        self.create_widgets()
        setup_logger(self.log_widget)

    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=BOTH, expand=YES, padx=10, pady=10)

        # Create the LoguruWidget
        self.log_widget = LoguruWidget(main_frame, show_scrollbar=True, color_mode='level', max_lines=1000)
        self.log_widget.pack(side=LEFT, fill=BOTH, expand=YES)

        # Create a frame for buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=RIGHT, fill=Y, padx=(10, 0))

        # Add buttons for different log levels
        levels = ['debug', 'info', 'success', 'warning', 'error', 'critical']
        for level in levels:
            btn = ttk.Button(
                button_frame, 
                text=level.capitalize(),
                command=lambda l=level: self.log_message(l),
                style=f"{level.upper()}.TButton"
            )
            btn.pack(fill=X, pady=5)

        # Add a button to start continuous logging
        self.continuous_logging = False
        self.continuous_log_btn = ttk.Button(
            button_frame,
            text="Start Continuous Log",
            command=self.toggle_continuous_log,
            style="info.Outline.TButton"
        )
        self.continuous_log_btn.pack(fill=X, pady=5)

    def log_message(self, level):
        log_func = getattr(logger, level)
        log_func(f"This is a {level} message")

    def toggle_continuous_log(self):
        self.continuous_logging = not self.continuous_logging
        if self.continuous_logging:
            self.continuous_log_btn.config(text="Stop Continuous Log")
            threading.Thread(target=self.continuous_log, daemon=True).start()
        else:
            self.continuous_log_btn.config(text="Start Continuous Log")

    def continuous_log(self):
        levels = ['debug', 'info', 'success', 'warning', 'error', 'critical']
        count = 0
        while self.continuous_logging:
            level = levels[count % len(levels)]
            self.log_message(level)
            count += 1
            time.sleep(0.5)

if __name__ == "__main__":
    app = TkLoguruDemo()
    app.mainloop()
