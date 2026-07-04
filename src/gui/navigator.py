"""Navigation model over the successfully processed image pairs.

Pure state, no widgets: the navigator remembers which pairs produced
products and where those products live, and answers previous/next/current
queries. Keeping this out of :mod:`src.gui.main_window` gives the window
one collaborator to call instead of index arithmetic scattered through
slots -- and makes the navigation logic testable without Qt.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.batch_processor import FloodComparisonResult


@dataclass(frozen=True)
class PairEntry:
    """One navigable, successfully processed pair.

    Attributes:
        record: The backend result record of the pair.
        before_image: Original pre-event image path.
        after_image: Original post-event image path.
        overlay: Generated overlay product path.
        new_flood_mask: Generated red-on-black change product path.
    """

    record: FloodComparisonResult
    before_image: Path
    after_image: Path
    overlay: Path
    new_flood_mask: Path


class PairNavigator:
    """Ordered collection of :class:`PairEntry` with a current position."""

    def __init__(self) -> None:
        """Start empty with no current entry."""
        self._entries: list[PairEntry] = []
        self._index: int = -1

    def clear(self) -> None:
        """Remove all entries (called when a new batch starts)."""
        self._entries.clear()
        self._index = -1

    def add(self, entry: PairEntry) -> None:
        """Append a new entry and make it the current one (follow mode).

        Following the newest entry during processing gives the live
        preview; once the batch is done the user navigates freely.

        Args:
            entry: The entry to append.
        """
        self._entries.append(entry)
        self._index = len(self._entries) - 1

    def previous(self) -> PairEntry | None:
        """Step back one entry if possible.

        Returns:
            The new current entry, or ``None`` at the start of the list.
        """
        if self.has_previous:
            self._index -= 1
            return self.current
        return None

    def next(self) -> PairEntry | None:
        """Step forward one entry if possible.

        Returns:
            The new current entry, or ``None`` at the end of the list.
        """
        if self.has_next:
            self._index += 1
            return self.current
        return None

    @property
    def current(self) -> PairEntry | None:
        """The entry at the current position, or ``None`` if empty."""
        if 0 <= self._index < len(self._entries):
            return self._entries[self._index]
        return None

    @property
    def position(self) -> tuple[int, int]:
        """``(1-based current index, total)``; ``(0, 0)`` when empty."""
        if not self._entries:
            return (0, 0)
        return (self._index + 1, len(self._entries))

    @property
    def has_previous(self) -> bool:
        """Whether stepping back is possible."""
        return self._index > 0

    @property
    def has_next(self) -> bool:
        """Whether stepping forward is possible."""
        return self._index < len(self._entries) - 1
