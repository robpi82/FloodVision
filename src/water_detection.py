"""Water detection from RGB images via classical HSV colour thresholding.

Pipeline implemented here (Version 0.2, no machine learning):

    RGB image -> Gaussian blur -> HSV conversion -> inRange threshold
              -> morphological cleanup (delegated to :mod:`src.mask_generator`)
              -> :class:`WaterDetectionResult`

Architecture note -- prepared for AI segmentation (Version 0.4+):
:class:`WaterSegmentationStrategy` defines the *contract* every detector
must fulfil (Strategy pattern via :class:`typing.Protocol`). ``main.py``
programs against this contract, so a future ``UNetSegmenter`` with the same
``detect()`` signature can replace :class:`HSVWaterDetector` without
touching any orchestration code (Open/Closed + Dependency Inversion).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

import cv2
import numpy as np
from PIL import Image

from src import config, mask_generator
from src.mask_generator import MaskArray, RGBImageArray

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HSVRange:
    """An inclusive lower/upper bound pair in OpenCV HSV space.

    OpenCV stores hue in ``[0, 179]`` (degrees halved to fit uint8) and
    saturation/value in ``[0, 255]``. The range is validated on creation so
    that a typo in the configuration fails immediately with a clear message
    instead of silently producing an empty mask.

    Attributes:
        lower: Inclusive lower bound ``(H, S, V)``.
        upper: Inclusive upper bound ``(H, S, V)``.
    """

    lower: tuple[int, int, int]
    upper: tuple[int, int, int]

    _MAXIMA: tuple[int, int, int] = (179, 255, 255)
    _CHANNELS: tuple[str, str, str] = ("H", "S", "V")

    def __post_init__(self) -> None:
        """Validate bounds channel by channel (fail fast).

        Raises:
            ValueError: If a bound leaves the OpenCV HSV value range or a
                lower bound exceeds its upper bound.
        """
        for name, low, high, maximum in zip(
            self._CHANNELS,
            self.lower,
            self.upper,
            self._MAXIMA,
        ):
            if not (0 <= low <= maximum and 0 <= high <= maximum):
                raise ValueError(
                    f"{name} bounds must lie in [0, {maximum}], "
                    f"got lower={low}, upper={high}."
                )

            if low > high:
                raise ValueError(
                    f"{name} lower bound {low} > upper bound {high}."
                )

    @property
    def lower_array(self) -> np.ndarray:
        """The lower bound as the uint8 array ``cv2.inRange`` expects."""
        return np.array(
            self.lower,
            dtype=np.uint8,
        )

    @property
    def upper_array(self) -> np.ndarray:
        """The upper bound as the uint8 array ``cv2.inRange`` expects."""
        return np.array(
            self.upper,
            dtype=np.uint8,
        )


@dataclass(frozen=True)
class WaterDetectionResult:
    """Immutable result bundle of one water-detection run.

    Attributes:
        image_rgb: The analysed image as an RGB uint8 array. It is the
            source for downstream visualization products such as overlays.
        raw_mask: Binary mask directly after thresholding and before
            morphological cleanup. It is retained for debugging and
            parameter tuning.
        mask: Final binary mask after optional cleanup
            (255 = water, 0 = non-water).
        water_coverage_percent: Share of valid pixels classified as water.
        valid_mask: Optional boolean mask identifying pixels that are valid
            for statistical evaluation. The mask must have the same spatial
            dimensions as ``mask``. ``None`` means all pixels are valid.
    """

    image_rgb: RGBImageArray
    raw_mask: MaskArray
    mask: MaskArray
    water_coverage_percent: float
    valid_mask: np.ndarray | None = None


class WaterSegmentationStrategy(Protocol):
    """Contract for every water segmentation implementation.

    Any object with a matching ``detect`` method satisfies this protocol
    through structural typing. This is the seam where a future AI-based
    segmenter can be integrated.
    """

    def detect(
        self,
        image: Image.Image,
    ) -> WaterDetectionResult:
        """Segment water in the given image.

        Args:
            image: Input image in any Pillow mode.

        Returns:
            The detection result bundle.
        """
        ...


class HSVWaterDetector:
    """Classical water detector based on HSV colour thresholding.

    All tuning parameters are injected via the constructor with defaults
    from :mod:`src.config`. Tests can therefore pass custom values without
    modifying global state.
    """

    def __init__(
        self,
        hsv_range: HSVRange | None = None,
        blur_kernel: tuple[int, int] = config.GAUSSIAN_BLUR_KERNEL,
        morph_kernel_size: int = config.MORPH_KERNEL_SIZE,
        open_iterations: int = config.MORPH_OPEN_ITERATIONS,
        close_iterations: int = config.MORPH_CLOSE_ITERATIONS,
    ) -> None:
        """Initialise the detector.

        Args:
            hsv_range: HSV window classified as water. Defaults to the
                thresholds defined in :mod:`src.config`.
            blur_kernel: Gaussian kernel size ``(width, height)``. Both
                values must be positive and odd.
            morph_kernel_size: Structuring-element diameter for cleanup.
            open_iterations: Opening iterations for speck removal.
            close_iterations: Closing iterations for hole filling.

        Raises:
            ValueError: If the blur-kernel dimensions are invalid.
        """
        if any(
            side < 1 or side % 2 == 0
            for side in blur_kernel
        ):
            raise ValueError(
                "Gaussian kernel sides must be positive odd ints, "
                f"got {blur_kernel}."
            )

        self._hsv_range = hsv_range or HSVRange(
            lower=config.WATER_HSV_LOWER,
            upper=config.WATER_HSV_UPPER,
        )
        self._blur_kernel = blur_kernel
        self._morph_kernel_size = morph_kernel_size
        self._open_iterations = open_iterations
        self._close_iterations = close_iterations

    def detect(
        self,
        image: Image.Image,
    ) -> WaterDetectionResult:
        """Run the full classical detection pipeline on one image.

        Steps:
            1. Convert the Pillow image to an RGB uint8 array.
            2. Apply Gaussian blur to suppress pixel noise.
            3. Convert RGB to HSV.
            4. Create the raw mask using ``cv2.inRange``.
            5. Clean the mask using morphological operations.

        Args:
            image: Input image in any Pillow mode.

        Returns:
            A detection result containing the RGB array, masks, coverage,
            and no explicit validity mask. For standard images, all pixels
            are considered valid.
        """
        rgb: RGBImageArray = np.asarray(
            image.convert("RGB"),
            dtype=np.uint8,
        )

        blurred = cv2.GaussianBlur(
            rgb,
            self._blur_kernel,
            0,
        )

        hsv = cv2.cvtColor(
            blurred,
            cv2.COLOR_RGB2HSV,
        )

        raw_mask: MaskArray = cv2.inRange(
            hsv,
            self._hsv_range.lower_array,
            self._hsv_range.upper_array,
        )

        mask = mask_generator.clean_mask(
            raw_mask,
            kernel_size=self._morph_kernel_size,
            open_iterations=self._open_iterations,
            close_iterations=self._close_iterations,
        )

        coverage = mask_generator.mask_coverage_percent(mask)

        logger.info(
            "Water detection finished: %.2f %% water coverage "
            "(HSV lower=%s, upper=%s)",
            coverage,
            self._hsv_range.lower,
            self._hsv_range.upper,
        )

        return WaterDetectionResult(
            image_rgb=rgb,
            raw_mask=raw_mask,
            mask=mask,
            water_coverage_percent=coverage,
            valid_mask=None,
        )