import ee
import pytest

import openet.core.common as common
import openet.core.utils as utils


def test_ee_init():
    assert ee.Number(1).getInfo() == 1


@pytest.mark.parametrize(
    "img_value, expected",
    [

        ['0000000000000000', 1],  # Designated Fill
        ['0000000000000001', 1],
        ['0000000000000010', 1],  # Terrain Occlusion
        ['0000000000000010', 1],  # Radiometric Saturation
        ['0000000000000010', 1],
        ['0000000000000010', 1],
        ['0000000000010000', 1],  # Cloud
        ['0000000000110000', 1],  # Cloud Confidence
        ['0000000001010000', 0],
        ['0000000001110000', 0],
        ['0000000010000000', 1],  # Cloud Shadow Confidence
        ['0000000100000000', 1],
        ['0000000110000000', 0],
        ['0000011000000000', 1],  # Snow/Ice Confidence
        ['0001100000000000', 1],  # Cirrus Confidence (don't mask on cirrus )
    ]
)
def test_landsat_c1_toa_cloud_mask(img_value, expected):
    input_img = ee.Image.constant(int(img_value, 2)).rename(['BQA'])
    output_img = common.landsat_c1_toa_cloud_mask(input_img)
    assert utils.constant_image_value(ee.Image(output_img))['BQA'] == expected


@pytest.mark.parametrize(
    "img_value, snow, expected",
    [
        # Snow/Ice Confidence
        ['0000011000000000', None, 1],
        ['0000011000000000', False, 1],
        ['0000001000000000', True, 1],
        ['0000010000000000', True, 1],
        ['0000011000000000', True, 0],
    ]
)
def test_landsat_c1_toa_cloud_mask_snow(img_value, snow, expected):
    input_img = ee.Image.constant(int(img_value, 2)).rename(['BQA'])
    input_args = {'input_img': input_img}
    if snow is not None:
        input_args['snow_flag'] = snow
    output_img = common.landsat_c1_toa_cloud_mask(**input_args)
    assert utils.constant_image_value(ee.Image(output_img))['BQA'] == expected


@pytest.mark.parametrize(
    "img_value, cirrus, expected",
    [
        # Cirrus Confidence (don't mask on cirrus for now)
        ['0001100000000000', None, 1],
        ['0001100000000000', False, 1],
        ['0000100000000000', True, 1],
        ['0001000000000000', True, 1],
        ['0001100000000000', True, 0],
    ]
)
def test_landsat_c1_toa_cloud_mask_cirrus(img_value, cirrus, expected):
    input_img = ee.Image.constant(int(img_value, 2)).rename(['BQA'])
    input_args = {'input_img': input_img}
    if cirrus is not None:
        input_args['cirrus_flag'] = cirrus
    output_img = common.landsat_c1_toa_cloud_mask(**input_args)
    assert utils.constant_image_value(ee.Image(output_img))['BQA'] == expected


@pytest.mark.parametrize(
    "img_value, expected",
    [

        ['0000000000000000', 1],  # Designated Fill
        ['0000000000000001', 1],
        ['0000000000000010', 1],  # Clear
        ['0000000000000100', 1],  # Water
        ['0000000000001000', 0],  # Cloud Shadow
        ['0000000000010000', 1],  # Snow
        ['0000000000100000', 1],  # Cloud
        ['0000000001100000', 1],  # Cloud Confidence
        ['0000000010100000', 1],
        ['0000000011100000', 0],
    ]
)
def test_landsat_c1_sr_cloud_mask(img_value, expected):
    input_img = ee.Image.constant(int(img_value, 2)).rename(['pixel_qa'])
    output_img = common.landsat_c1_sr_cloud_mask(input_img)
    assert utils.constant_image_value(output_img)['pixel_qa'] == expected


@pytest.mark.parametrize(
    "img_value, arg_name, flag_value, expected",
    [
        # Shadows
        ['0000000000001000', 'shadow_flag', None, 0],
        ['0000000000001000', 'shadow_flag', False, 1],
        ['0000000000001000', 'shadow_flag', True, 0],
        # Snow
        ['0000000000010000', 'snow_flag', None, 1],
        ['0000000000010000', 'snow_flag', False, 1],
        ['0000000000010000', 'snow_flag', True, 0],
    ]
)
def test_landsat_c1_sr_cloud_mask_flags(img_value, arg_name, flag_value, expected):
    input_img = ee.Image.constant(int(img_value, 2)).rename(['pixel_qa'])
    input_args = {'input_img': input_img}
    if flag_value is not None:
        input_args[arg_name] = flag_value
    output_img = common.landsat_c1_sr_cloud_mask(**input_args)
    assert utils.constant_image_value(output_img)['pixel_qa'] == expected


@pytest.mark.parametrize(
    "img_value, expected",
    [

        ['0000000000000000', 1],  # Designated Fill
        ['0000000000000001', 1],
        ['0000000000000010', 1],  # Dilated Cloud
        ['0000000000000100', 1],  # Cirrus
        ['0000000000001000', 0],  # Cloud
        ['0000000000010000', 0],  # Cloud Shadow
        ['0000000000100000', 1],  # Snow
        ['0000000001000000', 1],  # Clear
        ['0000000010000000', 1],  # Water
        # Not using the confidence bands to set cloud masking yet
        # ['0000000100000000', 0],  # Cloud Confidence
        # ['0000001000000000', 0],
        # ['0000001100000000', 0],
        # ['0000010000000000', 0],  # Cloud Shadow Confidence
        # ['0000100000000000', 0],
        # ['0000110000000000', 0],
        # ['0001000000000000', 0],  # Snow/Ice Confidence
        # ['0010000000000000', 0],
        # ['0011000000000000', 0],
        # ['0100000000000000', 0],  # Cirrus Confidence
        # ['1000000000000000', 0],
        # ['1100000000000000', 0],


    ]
)
def test_landsat_c2_sr_cloud_mask(img_value, expected):
    input_img = ee.Image.constant(int(img_value, 2)).rename(['QA_PIXEL'])
    output_img = common.landsat_c2_sr_cloud_mask(input_img)
    assert utils.constant_image_value(output_img)['QA_PIXEL'] == expected


@pytest.mark.parametrize(
    "img_value, arg_name, flag_value, expected",
    [
        # The "none" flag_value should test the default condition
        # Cirrus clouds
        ['0000000000000100', 'cirrus_flag', None, 1],
        ['0000000000000100', 'cirrus_flag', False, 1],
        ['0000000000000100', 'cirrus_flag', True, 0],
        # Dilated clouds
        ['0000000000000010', 'dilate_flag', None, 1],
        ['0000000000000010', 'dilate_flag', False, 1],
        ['0000000000000010', 'dilate_flag', True, 0],
        # Shadows
        ['0000000000010000', 'shadow_flag', None, 0],
        ['0000000000010000', 'shadow_flag', False, 1],
        ['0000000000010000', 'shadow_flag', True, 0],
        # Snow
        ['0000000000100000', 'snow_flag', None, 1],
        ['0000000000100000', 'snow_flag', False, 1],
        ['0000000000100000', 'snow_flag', True, 0],
    ]
)
def test_landsat_c2_sr_cloud_mask_flags(img_value, arg_name, flag_value, expected):
    input_img = ee.Image.constant(int(img_value, 2)).rename(['QA_PIXEL'])
    input_args = {'input_img': input_img}
    if flag_value is not None:
        input_args[arg_name] = flag_value
    output_img = common.landsat_c2_sr_cloud_mask(**input_args)
    assert utils.constant_image_value(output_img)['QA_PIXEL'] == expected


@pytest.mark.parametrize(
    "img_value, expected",
    [
        ['0000000000000000', 1],
        ['0000010000000000', 0],
        ['0000100000000000', 0],
    ]
)
def test_sentinel2_toa_cloud_mask(img_value, expected):
    input_img = ee.Image.constant(int(img_value, 2)).rename(['QA60'])
    output_img = common.sentinel2_toa_cloud_mask(input_img)
    assert utils.constant_image_value(ee.Image(output_img))['QA60'] == expected


@pytest.mark.parametrize(
    "img_value, expected",
    [
        ['0000000000000000', 1],
        ['0000010000000000', 0],
        ['0000100000000000', 0],
    ]
)
def test_sentinel2_sr_cloud_mask(img_value, expected):
    input_img = ee.Image.constant(int(img_value, 2)).rename(['QA60'])
    output_img = common.sentinel2_sr_cloud_mask(input_img)
    assert utils.constant_image_value(ee.Image(output_img))['QA60'] == expected


# def test_sentinel2_toa_cloud_mask_deprecation():
#     """Test that sentinel2_toa_cloud_mask returns a deprecation warning"""
#     with pytest.deprecated_call():
#         input_img = ee.Image.constant(int('0000010000000000', 2)).rename(['QA60'])
#         output_img = common.sentinel2_toa_cloud_mask(input_img)
#         assert utils.constant_image_value(ee.Image(output_img))['QA60'] == 0

