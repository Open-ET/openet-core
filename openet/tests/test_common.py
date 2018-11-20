import ee
import pytest

import openet.common as common
import openet.utils as utils


def test_ee_init():
    assert ee.Number(1).getInfo() == 1


@pytest.mark.parametrize(
    "img_value, expected",
    [
        # Designated Fill
        ['0000000000000000', 1],
        ['0000000000000001', 1],
        # Terrain Occlusion
        ['0000000000000010', 1],
        # Radiometric Saturation
        ['0000000000000010', 1],
        ['0000000000000010', 1],
        ['0000000000000010', 1],
        # Cloud
        ['0000000000010000', 1],
        # Cloud Confidence
        ['0000000000110000', 1],
        ['0000000001010000', 0],
        ['0000000001110000', 0],
        # Cloud Shadow Confidence
        ['0000000010000000', 1],
        ['0000000100000000', 1],
        ['0000000110000000', 0],
        # Snow/Ice Confidence
        ['0000001000000000', 1],
        ['0000010000000000', 1],
        ['0000011000000000', 0],
        # Cirrus Confidence (don't mask on cirrus for now)
        ['0000100000000000', 1],
        ['0001000000000000', 1],
        ['0001100000000000', 1],
    ]
)
def test_landsat_c1_toa_cloud_mask(img_value, expected):
    input_img = ee.Image.constant(int(img_value, 2)).rename(['BQA'])
    output_img = common.landsat_c1_toa_cloud_mask(input_img)
    assert utils.constant_image_value(ee.Image(output_img)) == expected


@pytest.mark.parametrize(
    "img_value, expected",
    [
        # Designated Fill
        ['0000000000000000', 1],
        ['0000000000000001', 1],
        # Clear
        ['0000000000000010', 1],
        # Water
        ['0000000000000100', 1],
        # Cloud Shadow
        ['0000000000001000', 0],
        # Snow
        ['0000000000010000', 0],
        # Cloud
        ['0000000000100000', 1],
        # Cloud Confidence
        ['0000000001100000', 1],
        ['0000000010100000', 0],
        ['0000000011100000', 0],
    ]
)
def test_landsat_c1_sr_cloud_mask(img_value, expected):
    input_img = ee.Image.constant(int(img_value, 2)).rename(['pixel_qa'])
    output_img = common.landsat_c1_sr_cloud_mask(input_img)
    assert utils.constant_image_value(ee.Image(output_img)) == expected


@pytest.mark.parametrize(
    "img_value, expected",
    [
        ['0000000000000000', 1],
        ['0000010000000000', 0],
        ['0000100000000000', 0],
    ]
)
def test_sentinel_2_toa_cloud_mask(img_value, expected):
    input_img = ee.Image.constant(int(img_value, 2)).rename(['QA60'])
    output_img = common.sentinel_2_toa_cloud_mask(input_img)
    assert utils.constant_image_value(ee.Image(output_img)) == expected
