import enum
import sys

LOGGER_COLOR_NONE = ""
LOGGER_COLOR_OFF = "\x1B[0m"
LOGGER_COLOR_RED = "\x1B[0;31m"
LOGGER_COLOR_LIGHT_RED = "\x1B[1;31m"
LOGGER_COLOR_GREEN = "\x1B[0;32m"
LOGGER_COLOR_LIGHT_GREEN = "\x1B[1;32m"
LOGGER_COLOR_YELLOW = "\x1B[0;33m"
LOGGER_COLOR_LIGHT_YELLOW = "\x1B[1;33m"
LOGGER_COLOR_BLUE = "\x1B[0;34m"
LOGGER_COLOR_LIGHT_BLUE = "\x1B[1;34m"
LOGGER_COLOR_MAGENTA = "\x1B[0;35m"
LOGGER_COLOR_LIGHT_MAGENTA = "\x1B[1;35m"
LOGGER_COLOR_CYAN = "\x1B[0;36m"
LOGGER_COLOR_LIGHT_CYAN = "\x1B[1;36m"

LOGGER_ERROR_COLOR = LOGGER_COLOR_LIGHT_RED
LOGGER_WARN_COLOR = LOGGER_COLOR_LIGHT_YELLOW
LOGGER_INFO_COLOR = LOGGER_COLOR_LIGHT_GREEN
LOGGER_DEBUG_COLOR = LOGGER_COLOR_LIGHT_CYAN


class Level(enum.Enum):
    ERROR = 0
    WARN = 1
    INFO = 2
    DEBUG = 3

    def __eq__(self, other):
        return self.value == other.value

    def __lt__(self, other):
        return self.value < other.value

    def __le__(self, other):
        return self.value <= other.value

    def __gt__(self, other):
        return self.value > other.value

    def __ge__(self, other):
        return self.value >= other.value


class Logger:
    def __init__(self, level: Level, colour: bool = True):
        self.level = level
        self.colour = colour

    def error(self, log):
        if self.level >= Level.ERROR:
            if self.colour:
                print(LOGGER_ERROR_COLOR + "---[ERROR] " + log + LOGGER_COLOR_OFF, file=sys.stderr)
            else:
                print("---[ERROR] " + log, file=sys.stderr)

    def warn(self, log):
        if self.level >= Level.WARN:
            if self.colour:
                print(LOGGER_WARN_COLOR + "---[WARN] " + log + LOGGER_COLOR_OFF)
            else:
                print("---[WARN] " + log)

    def info(self, log):
        if self.level >= Level.INFO:
            if self.colour:
                print(LOGGER_INFO_COLOR + "---[INFO] " + log + LOGGER_COLOR_OFF)
            else:
                print("---[INFO] " + log)

    def debug(self, log):
        if self.level >= Level.DEBUG:
            print("***[DEBUG] " + log)

    def e(self, log):
        self.error(log)

    def w(self, log):
        self.warn(log)

    def i(self, log):
        self.info(log)

    def d(self, log):
        self.debug(log)


logging = Logger(Level.INFO)
