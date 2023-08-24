# import datetime
# import logging
# import pprint

import ee
import pytest

import openet.core.ensemble as ensemble
import openet.core.utils as utils

# logging.basicConfig(level=logging.DEBUG, format='%(message)s')


# TODO: Write a test to check that the output bandnames
# def test_mad_bandname():
#     assert False


@pytest.mark.parametrize(
    "model_values, made_scale, expected",
    [
        [[118, 111, 57, 75, 99, 58], 2, 86.3333],
        # Check that None values get converted to masked values
        [[118, 111, 57, 75, None, 58], 2, 83.8],
        [[118, 111, 57, 75, 0, 58], 2, 69.8333],
        # Check the edges of the upper threshold
        [[87, 55, 23, 25, 41, 12], 2, 31.2],
        [[79, 71, 23, 25, 41, 12], 2, 34.4],
        [[78, 71, 23, 25, 41, 12], 2, 41.6667],
        [[77, 71, 23, 25, 40, 12], 2, 34.2],
        [[76, 71, 23, 25, 40, 12], 2, 41.1667],

        # Some real values that Thomas found
        # July 2020 37.36681547, -115.8973587
        [[0, 0, 1, 15, None, 0], 2, 0.25],
        # July 2020 36.62667211, -116.4601847
        [[0, 0, 13, 8, None, 0], 2, 2],
        # July 2020 37.82405775, -115.8266657
        [[0, 0, 0, 12, None, 0], 2, 0],
        # July 2020 -120.96178, 37.927754
        [[234, 248, 221, 198, 236, 266], 2, 233.8333],

        # Drop model values with SIMS included
        [[None, 71, 23, 25, 41, 12], 2, 25.25],
        [[None, None, 23, 25, 41, 12], 2, 25.25],
        [[None, None, None, 25, 41, 12], 2, 26],
        [[None, None, None, None, 41, 12], 2, 26.50],
        [[None, None, None, None, 41, None], 2, 41],
        # Drop model values with SIMS excluded
        [[None, 71, 23, 25, None, 12], 2, 32.75],
        [[None, None, 23, 25, None, 12], 2, 20],
        [[None, None, None, 25, None, 12], 2, 18.5],
        [[None, None, None, None, None, 12], 2, 12],

        # Test combinations of masking, zeros, and values
        [[None, None, None, None, None, 12], 2, 12],
        [[None, None, None, None, 0, 12], 2, 6],
        [[None, None, None, 0, 0, 12], 2, 4],
        [[None, None, 0, 0, 0, 12], 2, 3],
        [[None, 0, 0, 0, 0, 12], 2, 0],
        [[0, 0, 0, 0, 0, 12], 2, 0],
        [[None, None, None, None, 41, 12], 2, 26.5],
        [[None, None, None, 0, 41, 12], 2, 17.6667],
        [[None, None, 0, 0, 41, 12], 2, 13.25],
        [[None, 0, 0, 0, 41, 12], 2, 3],
        [[0, 0, 0, 0, 41, 12], 2, 0],
        [[None, None, None, 25, 41, 12], 2, 26],
        [[None, None, 0, 25, 41, 12], 2, 19.5],
        [[None, 0, 0, 25, 41, 12], 2, 15.6],
        [[0, 0, 0, 25, 41, 12], 2, 3],
        [[None, None, 23, 25, 41, 12], 2, 25.25],
        [[None, 0, 23, 25, 41, 12], 2, 20.2],
        [[0, 0, 23, 25, 41, 12], 2, 16.8333],
        [[None, 55, 23, 25, 41, 12], 2, 31.2],
        [[0, 55, 23, 25, 41, 12], 2, 26],
        # # Test various number of only zeros
        # [[None, None, None, None, None, None], 2, 0],
        # [[None, None, None, None, None, 0], 2, 0],
        # [[None, None, None, None, 0, 0], 2, 0],
        # [[None, None, None, 0, 0, 0], 2, 0],
        # [[None, None, 0, 0, 0, 0], 2, 0],
        # [[None, 0, 0, 0, 0, 0], 2, 0],
        # [[0, 0, 0, 0, 0, 0], 2, 0],

        #
        [[None, None, None, 0, 100, 12], 2, 37.3333],
        [[224, 231, 210, 194, 235, 242], 2, 228.4],

        # Check that the scale term does something
        # CGM - This might be better as a separate test function
        [[87, 55, 23, 25, 41, 12], 2.5, 40.5],

        # Check that dropping an image works (dropped SIMS None)
        [[118, 111, 57, 75, 58], 2, 83.8],
    ]
)
def test_mad_values(model_values, made_scale, expected, tol=0.001):
    print(model_values)
    # TODO: Check if using constant images is faster and works
    images = []
    mask_img = ee.Image('IDAHO_EPSCOR/GRIDMET/20200101')\
        .select(['tmmx']).multiply(0)
    for i, value in enumerate(model_values):
        if value is None:
            images.append(mask_img.updateMask(0).rename([f'B{i+1}']))
        else:
            images.append(mask_img.add(value).rename([f'B{i+1}']))

    output_img = ensemble.mad(ensemble_img=ee.Image(images), made_scale=made_scale)
    output = utils.point_image_value(output_img, [-120, 39])['ensemble_mad']
    assert abs(output - expected) <= tol


# TODO: Create separate tests for each of the other (non-mean) stats,
#   For now test all of them in one function
@pytest.mark.parametrize(
    "model_values, made_scale, mn, mx, count",
    [
        [[118, 111, 57, 75, 99, 58], 2, 57, 118, 6],
        [[87, 55, 23, 25, 41, 12], 2, 12, 55, 5],
        [[55, 23, 25, 41, None, 12], 2, 12, 55, 5],
        [[100, 23, 25, 41, None, 12], 2, 12, 41, 4],
        [[0, 0, 1, 15, None, 0], 2, 0, 1, 4],
        [[0, 0, 13, 8, None, 0], 2, 0, 8, 4],
        [[0, 0, 0, 12, None, 0], 2, 0, 0, 4],
    ]
)
def test_mad_other_stats(model_values, made_scale, mn, mx, count, tol=0.001):
    # print(model_values)
    images = []
    mask_img = ee.Image('IDAHO_EPSCOR/GRIDMET/20200101')\
        .select(['tmmx']).multiply(0)
    for i, value in enumerate(model_values):
        if value is None:
            images.append(mask_img.updateMask(0).rename([f'B{i+1}']))
        else:
            images.append(mask_img.add(value).rename([f'B{i+1}']))

    output_img = ensemble.mad(ensemble_img=ee.Image(images), made_scale=made_scale)
    output = utils.point_image_value(output_img, [-120, 39], scale=100)
    assert abs(output['ensemble_mad_min'] - mn) <= tol
    assert abs(output['ensemble_mad_max'] - mx) <= tol
    assert abs(output['ensemble_mad_count'] - count) <= tol


@pytest.mark.parametrize(
    "model_values, made_scale, index",
    [
        # Same test values as in stats test
        [{'disalexi': 118, 'eemetric': 111, 'geesebal': 57, 'ptjpl': 75,
          'sims': 99, 'ssebop': 58}, 2, 63],
        [{'disalexi': 87, 'eemetric': 55, 'geesebal': 23, 'ptjpl': 25,
          'sims': 41, 'ssebop': 12}, 2, 62],
        [{'disalexi': 55, 'eemetric': 23, 'geesebal': 25, 'ptjpl': 41,
          'sims': None, 'ssebop': 12}, 2, 47],
        [{'disalexi': 100, 'eemetric': 23, 'geesebal': 25, 'ptjpl': 41,
          'sims': None, 'ssebop': 12}, 2, 46],
        [{'disalexi': 0, 'eemetric': 0, 'geesebal': 1, 'ptjpl': 15,
          'sims': None, 'ssebop': 0}, 2, 39],
        [{'disalexi': 0, 'eemetric': 0, 'geesebal': 13, 'ptjpl': 8,
          'sims': None, 'ssebop': 0}, 2, 43],
        [{'disalexi': 0, 'eemetric': 0, 'geesebal': 0, 'ptjpl': 12,
          'sims': None, 'ssebop': 0}, 2, 39],
        # Check that 5 band image with SIMS totally excluded
        [{'disalexi': 55, 'eemetric': 23, 'geesebal': 25, 'ptjpl': 41,
          'ssebop': 12}, 2, 47],
        # Check that order doesn't matter
        [{'eemetric': 23, 'sims': None, 'ptjpl': 41, 'disalexi': 55,
          'geesebal': 25, 'ssebop': 12}, 2, 47],

    ]
)
def test_mad_index(model_values, made_scale, index):
    # print(model_values)
    images = []
    mask_img = ee.Image('IDAHO_EPSCOR/GRIDMET/20200101')\
        .select(['tmmx']).multiply(0)
    for name, value in model_values.items():
        if value is None:
            images.append(mask_img.updateMask(0).rename([name]))
        else:
            images.append(mask_img.add(value).rename([name]))

    output_img = ensemble.mad(ensemble_img=ee.Image(images), made_scale=made_scale)
    output = utils.point_image_value(output_img, [-120, 39], scale=100)
    assert output['ensemble_mad_index'] == index


@pytest.mark.parametrize(
    "model_values, expected",
    [
        [[118, 111, 57, 75, 99, 58], 86.3333],
        [[87, 55, 23, 25, 41, 12], 40.5],
        [[118, 111, 57, 75, None, 58], 83.8],
        [[118, 111, 57, 75, 0, 58], 69.8333],
    ]
)
def test_mean_values(model_values, expected, tol=0.0001):
    # input_img = ee.Image.constant(int(img_value, 2)).rename(['BQA'])
    # input_args = {'input_img': input_img}
    images = []
    for value in model_values:
        if value is None:
            images.append(ee.Image.constant(0).updateMask(0))
        else:
            images.append(ee.Image.constant(value))

    output_img = ensemble.mean(ensemble_img=ee.Image(images))
    output = utils.constant_image_value(output_img)['ensemble_sam']
    assert abs(output - expected) <= tol
