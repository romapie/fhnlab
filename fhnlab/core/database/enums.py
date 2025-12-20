from enum import Enum


class ExperimentStatus(str, Enum):
    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class ExecutionTarget(str, Enum):
    LOCAL = "LOCAL"
    CLUSTER = "CLUSTER"


class GeometryType(str, Enum):
    LINE = "LINE"
    RECTANGLE = "RECTANGLE"
    CURVE = "CURVE"
    SURFACE = "SURFACE"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
