import webview
import os

class WindowFunctions:
    def __init__(self, window=None):
        self.window = window

    def set_window(self, window):
        self.window = window

    def minimize_window(self):
        self.window.minimize()

    def close_window(self):
        self.window.destroy()
        os._exit(0)

