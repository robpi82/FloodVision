"""Bridge from Python logging into the GUI log console.

Log records originate in *any* thread (the batch worker included), but Qt
widgets may only be touched from the GUI thread. The handler therefore
never writes to a widget itself: it emits a Qt *signal*, and Qt's queued
cross-thread delivery hands the formatted line to the GUI thread, where a
slot appends it to the console. This signal/slot hop is the canonical,
race-free pattern for thread-safe GUI logging.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal


class QtLogHandler(QObject, logging.Handler):
    """A ``logging.Handler`` that forwards records as a Qt signal.

    Inherits from both ``QObject`` (to own a signal) and
    ``logging.Handler`` (to plug into the logging tree); both bases are
    initialised explicitly because multiple inheritance with non-cooperative
    ``__init__`` chains must not rely on ``super()`` alone here.
    """

    message_emitted = Signal(str)

    def __init__(self, level: int = logging.INFO) -> None:
        """Initialise both base classes and set the display format.

        Args:
            level: Minimum level forwarded to the GUI console.
        """
        QObject.__init__(self)
        logging.Handler.__init__(self, level=level)
        self.setFormatter(logging.Formatter("%(levelname)-8s | %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        """Format the record and hand it to the GUI thread via signal.

        Args:
            record: The log record to forward.
        """
        self.message_emitted.emit(self.format(record))
