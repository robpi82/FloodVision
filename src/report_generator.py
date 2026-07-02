"""Report generation for batch runs: CSV export and console summary.

Reporting is a separate concern from processing: the
:class:`~src.batch_processor.BatchProcessor` *produces* data, this module
*presents* it. Keeping them apart means new report formats (JSON, HTML,
PDF in later versions) are added here without ever touching the
processing code (Open/Closed principle).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src import config
from src.batch_processor import BatchResult, FloodComparisonResult

logger = logging.getLogger(__name__)

_SEPARATOR: str = "-" * 45


def save_report_csv(result: BatchResult, path: Path = config.REPORT_CSV_PATH) -> Path:
    """Write the per-image batch report as a CSV file.

    The DataFrame is built from :meth:`ImageProcessingRecord.to_dict`, so
    the CSV schema is defined in exactly one place -- next to the record
    itself -- and can never drift apart from it.

    Args:
        result: The finished batch result.
        path: Target CSV path. Defaults to the location in
            :mod:`src.config`.

    Returns:
        The path the report was written to.
    """
    frame = pd.DataFrame([record.to_dict() for record in result.records])
    path.parent.mkdir(parents=True, exist_ok=True)
    # index=False: the row number is meaningless data and would only add
    # an unnamed column that confuses spreadsheet users.
    frame.to_csv(path, index=False)
    logger.info("Batch report saved to %s (%d rows)", path, len(frame))
    return path


def build_summary(result: BatchResult) -> str:
    """Build the human-readable end-of-batch summary block.

    Returned as a string (instead of being logged directly) so callers
    decide the channel: ``main.py`` logs it, a future dashboard could
    display it, and tests can assert on it without capturing log output.

    Args:
        result: The finished batch result.

    Returns:
        A multi-line summary ready for logging.
    """
    lines = [
        _SEPARATOR,
        "FloodVision Change Detection Summary",
        _SEPARATOR,
        f"Image pairs processed : {len(result.records)}",
        f"Successful            : {len(result.successful)}",
        f"Failed                : {len(result.failed)}",
        f"Average water before  : {_format_percent(result.average_water_before_percent)}",
        f"Average water after   : {_format_percent(result.average_water_after_percent)}",
        f"Average net increase  : {_format_points(result.average_increase_percent)}",
        f"Largest net increase  : {_format_record(result.largest_increase_record)}",
        _SEPARATOR,
    ]
    return "\n".join(lines)


def _format_percent(value: float | None) -> str:
    """Format a percentage value, tolerating the all-failed edge case.

    Args:
        value: Percentage or ``None``.

    Returns:
        ``"18.4 %"`` style string, or ``"n/a"`` if no value exists.
    """
    return "n/a" if value is None else f"{value:.1f} %"


def _format_points(value: float | None) -> str:
    """Format a net change in percentage points, tolerating ``None``.

    Args:
        value: Change in percentage points or ``None``.

    Returns:
        ``"+13.4 pp"`` style string (signed), or ``"n/a"``.
    """
    return "n/a" if value is None else f"{value:+.1f} pp"


def _format_record(record: FloodComparisonResult | None) -> str:
    """Format the largest-increase record including its filename.

    Args:
        record: The record to format, or ``None``.

    Returns:
        ``"+18.2 pp (location01.png)"`` style string, or ``"n/a"``.
    """
    if record is None or record.increase_percent is None:
        return "n/a"
    return f"{record.increase_percent:+.1f} pp ({record.filename})"
