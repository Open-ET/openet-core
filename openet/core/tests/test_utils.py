import datetime

import ee
# import pytest

import openet.core.utils as utils


def test_ee_init():
    assert ee.Number(1).getInfo() == 1


def test_constant_image_value(tol=0.000001):
    expected = 10.123456789
    input_img = ee.Image.constant(expected)
    output = utils.constant_image_value(input_img)
    assert abs(output - expected) <= tol


def test_constant_image_value_multiband(tol=0.000001):
    expected = 10.123456789
    input_img = ee.Image.constant([expected, expected + 1])
    output = utils.constant_image_value(input_img)
    assert abs(output[0] - expected) <= tol
    assert abs(output[1] - (expected + 1)) <= tol


# This could probably be parameterized with the previous function
def test_constant_image_value_multiband_band_names(tol=0.000001):
    expected = 10.123456789
    input_img = ee.Image.constant([expected, expected + 1])
    output = utils.constant_image_value(input_img, bands=['foo', 'bar'])
    assert abs(output[0] - expected) <= tol
    assert abs(output[1] - (expected + 1)) <= tol


def test_point_image_value(tol=0.001):
    expected = 2364.351
    output = utils.point_image_value(ee.Image('USGS/NED'), [-106.03249, 37.17777])
    assert abs(output - expected) <= tol


def test_millis():
    assert utils.millis(datetime.datetime(2015, 7, 13)) == 1436745600000
