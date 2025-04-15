import tkinter as tk
from screeninfo import get_monitors
import threading


class WindowTracker:
    def __init__(self):
        self.window_data = {}
        self.largest_monitor = None
        self.update_interval = 0.5
        self.running = True
        self._detect_largest_monitor()
        self._start_monitor_thread()

    def _detect_largest_monitor(self):
        monitors = get_monitors()
        self.largest_monitor = max(monitors, key=lambda m: m.width * m.height)

    def _start_monitor_thread(self):
        def monitor_loop():
            while self.running:
                try:
                    self._update_all_windows()
                except Exception as e:
                    print(f"Error in monitor_loop: {e}")
                threading.Event().wait(self.update_interval)

        threading.Thread(target=monitor_loop, daemon=True).start()

    def _update_all_windows(self):
        for window in list(self.window_data.keys()):
            if window.winfo_exists():
                self._update_window_position(window)
            else:
                self.unregister_window(window)

    def _update_window_position(self, window):
        try:
            if window.winfo_viewable():
                x = window.winfo_x() + window.winfo_width() // 2
                y = window.winfo_y() + window.winfo_height() // 2
                monitor = self.get_monitor_from_position(x, y)
                self.window_data[window]['monitor'] = monitor
                self.window_data[window]['x'] = x
                self.window_data[window]['y'] = y
        except tk.TclError:
            pass

    def register_window(self, window, parent=None):
        self.window_data[window] = {
            'parent': parent,
            'monitor': self.largest_monitor,
            'x': 0,
            'y': 0
        }
        self._update_window_position(window)

    def unregister_window(self, window):
        if window in self.window_data:
            del self.window_data[window]

    def get_effective_monitor(self, window):
        current = window
        visited = set()

        while current:
            if current in visited:
                break
            visited.add(current)

            if current.winfo_exists() and current in self.window_data:
                data = self.window_data[current]
                if data['monitor']:
                    return data['monitor']

            if hasattr(current, 'master'):
                current = current.master
            else:
                current = None

        return self.largest_monitor

    def get_monitor_from_position(self, x, y):
        for m in get_monitors():
            if m.x <= x <= m.x + m.width and m.y <= y <= m.y + m.height:
                return m
        return self.largest_monitor

    def stop(self):
        self.running = False


def _auto_configure_window(self):
    tracker = getattr(tk, '_global_tracker', None)
    if tracker:
        if isinstance(self, tk.Tk):
            monitor = tracker.largest_monitor
            self.geometry(f"{monitor.width}x{monitor.height}+{monitor.x}+{monitor.y}")
            tracker.register_window(self)
        elif isinstance(self, tk.Toplevel):
            self.update_idletasks()  # Asegurar dimensiones actualizadas

            # Obtener monitor efectivo
            monitor = tracker.get_effective_monitor(self.master) if self.master else tracker.largest_monitor

            # Calcular posición centrada
            width = self.winfo_width()
            height = self.winfo_height()

            x_pos = monitor.x + (monitor.width - width) // 2
            y_pos = monitor.y + (monitor.height - height) // 2

            self.geometry(f"+{x_pos}+{y_pos}")
            tracker.register_window(self, self.master)


def _new_tk_init(self, *args, **kwargs):
    original_tk_init = tk.Tk.__old_init__ if hasattr(tk.Tk, '__old_init__') else tk.Tk.__init__
    original_tk_init(self, *args, **kwargs)
    self._auto_configure_window = lambda: _auto_configure_window(self)
    self.after(100, self._auto_configure_window)


def _new_toplevel_init(self, master=None, **kwargs):
    original_toplevel_init = tk.Toplevel.__old_init__ if hasattr(tk.Toplevel, '__old_init__') else tk.Toplevel.__init__
    original_toplevel_init(self, master, **kwargs)
    self._auto_configure_window = lambda: _auto_configure_window(self)
    self.after(100, self._auto_configure_window)


# Preservar métodos originales
if not hasattr(tk.Tk, '__old_init__'):
    tk.Tk.__old_init__ = tk.Tk.__init__
if not hasattr(tk.Toplevel, '__old_init__'):
    tk.Toplevel.__old_init__ = tk.Toplevel.__init__

# Aplicar monkey patching
tk.Tk.__init__ = _new_tk_init
tk.Toplevel.__init__ = _new_toplevel_init


def start_tracker():
    if not hasattr(tk, '_global_tracker'):
        tk._global_tracker = WindowTracker()
    return tk._global_tracker