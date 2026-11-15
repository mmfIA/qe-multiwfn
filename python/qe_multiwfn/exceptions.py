"""
qe_multiwfn.exceptions — Python exceptions for C ABI status codes.

Each QE_ERROR_* code returned by the C ABI is mapped to a Python exception
class. The mapping is performed by native._check_status() before the
exception is raised, so callers can `except` specific cases.
"""

class QeError(Exception):
    """Base class for all QE-Multiwfn errors."""
    def __init__(self, code: int, message: str, routine: str = ""):
        super().__init__(f"[code={code}] {routine}: {message}")
        self.code = code
        self.message = message
        self.routine = routine


class QeInvalidArgument(QeError): pass        # 1
class QeInvalidState(QeError): pass             # 2
class QeInvalidDimension(QeError): pass        # 3
class QeNullPointer(QeError): pass              # 4
class QeAllocation(QeError): pass               # 5
class QeIncompleteState(QeError): pass          # 6
class QeUnsupported(QeError): pass              # 7
class QeCalculation(QeError): pass              # 8
class QeInternal(QeError): pass                 # 9
class QeCompatibility(QeError): pass            # 10
class QeMemoryLayout(QeError): pass            # 11
class QeNotAvailable(QeError): pass             # 12


# Map C status codes to Python exception classes.
STATUS_TO_EXCEPTION = {
    0:  None,  # success
    1:  QeInvalidArgument,
    2:  QeInvalidState,
    3:  QeInvalidDimension,
    4:  QeNullPointer,
    5:  QeAllocation,
    6:  QeIncompleteState,
    7:  QeUnsupported,
    8:  QeCalculation,
    9:  QeInternal,
    10: QeCompatibility,
    11: QeMemoryLayout,
    12: QeNotAvailable,
}

STATUS_NAMES = {
    0:  "QE_SUCCESS",
    1:  "QE_ERROR_INVALID_ARGUMENT",
    2:  "QE_ERROR_INVALID_STATE",
    3:  "QE_ERROR_INVALID_DIMENSION",
    4:  "QE_ERROR_NULL_POINTER",
    5:  "QE_ERROR_ALLOCATION",
    6:  "QE_ERROR_INCOMPLETE_STATE",
    7:  "QE_ERROR_UNSUPPORTED",
    8:  "QE_ERROR_CALCULATION",
    9:  "QE_ERROR_INTERNAL",
    10: "QE_ERROR_COMPATIBILITY",
    11: "QE_ERROR_MEMORY_LAYOUT",
    12: "QE_ERROR_NOT_AVAILABLE",
}
