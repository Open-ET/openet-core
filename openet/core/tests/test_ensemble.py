# import datetime
import logging
import pprint

import ee
import pytest

import openet.core.ensemble as ensemble
import openet.core.utils as utils

# logging.basicConfig(level=logging.DEBUG, format='%(message)s')


@pytest.mark.parametrize(
    "model_values, crop_mask, made_scale, expected",
    [
        [[118, 111, 57, 75, 99, 58], 1, 2, 86.3333],
        # CGM - Crop masking isn't currently used
        [[118, 111, 57, 75, None, 58], 1, 2, 83.8],
        [[118, 111, 57, 75, 0, 58], 0, 2, 69.8333],
    ]
)
def test_mean(model_values, made_scale, crop_mask, expected, tol=0.0001):
    # input_img = ee.Image.constant(int(img_value, 2)).rename(['BQA'])
    # input_args = {'input_img': input_img}
    images = []
    for value in model_values:
        if value is None:
            images.append(ee.Image.constant(0).updateMask(0))
        else:
            images.append(ee.Image.constant(value))

    output_img = ensemble.mean(
        images=images, crop_mask=ee.Image.constant(crop_mask))
    output = utils.constant_image_value(output_img)['ensemble']
    assert abs(output - expected) <= tol


@pytest.mark.parametrize(
    "model_values, crop_mask, made_scale, expected",
    [
        [[118, 111, 57, 75, 99, 58], 1, 2, 86.3333],
        # CGM - Checking if None values get handled as expected
        [[118, 111, 57, 75, None, 58], 1, 2, 83.8],
        [[118, 111, 57, 75, 0, 58], 1, 2, 69.83],
        # [[87, 55, 23, 25, 41, 12], 1, 2, 50],
    ]
)
def test_mad(model_values, made_scale, crop_mask, expected, tol=0.0001):
    # input_img = ee.Image.constant(int(img_value, 2)).rename(['BQA'])
    # input_args = {'input_img': input_img}
    images = []
    for value in model_values:
        if value is None:
            images.append(ee.Image.constant(0).updateMask(0))
        else:
            images.append(ee.Image.constant(value))

    output_img = ensemble.median_absolute_deviation(
        images=images, crop_mask=ee.Image.constant(crop_mask),
        made_scale=made_scale)
    output = utils.constant_image_value(output_img)['ensemble']
    assert abs(output - expected) <= tol



