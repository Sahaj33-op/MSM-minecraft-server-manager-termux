"""Terminal color helpers."""


class ColorScheme:
    """ANSI color palette used by the CLI."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    BG_RED = "\033[101m"

    SUCCESS = GREEN
    ERROR = RED
    WARNING = YELLOW
    INFO = BLUE
    DEBUG = DIM

    @classmethod
    def disable_colors(cls) -> None:
        for attr in dir(cls):
            if attr.startswith("_"):
                continue
            value = getattr(cls, attr)
            if not callable(value):
                setattr(cls, attr, "")


C = ColorScheme()
