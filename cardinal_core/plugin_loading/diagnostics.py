from pathlib import Path

from Utils.logging_support.constants import DETAILS_MESSAGE
from Utils.logging_support.formatters import clean_text, has_payload


def error_summary(error: BaseException) -> str:
    try:
        reason = clean_text(error)
    except Exception:
        reason = "<exception message unavailable>"
    if has_payload(reason):
        reason = DETAILS_MESSAGE
    summary = f"{type(error).__name__}: {reason}"
    filename, line = None, None
    if isinstance(error, SyntaxError):
        filename, line = error.filename, error.lineno
    elif error.__traceback__ is not None:
        frame = error.__traceback__
        while frame.tb_next is not None:
            frame = frame.tb_next
        filename, line = frame.tb_frame.f_code.co_filename, frame.tb_lineno
    if filename:
        path = Path(filename)
        try:
            path = path.resolve().relative_to(Path.cwd())
        except (OSError, ValueError):
            pass
        summary += f" ({path.as_posix()}:{line})"
    return summary
