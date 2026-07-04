"""Bridge from Python logging into the GUI log console.

Log records originate in *any* thread (the batch worker included), but Qt
widgets may only be touched from the GUI thread. The handler therefore
never writes to a widget itself: it emits a Qt *signal* carrying the
formatted line **and its level**, and Qt's queued cross-thread delivery
hands both to the GUI thread, where the console slot renders the line in
the level's colour.

This module also registers the custom ``SUCCESS`` level (25, between
INFO and WARNING): standard logging has no positive-outcome level, but a
professional log console distinguishes "done" (green) from mere
information (neutral).
"""

from __future__ import annotations

import logging
from typing import Final

from PySide6.QtCore import QObject, Signal

#: Custom level for positive outcomes, rendered green in the console.
SUCCESS: Final[int] = 25
logging.addLevelName(SUCCESS, "SUCCESS")


class QtLogHandler(QObject, logging.Handler):
    """A ``logging.Handler`` that forwards records as a Qt signal.

    Inherits from both ``QObject`` (to own a signal) and
    ``logging.Handler`` (to plug into the logging tree); both bases are
    initialised explicitly because multiple inheritance with
    non-cooperative ``__init__`` chains must not rely on ``super()``
    alone here.
    """

    message_emitted = Signal(int, str)

    def __init__(self, level: int = logging.INFO) -> None:
        """Initialise both base classes and set the display format.

        Args:
            level: Minimum level forwarded to the GUI console.
        """
        QObject.__init__(self)
        logging.Handler.__init__(self, level=level)
        self.setFormatter(
            logging.Formatter(
                "%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S"
            )
        )

    def emit(self, record: logging.LogRecord) -> None:
        """Format the record and hand it to the GUI thread via signal.

        Args:
            record: The log record to forward.
        """
        self.message_emitted.emit(record.levelno, self.format(record))
