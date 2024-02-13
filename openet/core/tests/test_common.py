# import pprint

import ee
import pytest

import openet.core.common as common
import openet.core.utils as utils


def test_ee_init():
    assert ee.Number(1).getInfo() == 1


@pytest.mark.parametrize(
    "qa_pixel, qa_radsat, input_args, expected",
    [
        # The cloud mask is 1 for "clear" pixels and 0 for cloud/snow/sat pixels
        # The "none" flag_value should test the default condition
        ['0000000000000000', '0000', {}, 1],  # Clear
        ['0000000000001000', '0000', {}, 0],  # Cloud
        # Dilated flag
        ['0000000000000010', '0000', {'dilate_flag': False}, 1],
        ['0000000000000010', '0000', {'dilate_flag': True}, 0],
        ['0000000000000010', '0000', {'dilate_flag': None}, 1],
        # Cirrus flag
        ['0000000000000100', '0000', {'cirrus_flag': False}, 1],
        ['0000000000000100', '0000', {'cirrus_flag': True}, 0],
        ['0000000000000100', '0000', {'cirrus_flag': None}, 1],
        # Shadow flag (default is True)
        ['0000000000010000', '0000', {'shadow_flag': False}, 1],
        ['0000000000010000', '0000', {'shadow_flag': True}, 0],
        ['0000000000010000', '0000', {'shadow_flag': None}, 0],
        # Snow flag
        ['0000000000100000', '0000', {'snow_flag': False}, 1],
        ['0000000000100000', '0000', {'snow_flag': True}, 0],
        ['0000000000100000', '0000', {'snow_flag': None}, 1],
        # Test the saturated flag
        # Using a "snowy" QA_PIXEL bit mask that should be unmasked by default
        ['0000000000100000', '0000', {'saturated_flag': False}, 1],
        ['0000000000100000', '0000', {'saturated_flag': True}, 1],
        ['0000000000100000', '0000', {'saturated_flag': None}, 1],
        ['0000000000100000', '1110', {'saturated_flag': False}, 1],
        ['0000000000100000', '1110', {'saturated_flag': True}, 0],
        ['0000000000100000', '1110', {'saturated_flag': None}, 1],
        # # Testing the cloud score here won't work since this test is assuming a constant image
        # # Added a separate test below but it should probably be reworked
        # ['0000000000100000', '0000', {'cloud_score_flag': True, 'cloud_score_pct': 100}, 1],
    ]
)
def test_landsat_c2_sr_cloud_mask(qa_pixel, qa_radsat, input_args, expected):
    # Remove input arguments that have a value of None to check defaults
    input_args = {k: v for k, v in input_args.items() if v is not None}
    input_img = (
        ee.Image.constant([int(qa_pixel, 2), int(qa_radsat, 2)])
        .rename(['QA_PIXEL', 'QA_RADSAT'])
        .set({'SPACECRAFT_ID': 'LANDSAT_8',
              'system:index': 'LC08_030036_20210725',
              'system:time_start': ee.Date('2021-07-25T17:20:21')})
    )
    input_args['input_img'] = input_img
    output_img = common.landsat_c2_sr_cloud_mask(**input_args)
    assert utils.constant_image_value(output_img)['cloud_mask'] == expected


# TODO: Rework this test to just check if a mask is returned since the
#   actual value testing is being checked in the landsat module function test
@pytest.mark.parametrize(
    "image_id, xy, cloud_score, expected",
    [
        ['LANDSAT/LT05/C02/T1_L2/LT05_042034_20091016', [-120.0, 37.0], 100, 0],
        # Pixel has a cloud score of 56, so mask if threshold is 50 but don't mask at 60
        ['LANDSAT/LT05/C02/T1_L2/LT05_042034_20091016', [-119.963613, 37.217444], 50, 0],
        ['LANDSAT/LT05/C02/T1_L2/LT05_042034_20091016', [-119.963613, 37.217444], 60, 1],
    ]
)
def test_landsat_c2_sr_cloud_mask_cloud_score(image_id, xy, cloud_score, expected):
    output_img = common.landsat_c2_sr_cloud_mask(
        input_img=ee.Image(image_id), cloud_score_flag=True, cloud_score_pct=cloud_score,
    )
    output = utils.point_image_value(output_img, xy, scale=30)
    assert output['cloud_mask'] == expected


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
    assert utils.constant_image_value(ee.Image(output_img))['cloud_mask'] == expected


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
    assert utils.constant_image_value(ee.Image(output_img))['cloud_mask'] == expected


# def test_sentinel2_toa_cloud_mask_deprecation():
#     """Test that sentinel2_toa_cloud_mask returns a deprecation warning"""
#     with pytest.deprecated_call():
#         input_img = ee.Image.constant(int('0000010000000000', 2)).rename(['QA60'])
#         output_img = common.sentinel2_toa_cloud_mask(input_img)
#         assert utils.constant_image_value(ee.Image(output_img))['QA60'] == 0


def test_landsat_c2_sr_lst_correct():
    # Basic function test with default inputs
    sr_img = ee.Image('LANDSAT/LC08/C02/T1_L2/LC08_030036_20210725')
    ndvi_img = sr_img.multiply(0.0000275).add(-0.2).normalizedDifference(['SR_B5', 'SR_B4'])
    output_img = common.landsat_c2_sr_lst_correct(sr_img, ndvi_img)
    output = utils.get_info(output_img)
    assert output['bands'][0]['id'] == 'surface_temperature'


def test_landsat_c2_sr_lst_parameter_keywords():
    # Check that the function parameter keywords all work
    sr_img = ee.Image('LANDSAT/LC08/C02/T1_L2/LC08_030036_20210725')
    ndvi_img = sr_img.multiply(0.0000275).add(-0.2).normalizedDifference(['SR_B5', 'SR_B4'])
    output_img = common.landsat_c2_sr_lst_correct(ndvi=ndvi_img, sr_image=sr_img)
    output = utils.get_info(output_img)
    assert output['bands'][0]['id'] == 'surface_temperature'


# TODO: Consider reworking this test to compare the before and after value
#   instead of testing the values themselves
@pytest.mark.parametrize(
    "image_id, xy, expected",
    [
        # First two points are in the same field but the second one is in an
        # area of bad emissivity data and needs correction
        ['LANDSAT/LC08/C02/T1_L2/LC08_030036_20210725', [-102.266679, 34.368470], 309.95],
        ['LANDSAT/LC08/C02/T1_L2/LC08_030036_20210725', [-102.266754, 34.367682], 309.93],
        # This point is just outside the field and should stay the same
        ['LANDSAT/LC08/C02/T1_L2/LC08_030036_20210725', [-102.269769, 34.366115], 318.10],
        # These two points are in the ASTER GED hole and have no L2 temperature
        # The first his a high NDVI field, the second is a low NDVI field
        ['LANDSAT/LC08/C02/T1_L2/LC08_031034_20160702', [-102.08284, 37.81728], 306.83],
        ['LANDSAT/LC08/C02/T1_L2/LC08_031034_20160702', [-102.04696, 37.81796], 297.88],
    ]
)
def test_landsat_c2_sr_lst_correct_values(image_id, xy, expected, tol=0.25):
    input_img = ee.Image(image_id)
    ndvi_img = input_img.multiply(0.0000275).add(-0.2).normalizedDifference(['SR_B5', 'SR_B4'])
    # lst_img = input_img.select(['ST_B10']).multiply(0.00341802).add(149.0)
    # original = utils.point_image_value(lst_img, xy, scale=30)['ST_B10']
    output_img = common.landsat_c2_sr_lst_correct(input_img, ndvi_img)
    corrected = utils.point_image_value(output_img, xy, scale=30)
    assert abs(corrected['surface_temperature'] - expected) <= tol
