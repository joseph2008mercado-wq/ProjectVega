"""Screen-independent sizing policy in Qt logical pixels (already DPI-scaled)."""


def initial_size(available_width: int, available_height: int) -> tuple[int, int]:
    # Leave room for native titlebar, borders, taskbar and a little desktop.
    return max(1, min(900, available_width - 48)), max(1, min(940, available_height - 64))
