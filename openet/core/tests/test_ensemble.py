# import datetime
import logging
import pprint

import ee
import pytest

import openet.core.ensemble as ensemble
import openet.core.utils as utils

# logging.basicConfig(level=logging.DEBUG, format='%(message)s')


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
    ]
)
def test_mad(model_values, made_scale, expected, tol=0.001):
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

    output_img = ensemble.mad(ensemble_img=ee.Image(images),
                              made_scale=made_scale)
    output = utils.point_image_value(output_img, [-120, 39])['ensemble']
    assert abs(output - expected) <= tol


# TODO: Write a test to check that the output band is called ensemble
# def test_mad_bandname():
#     assert False


# TODO: Write a test to check if the MADe_scale factor works


# @pytest.mark.parametrize(
#     "model_values, crop_mask, made_scale, expected",
#     [
#         [[118, 111, 57, 75, 99, 58], 1, 2, 86.3333],
#         # CGM - Crop masking isn't currently used
#         [[118, 111, 57, 75, None, 58], 1, 2, 83.8],
#         [[118, 111, 57, 75, 0, 58], 0, 2, 69.8333],
#     ]
# )
# def test_mean(model_values, made_scale, crop_mask, expected, tol=0.0001):
#     # input_img = ee.Image.constant(int(img_value, 2)).rename(['BQA'])
#     # input_args = {'input_img': input_img}
#     images = []
#     for value in model_values:
#         if value is None:
#             images.append(ee.Image.constant(0).updateMask(0))
#         else:
#             images.append(ee.Image.constant(value))
#
#     output_img = ensemble.mean(
#         ensemble_img=images, crop_mask=ee.Image.constant(crop_mask))
#     output = utils.constant_image_value(output_img)['ensemble']
#     assert abs(output - expected) <= tol
