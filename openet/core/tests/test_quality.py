"""Tests for openet.core.quality module."""
import logging

import ee
import pytest

import openet.core.quality as quality
import openet.core.utils as utils

logging.basicConfig(level=logging.DEBUG, format='%(message)s')


def test_ee_init():
    assert ee.Number(1).getInfo() == 1


def _build_scene_coll(dates):
    """Build a synthetic scene collection with a single 'et' band.

    Parameters
    ----------
    dates : list of str
        ISO format date strings (e.g. ['2017-07-08', '2017-07-16']).
        Each date produces a fully-valid constant image.

    Returns
    -------
    ee.ImageCollection

    """
    images = []
    for d in dates:
        time = ee.Date(d).advance(18, 'hours').millis()
        img = (
            ee.Image.constant(1).double().rename('et')
            .set({
                'system:time_start': time,
                'system:index': ee.Date(d).format('yyyyMMdd'),
            })
        )
        images.append(img)
    return ee.ImageCollection.fromImages(images)


def _build_scene_coll_with_mask(date_mask_pairs):
    """Build a scene collection where some scenes can be masked.

    Parameters
    ----------
    date_mask_pairs : list of (str, bool)
        Each tuple is (date_string, is_valid). If is_valid is False,
        the image will be fully masked.

    Returns
    -------
    ee.ImageCollection

    """
    images = []
    for d, valid in date_mask_pairs:
        time = ee.Date(d).advance(18, 'hours').millis()
        img = ee.Image.constant(1).double().rename('et')
        if not valid:
            img = img.updateMask(0)
        img = img.set({
            'system:time_start': time,
            'system:index': ee.Date(d).format('yyyyMMdd'),
        })
        images.append(img)
    return ee.ImageCollection.fromImages(images)


class TestCalculateMonthlyDistance:
    """Tests for quality.calculate_monthly_distance."""

    def test_output_band_name(self):
        """Output image should have a single 'mean_distance' band."""
        coll = _build_scene_coll(['2017-07-08', '2017-07-16', '2017-07-24'])
        result = quality.calculate_monthly_distance(coll, 2017, 7, day_step=1)
        band_names = utils.get_info(result.bandNames())
        assert band_names == ['mean_distance']

    def test_single_mid_month_observation(self):
        """A single observation on July 16 in a 31-day month.

        For each day d in [1..31], min distance = |d - 16|.
        Distances: [15, 14, 13, ..., 1, 0, 1, ..., 15]
        Sum = 2 * (1+2+...+15) + 0 = 240
        Mean = 240 / 31 ≈ 7.742
        """
        coll = _build_scene_coll(['2017-07-16'])
        result = quality.calculate_monthly_distance(coll, 2017, 7, day_step=1)
        output = utils.constant_image_value(result)
        expected = 240.0 / 31.0
        assert abs(output['mean_distance'] - expected) <= 0.01

    def test_two_observations_symmetric(self):
        """Two observations on July 1 and July 31.

        For day offset d in [0..30], min distance = min(d, 30 - d).
        Distances: [0, 1, ..., 14, 15, 14, ..., 1, 0]
        Sum = 2 * (1+2+...+14) + 15 = 225
        Mean = 225 / 31 ≈ 7.258
        """
        coll = _build_scene_coll(['2017-07-01', '2017-07-31'])
        result = quality.calculate_monthly_distance(coll, 2017, 7, day_step=1)
        output = utils.constant_image_value(result)
        expected = 225.0 / 31.0
        assert abs(output['mean_distance'] - expected) <= 0.01

    def test_observation_every_8_days(self):
        """Observations on July 1, 9, 17, 25 (every 8 days).

        Max gap between consecutive observations within month is 8 days,
        so max daily min distance is 4 days. Mean should be relatively low.
        """
        coll = _build_scene_coll(['2017-07-01', '2017-07-09', '2017-07-17', '2017-07-25'])
        result = quality.calculate_monthly_distance(coll, 2017, 7)
        output = utils.constant_image_value(result)
        # With 8-day revisit, mean distance should be around 2-3 days
        assert 1.0 <= output['mean_distance'] <= 4.0

    def test_daily_observations(self):
        """An observation every day should produce mean_distance ≈ 0."""
        dates = [f'2017-07-{d:02d}' for d in range(1, 32)]
        coll = _build_scene_coll(dates)
        result = quality.calculate_monthly_distance(coll, 2017, 7)
        output = utils.constant_image_value(result)
        assert abs(output['mean_distance']) <= 0.01

    def test_observations_outside_month(self):
        """Observations only before and after the month.

        June 15 and August 15 — distances to July days are large but
        within the ±32 day window.
        """
        coll = _build_scene_coll(['2017-06-15', '2017-08-15'])
        result = quality.calculate_monthly_distance(coll, 2017, 7)
        output = utils.constant_image_value(result)
        # July 1 → min(16, 45) = 16; July 31 → min(46, 15) = 15
        # All days have relatively high mean distance
        assert output['mean_distance'] > 10.0

    def test_custom_band_name(self):
        """Should work with a custom band name."""
        images = []
        for d in ['2017-07-08', '2017-07-16', '2017-07-24']:
            time = ee.Date(d).advance(18, 'hours').millis()
            img = (
                ee.Image.constant(1).double().rename('ndvi')
                .set({'system:time_start': time,
                      'system:index': ee.Date(d).format('yyyyMMdd')})
            )
            images.append(img)
        coll = ee.ImageCollection.fromImages(images)
        result = quality.calculate_monthly_distance(coll, 2017, 7, band_name='ndvi')
        output = utils.constant_image_value(result)
        assert output['mean_distance'] is not None

    def test_february_non_leap(self):
        """February 2017 (28 days) — verify correct day count."""
        coll = _build_scene_coll(['2017-02-14'])
        result = quality.calculate_monthly_distance(coll, 2017, 2, day_step=1)
        output = utils.constant_image_value(result)
        # Single obs on day 14 (offset 13): distances [13,12,...,0,...,14]
        # Sum = (0+1+...+13) + (1+2+...+14) = 91 + 105 = 196
        expected = 196.0 / 28.0
        assert abs(output['mean_distance'] - expected) <= 0.01

    def test_system_properties(self):
        """Output image should have system:time_start and system:index set."""
        coll = _build_scene_coll(['2017-07-16'])
        result = quality.calculate_monthly_distance(coll, 2017, 7, day_step=1)
        info = utils.get_info(result)
        props = info['properties']
        assert props['system:index'] == '201707'
        assert props['year'] == 2017
        assert props['month'] == 7

    def test_masked_scenes_ignored(self):
        """Fully masked scenes should not contribute to distance calculation."""
        # Only the July 16 scene is valid; the others are masked
        coll = _build_scene_coll_with_mask([
            ('2017-07-08', False),
            ('2017-07-16', True),
            ('2017-07-24', False),
        ])
        result = quality.calculate_monthly_distance(coll, 2017, 7, day_step=1)
        output = utils.constant_image_value(result)
        # Same as single mid-month observation
        expected = 240.0 / 31.0
        assert abs(output['mean_distance'] - expected) <= 0.01

    def test_day_step(self):
        """day_step=2 should produce a close approximation to day_step=1."""
        coll = _build_scene_coll(['2017-07-08', '2017-07-16', '2017-07-24'])
        result_1 = quality.calculate_monthly_distance(coll, 2017, 7, day_step=1)
        result_2 = quality.calculate_monthly_distance(coll, 2017, 7, day_step=2)
        val_1 = utils.constant_image_value(result_1)['mean_distance']
        val_2 = utils.constant_image_value(result_2)['mean_distance']
        # With 8-day spacing the max error from skipping a day is ~0.5
        assert abs(val_1 - val_2) <= 0.5

    def test_day_step_must_be_positive(self):
        coll = _build_scene_coll(['2017-07-16'])
        with pytest.raises(ValueError):
            quality.calculate_monthly_distance(coll, 2017, 7, day_step=0)
