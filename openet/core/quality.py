"""Observation quality metrics for OpenET temporal interpolation.

Functions for computing per-pixel temporal distance to the nearest valid
Landsat observation.  These provide information for a quality/uncertainty
indicator for interpolated monthly products: a low value means the monthly
value is well supported by observations, a high value means it relies more
on interpolation across gaps.
"""
import calendar
import logging

import ee

logger = logging.getLogger(__name__)

# Milliseconds in one day — used for unit conversion
_MS_PER_DAY = 86400000


def calculate_monthly_distance(
        scene_coll,
        year,
        month,
        band_name='et',
        max_days=32,
        day_step=1,
):
    """Compute mean per-pixel temporal distance to the nearest observation.

    For each sampled day in the target month, computes the minimum distance
    (in days) to the nearest valid Landsat observation within the window
    from ``max_days`` before the first of the month to ``max_days`` after
    the end of the month.  Returns the mean of those daily minimum distances
    as a single-band image.

    Parameters
    ----------
    scene_coll : ee.ImageCollection
        Pre-filtered collection of Landsat scenes.  Each image must have a
        ``system:time_start`` property and at least one band whose mask
        indicates valid pixels.  This should be the same filtered collection
        used for interpolation (same cloud filtering, skip list, etc.).
        Scene times are truncated to 0 UTC of the scene date.
    year : int
        Target year.
    month : int
        Target month (1-12).
    band_name : str, optional
        Name of the band to use for the valid-pixel mask (default ``'et'``).
        Only the mask of this band is used — the values are ignored.
    max_days : int, optional
        Number of days before/after the month to search for observations
        (default 32).  Should match the ``interp_days`` parameter used in
        interpolation so the band describes the same observations the
        interpolation can use.
    day_step : int, optional
        Sample every Nth day of the month, starting on the 1st (default 1,
        every day, which gives the exact monthly mean).  Larger values reduce
        computation but approximate the monthly mean from a subset of days.

    Returns
    -------
    ee.Image
        Single-band float image named ``'mean_distance'``: the mean daily
        minimum distance to the nearest valid observation, in days.
        0 means an observation on every sampled day.  Pixels with no valid
        observation anywhere in the window are masked.  Image properties
        ``system:index`` (YYYYMM), ``system:time_start``, ``year`` and
        ``month`` are set.

    Raises
    ------
    ValueError
        If ``day_step`` is less than 1.

    Notes
    -----
    This function is independent of the interpolated ET values — it only
    depends on the temporal distribution of valid scene pixels within the
    window around the target month.

    Preliminary cost and accuracy (SSEBop, MGRS tile 11U, 2018-2019,
    quality-only monthly exports at 120 m, cost in Earth Engine EECU relative
    to the standard 30 m ``et, count`` monthly export of the same months):

    - ``day_step=1``: +5.9% EECU (mean monthly +5.3%, 95% CI 4.4-6.2%).
    - ``day_step=2``: +3.0% EECU (mean monthly +2.8%, 95% CI 2.3-3.3%),
      about half the ``day_step=1`` cost.  Compared with ``day_step=1`` the
      per-pixel error had a mean absolute value of 0.12 days (RMSE 0.18 days,
      about 1% of the mean value of 11 days) and never exceeded 0.5 days.
      Errors are largest in February and 30-day months, where every-other-day
      sampling is not centered in the month.
    - Exporting the band at 30 m instead of 120 m (``day_step=2``) cost about
      +44% EECU, so a coarser quality grid is recommended.

    These results are from one tile and should be treated as guidance only.
    """
    if day_step < 1:
        raise ValueError('day_step must be at least 1')

    days_in_month = calendar.monthrange(year, month)[1]

    month_start = ee.Date.fromYMD(year, month, 1)
    month_end = month_start.advance(1, 'month')

    # Expand the window by max_days to capture observations before/after month
    window_start = month_start.advance(-max_days, 'day')
    window_end = month_end.advance(max_days, 'day')

    # Filter the scene collection to the expanded window
    window_coll = scene_coll.filterDate(window_start, window_end)

    # Stamp each scene ONCE with its 0-UTC time as a band value (in millis).
    # This avoids recomputing per-scene metadata inside the daily loop.
    def _stamp_time(image):
        date = ee.Date(image.get('system:time_start'))
        date_0utc = ee.Date.fromYMD(
            date.get('year'), date.get('month'), date.get('day')
        )
        time_millis = date_0utc.millis()
        # Constant image with the scene's timestamp, masked to valid pixels
        mask = image.select([band_name]).mask()
        return (
            ee.Image.constant(time_millis)
            .toFloat()
            .rename('obs_time')
            .updateMask(mask)
            .set('system:time_start', time_millis)
        )

    # This collection is mapped ONCE — not once per day
    stamped_coll = window_coll.map(_stamp_time)

    # For each day in the month, compute the per-pixel minimum distance.
    # The key optimisation: for each day we only create ONE constant image
    # for the target date, subtract the pre-stamped obs_time band, take
    # abs, divide, and reduce with .min().  The per-scene loop is handled
    # implicitly by ee.ImageCollection.map + .min(), which EE can
    # parallelise efficiently.
    day_offsets = ee.List.sequence(0, days_in_month - 1, day_step)

    def _daily_min_distance(day_offset):
        day_offset = ee.Number(day_offset)
        target_millis = month_start.advance(day_offset, 'day').millis()

        def _pixel_distance(obs_img):
            return (
                obs_img.subtract(target_millis)
                .abs()
                .divide(_MS_PER_DAY)
                .rename('distance')
            )

        return stamped_coll.map(_pixel_distance).min().rename('min_distance')

    daily_images = ee.ImageCollection.fromImages(
        day_offsets.map(_daily_min_distance)
    )

    mean_distance = daily_images.mean().rename('mean_distance')

    return mean_distance.set({
        'system:index': ee.Date.fromYMD(year, month, 1).format('YYYYMM'),
        'system:time_start': ee.Date.fromYMD(year, month, 1).millis(),
        'year': year,
        'month': month,
    })
