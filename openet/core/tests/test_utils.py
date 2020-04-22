import datetime

import ee
import pytest

import openet.core.utils as utils


def test_get_info():
    assert utils.get_info(ee.Number(1)) == 1


def test_constant_image_value(tol=0.000001):
    expected = 10.123456789
    input_img = ee.Image.constant(expected)
    output = utils.constant_image_value(input_img)
    assert abs(output['constant'] - expected) <= tol


def test_constant_image_value_band_name(tol=0.000001):
    """Test that a custom band name is carried through"""
    expected = 10.123456789
    input_img = ee.Image.constant(expected).rename('foo')
    output = utils.constant_image_value(input_img)
    assert abs(output['foo'] - expected) <= tol


def test_constant_image_value_multiband(tol=0.000001):
    """Test that a multiband image returns multiple values"""
    expected = 10.123456789
    input_img = ee.Image.constant([expected, expected + 1])
    output = utils.constant_image_value(input_img)
    assert abs(output['constant_0'] - expected) <= tol
    assert abs(output['constant_1'] - (expected + 1)) <= tol


def test_constant_image_value_multiband_bands(tol=0.000001):
    """Test that the band names are carried through on a multiband image"""
    expected = 10.123456789
    input_img = ee.Image.constant([expected, expected + 1])\
        .rename(['foo', 'bar'])
    output = utils.constant_image_value(input_img)
    assert abs(output['foo'] - expected) <= tol
    assert abs(output['bar'] - (expected + 1)) <= tol


def test_point_image_value(tol=0.001):
    expected = 2364.351
    output = utils.point_image_value(
        ee.Image('USGS/NED'), [-106.03249, 37.17777])
    assert abs(output['elevation'] - expected) <= tol


def test_point_coll_value(tol=0.001):
    expected = 2364.351
    output = utils.point_coll_value(
        ee.ImageCollection([ee.Image('USGS/NED')]), [-106.03249, 37.17777])
    assert abs(output['elevation']['2012-04-04'] - expected) <= tol


def test_millis():
    assert utils.millis(datetime.datetime(2015, 7, 13)) == 1436745600000


def test_date_0utc(date='2015-07-13'):
    assert utils.get_info(utils.date_0utc(
        ee.Date(date).advance(2, 'hour')).format('yyyy-MM-dd')) == date


@pytest.mark.parametrize(
    # Note: These are made up values
    'input, expected',
    [
        [300, True],
        ['300', True],
        [300.25, True],
        ['300.25', True],
        ['a', False],
    ]
)
def test_is_number(input, expected):
    assert utils.is_number(input) == expected
