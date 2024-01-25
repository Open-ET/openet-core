# import pprint

import ee
import pytest

import openet.core.common as common
import openet.core.utils as utils


# def test_ee_init():
#     assert ee.Number(1).getInfo() == 1
#
#
# @pytest.mark.parametrize(
#     "img_value, expected",
#     [
#
#         ['0000000000000000', 1],  # Designated Fill
#         ['0000000000000001', 1],
#         ['0000000000000010', 1],  # Terrain Occlusion
#         ['0000000000000010', 1],  # Radiometric Saturation
#         ['0000000000000010', 1],
#         ['0000000000000010', 1],
#         ['0000000000010000', 1],  # Cloud
#         ['0000000000110000', 1],  # Cloud Confidence
#         ['0000000001010000', 0],
#         ['0000000001110000', 0],
#         ['0000000010000000', 1],  # Cloud Shadow Confidence
#         ['0000000100000000', 1],
#         ['0000000110000000', 0],
#         ['0000011000000000', 1],  # Snow/Ice Confidence
#         ['0001100000000000', 1],  # Cirrus Confidence (don't mask on cirrus )
#     ]
# )
# def test_landsat_c1_toa_cloud_mask(img_value, expected):
#     input_img = ee.Image.constant(int(img_value, 2)).rename(['BQA'])
#     output_img = common.landsat_c1_toa_cloud_mask(input_img)
#     assert utils.constant_image_value(ee.Image(output_img))['BQA'] == expected
#
#
# @pytest.mark.parametrize(
#     "img_value, snow, expected",
#     [
#         # Snow/Ice Confidence
#         ['0000011000000000', None, 1],
#         ['0000011000000000', False, 1],
#         ['0000001000000000', True, 1],
#         ['0000010000000000', True, 1],
#         ['0000011000000000', True, 0],
#     ]
# )
# def test_landsat_c1_toa_cloud_mask_snow(img_value, snow, expected):
#     input_img = ee.Image.constant(int(img_value, 2)).rename(['BQA'])
#     input_args = {'input_img': input_img}
#     if snow is not None:
#         input_args['snow_flag'] = snow
#     output_img = common.landsat_c1_toa_cloud_mask(**input_args)
#     assert utils.constant_image_value(ee.Image(output_img))['BQA'] == expected
#
#
# @pytest.mark.parametrize(
#     "img_value, cirrus, expected",
#     [
#         # Cirrus Confidence (don't mask on cirrus for now)
#         ['0001100000000000', None, 1],
#         ['0001100000000000', False, 1],
#         ['0000100000000000', True, 1],
#         ['0001000000000000', True, 1],
#         ['0001100000000000', True, 0],
#     ]
# )
# def test_landsat_c1_toa_cloud_mask_cirrus(img_value, cirrus, expected):
#     input_img = ee.Image.constant(int(img_value, 2)).rename(['BQA'])
#     input_args = {'input_img': input_img}
#     if cirrus is not None:
#         input_args['cirrus_flag'] = cirrus
#     output_img = common.landsat_c1_toa_cloud_mask(**input_args)
#     assert utils.constant_image_value(ee.Image(output_img))['BQA'] == expected
#
#
# @pytest.mark.parametrize(
#     "img_value, expected",
#     [
#
#         ['0000000000000000', 1],  # Designated Fill
#         ['0000000000000001', 1],
#         ['0000000000000010', 1],  # Clear
#         ['0000000000000100', 1],  # Water
#         ['0000000000001000', 0],  # Cloud Shadow
#         ['0000000000010000', 1],  # Snow
#         ['0000000000100000', 1],  # Cloud
#         ['0000000001100000', 1],  # Cloud Confidence
#         ['0000000010100000', 1],
#         ['0000000011100000', 0],
#     ]
# )
# def test_landsat_c1_sr_cloud_mask(img_value, expected):
#     input_img = ee.Image.constant(int(img_value, 2)).rename(['pixel_qa'])
#     output_img = common.landsat_c1_sr_cloud_mask(input_img)
#     assert utils.constant_image_value(output_img)['pixel_qa'] == expected
#
#
# @pytest.mark.parametrize(
#     "img_value, arg_name, flag_value, expected",
#     [
#         # Shadows
#         ['0000000000001000', 'shadow_flag', None, 0],
#         ['0000000000001000', 'shadow_flag', False, 1],
#         ['0000000000001000', 'shadow_flag', True, 0],
#         # Snow
#         ['0000000000010000', 'snow_flag', None, 1],
#         ['0000000000010000', 'snow_flag', False, 1],
#         ['0000000000010000', 'snow_flag', True, 0],
#     ]
# )
# def test_landsat_c1_sr_cloud_mask_flags(img_value, arg_name, flag_value, expected):
#     input_img = ee.Image.constant(int(img_value, 2)).rename(['pixel_qa'])
#     input_args = {'input_img': input_img}
#     if flag_value is not None:
#         input_args[arg_name] = flag_value
#     output_img = common.landsat_c1_sr_cloud_mask(**input_args)
#     assert utils.constant_image_value(output_img)['pixel_qa'] == expected
#
#
# @pytest.mark.parametrize(
#     "qa_pixel, expected",
#     [
#
#         ['0000000000000000', 1],  # Designated Fill
#         ['0000000000000001', 1],
#         ['0000000000000010', 1],  # Dilated Cloud
#         ['0000000000000100', 1],  # Cirrus
#         ['0000000000001000', 0],  # Cloud
#         ['0000000000010000', 0],  # Cloud Shadow
#         ['0000000000100000', 1],  # Snow
#         ['0000000001000000', 1],  # Clear
#         ['0000000010000000', 1],  # Water
#         # Check that any saturated bits are masked
#         # ['0000000000100000', 0, 0],  # Snow
#         # Not using the confidence bands to set cloud masking yet
#         # ['0000000100000000', 0],  # Cloud Confidence
#         # ['0000001000000000', 0],
#         # ['0000001100000000', 0],
#         # ['0000010000000000', 0],  # Cloud Shadow Confidence
#         # ['0000100000000000', 0],
#         # ['0000110000000000', 0],
#         # ['0001000000000000', 0],  # Snow/Ice Confidence
#         # ['0010000000000000', 0],
#         # ['0011000000000000', 0],
#         # ['0100000000000000', 0],  # Cirrus Confidence
#         # ['1000000000000000', 0],
#         # ['1100000000000000', 0],
#
#
#     ]
# )
# def test_landsat_c2_sr_cloud_mask(qa_pixel, expected):
#     input_img = ee.Image.constant([int(qa_pixel, 2)]).rename(['QA_PIXEL'])
#     output_img = common.landsat_c2_sr_cloud_mask(input_img)
#     assert utils.constant_image_value(output_img)['cloud_mask'] == expected
#
#
# @pytest.mark.parametrize(
#     "img_value, arg_name, flag_value, expected",
#     [
#         # The "none" flag_value should test the default condition
#         # Dilated clouds
#         ['0000000000000010', 'dilate_flag', None, 1],
#         ['0000000000000010', 'dilate_flag', False, 1],
#         ['0000000000000010', 'dilate_flag', True, 0],
#         # Cirrus clouds
#         ['0000000000000100', 'cirrus_flag', None, 1],
#         ['0000000000000100', 'cirrus_flag', False, 1],
#         ['0000000000000100', 'cirrus_flag', True, 0],
#         # Shadows
#         ['0000000000010000', 'shadow_flag', None, 0],
#         ['0000000000010000', 'shadow_flag', False, 1],
#         ['0000000000010000', 'shadow_flag', True, 0],
#         # Snow
#         ['0000000000100000', 'snow_flag', None, 1],
#         ['0000000000100000', 'snow_flag', False, 1],
#         ['0000000000100000', 'snow_flag', True, 0],
#     ]
# )
# def test_landsat_c2_sr_cloud_mask_flags(img_value, arg_name, flag_value, expected):
#     input_img = ee.Image.constant([int(img_value, 2)]).rename(['QA_PIXEL'])
#     input_args = {'input_img': input_img}
#     if flag_value is not None:
#         input_args[arg_name] = flag_value
#     output_img = common.landsat_c2_sr_cloud_mask(**input_args)
#     assert utils.constant_image_value(output_img)['cloud_mask'] == expected


@pytest.mark.parametrize(
    "qa_pixel, qa_radsat, arg_name, flag_value, expected",
    [
        # The cloud mask is 1 for "clear" pixels and 0 for cloud/snow/sat pixels
        # The "none" flag_value should test the default condition
        # Using a "snowy" QA_PIXEL bit mask that should be unmasked by default
        ['0000000000100000', '0000', 'saturated_flag', False, 1],
        ['0000000000100000', '0000', 'saturated_flag', True, 1],
        ['0000000000100000', '0000', 'saturated_flag', None, 1],
        ['0000000000100000', '1110', 'saturated_flag', False, 1],
        ['0000000000100000', '1110', 'saturated_flag', True, 0],
        ['0000000000100000', '1110', 'saturated_flag', None, 1],
    ]
)
def test_landsat_c2_sr_saturated_flag(qa_pixel, qa_radsat, arg_name, flag_value, expected):
    input_img = (
        ee.Image.constant([int(qa_pixel, 2), int(qa_radsat, 2)])
        .rename(['QA_PIXEL', 'QA_RADSAT'])
        .set({'SPACECRAFT_ID': 'LANDSAT_8'})
    )
    input_args = {'input_img': input_img}
    if flag_value is not None:
        input_args[arg_name] = flag_value
    output_img = common.landsat_c2_sr_cloud_mask(**input_args)
    assert utils.constant_image_value(output_img)['cloud_mask'] == expected


# @pytest.mark.parametrize(
#     "img_value, expected",
#     [
#         ['0000000000000000', 1],
#         ['0000010000000000', 0],
#         ['0000100000000000', 0],
#     ]
# )
# def test_sentinel2_toa_cloud_mask(img_value, expected):
#     input_img = ee.Image.constant(int(img_value, 2)).rename(['QA60'])
#     output_img = common.sentinel2_toa_cloud_mask(input_img)
#     assert utils.constant_image_value(ee.Image(output_img))['QA60'] == expected
#
#
# @pytest.mark.parametrize(
#     "img_value, expected",
#     [
#         ['0000000000000000', 1],
#         ['0000010000000000', 0],
#         ['0000100000000000', 0],
#     ]
# )
# def test_sentinel2_sr_cloud_mask(img_value, expected):
#     input_img = ee.Image.constant(int(img_value, 2)).rename(['QA60'])
#     output_img = common.sentinel2_sr_cloud_mask(input_img)
#     assert utils.constant_image_value(ee.Image(output_img))['QA60'] == expected
#
#
# # def test_sentinel2_toa_cloud_mask_deprecation():
# #     """Test that sentinel2_toa_cloud_mask returns a deprecation warning"""
# #     with pytest.deprecated_call():
# #         input_img = ee.Image.constant(int('0000010000000000', 2)).rename(['QA60'])
# #         output_img = common.sentinel2_toa_cloud_mask(input_img)
# #         assert utils.constant_image_value(ee.Image(output_img))['QA60'] == 0
#
#
# def test_landsat_c2_sr_lst_correct():
#     # Basic function test with default inputs
#     sr_img = ee.Image('LANDSAT/LC08/C02/T1_L2/LC08_030036_20210725')
#     ndvi_img = sr_img.multiply(0.0000275).add(-0.2).normalizedDifference(['SR_B5', 'SR_B4'])
#     output_img = common.landsat_c2_sr_lst_correct(sr_img, ndvi_img)
#     output = utils.get_info(output_img)
#     assert output['bands'][0]['id'] == 'surface_temperature'
#
#
# def test_landsat_c2_sr_lst_parameter_keywords():
#     # Check that the function parameter keywords all work
#     sr_img = ee.Image('LANDSAT/LC08/C02/T1_L2/LC08_030036_20210725')
#     ndvi_img = sr_img.multiply(0.0000275).add(-0.2).normalizedDifference(['SR_B5', 'SR_B4'])
#     output_img = common.landsat_c2_sr_lst_correct(ndvi=ndvi_img, sr_image=sr_img)
#     output = utils.get_info(output_img)
#     assert output['bands'][0]['id'] == 'surface_temperature'
#
#
# # TODO: Consider reworking this test to compare the before and after value
# #   instead of testing the values themselves
# @pytest.mark.parametrize(
#     "image_id, xy, expected",
#     [
#         # First two points are in the same field but the second one is in an
#         # area of bad emissivity data and needs correction
#         ['LANDSAT/LC08/C02/T1_L2/LC08_030036_20210725', [-102.266679, 34.368470], 309.95],
#         ['LANDSAT/LC08/C02/T1_L2/LC08_030036_20210725', [-102.266754, 34.367682], 309.93],
#         # This point is just outside the field and should stay the same
#         ['LANDSAT/LC08/C02/T1_L2/LC08_030036_20210725', [-102.269769, 34.366115], 318.10],
#         # These two points are in the ASTER GED hole and have no L2 temperature
#         # The first his a high NDVI field, the second is a low NDVI field
#         ['LANDSAT/LC08/C02/T1_L2/LC08_031034_20160702', [-102.08284, 37.81728], 306.83],
#         ['LANDSAT/LC08/C02/T1_L2/LC08_031034_20160702', [-102.04696, 37.81796], 297.88],
#     ]
# )
# def test_landsat_c2_sr_lst_correct_values(image_id, xy, expected, tol=0.25):
#     input_img = ee.Image(image_id)
#     ndvi_img = input_img.multiply(0.0000275).add(-0.2).normalizedDifference(['SR_B5', 'SR_B4'])
#     # lst_img = input_img.select(['ST_B10']).multiply(0.00341802).add(149.0)
#     # original = utils.point_image_value(lst_img, xy, scale=30)['ST_B10']
#     output_img = common.landsat_c2_sr_lst_correct(input_img, ndvi_img)
#     corrected = utils.point_image_value(output_img, xy, scale=30)
#     assert abs(corrected['surface_temperature'] - expected) <= tol
