import ee
import pytest

import openet.core.landsat as landsat
import openet.core.utils as utils


# TODO: Add additional tests and/or rebuild these as a constant image test
def test_c02_l2_sr_band_names():
    input_img = ee.Image('LANDSAT/LT05/C02/T1_L2/LT05_042034_20091016')
    output = utils.get_info(landsat.c02_l2_sr(input_img).bandNames())
    assert output == ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'lst', 'QA_PIXEL', 'QA_RADSAT']


def test_c02_sr_ndi_band_name():
    # Check that the NDI function works and returns a properly named output
    input_img = ee.Image('LANDSAT/LT05/C02/T1_L2/LT05_042034_20091016')
    sr_img = landsat.c02_l2_sr(input_img).select(['green', 'nir'])
    output = utils.get_info(landsat.c02_sr_ndi(sr_img, 'green', 'nir').bandNames())
    assert output == ['ndi']


@pytest.mark.parametrize(
    'red, nir, expected',
    [
        [0.02, 0.9 / 55, -0.1],
        [0.02, 0.02,  0.0],
        [0.01, 0.11 / 9, 0.1],
        [0.02, 0.03, 0.2],
        [0.01, 0.13 / 7, 0.3],
        [0.03, 0.07, 0.4],
        [0.02, 0.06, 0.5],
        [0.02, 0.08, 0.6],
        [0.01, 0.17 / 3, 0.7],
        [0.01, 0.09, 0.8],
    ]
)
def test_c02_sr_ndi_calculation(red, nir, expected, tol=0.000001):
    # Check the normalized difference index calculation for a few different values
    input_img = ee.Image('LANDSAT/LT05/C02/T1_L2/LT05_042034_20091016')
    sr_img = landsat.c02_l2_sr(input_img).select(['red', 'nir']).multiply([0, 0]).add([red, nir])
    xy = input_img.geometry().centroid().getInfo()['coordinates']
    output = utils.point_image_value(landsat.c02_sr_ndi(sr_img, 'nir', 'red'), xy, 30)
    assert abs(output['ndi'] - expected) <= tol


@pytest.mark.parametrize(
    'b1_name, b2_name, b1_value, b2_value, expected',
    [
        ['nir', 'red', 0.07, 0.03, 0.4],
    ]
)
def test_c02_sr_ndi_input_bands(b1_name, b2_name, b1_value, b2_value, expected, tol=0.000001):
    # Check that the input band name parameters work and the order is correct
    # The input band naming is set to match the typical order in the NDVI calculation
    #   where the calculation is band 1 - band 2 over the sum ((NIR - RED) / (NIR + RED)
    # This is also consistent with the GEE .normalizedDifference() function
    input_img = ee.Image('LANDSAT/LT05/C02/T1_L2/LT05_042034_20091016')
    sr_img = landsat.c02_l2_sr(input_img).select([b1_name, b2_name]).multiply([0, 0]).add([b1_value, b2_value])
    xy = input_img.geometry().centroid().getInfo()['coordinates']
    output = utils.point_image_value(landsat.c02_sr_ndi(sr_img, b1_name=b1_name, b2_name=b2_name), xy, 30)
    assert abs(output['ndi'] - expected) <= tol
    output = utils.point_image_value(landsat.c02_sr_ndi(sr_img, b1_name, b2_name), xy, 30)
    assert abs(output['ndi'] - expected) <= tol


@pytest.mark.parametrize(
    'red, nir, expected',
    [
        [1.0, 0.4, 0.0],
        [0.4, 1.0, 0.0],
        [1.0, 1.0, 0.0],
    ]
)
def test_c02_sr_ndi_saturated_reflectance(red, nir, expected, tol=0.000001):
    # Check that saturated reflectance values return 0
    input_img = ee.Image('LANDSAT/LT05/C02/T1_L2/LT05_042034_20091016')
    sr_img = landsat.c02_l2_sr(input_img).select(['red', 'nir']).multiply([0, 0]).add([red, nir])
    xy = input_img.geometry().centroid().getInfo()['coordinates']
    output = utils.point_image_value(landsat.c02_sr_ndi(sr_img, 'nir', 'red'), xy, 30)
    assert abs(output['ndi'] - expected) <= tol


@pytest.mark.parametrize(
    'red, nir, expected',
    [
        [-0.1, -0.1, 0.0],
        [0.0, 0.0, 0.0],
        [0.009, 0.009, 0.0],
        [0.009, -0.01, 0.0],
        [-0.01, 0.009, 0.0],
        # Check that calculation works correctly if one value is above threshold
        [-0.01, 0.1, 1.0],
        [0.1, -0.01, -1.0],
    ]
)
def test_c02_sr_ndi_negative_non_water(red, nir, expected, tol=0.000001):
    # Check that non-water pixels with very low or negative reflectance values are set to 0.0
    input_img = ee.Image('LANDSAT/LT05/C02/T1_L2/LT05_042034_20091016')
    sr_img = landsat.c02_l2_sr(input_img).select(['red', 'nir']).multiply([0, 0]).add([red, nir])
    xy = input_img.geometry().centroid().getInfo()['coordinates']
    output = utils.point_image_value(landsat.c02_sr_ndi(sr_img, 'nir', 'red'), xy, 30)
    assert abs(output['ndi'] - expected) <= tol


@pytest.mark.parametrize(
    'red, nir, water_value',
    [
        [-0.1, -0.1, -0.1],
        [0.0, 0.0, -0.1],
        [0.009, 0.009, -0.1],
        [0.009, -0.01, -0.1],
        [-0.01, 0.009, -0.1],
        [-0.1, -0.1, -0.5],
    ]
)
def test_c02_sr_ndi_negative_water(red, nir, water_value, tol=0.000001):
    # Check that water pixels with very low or negative reflectance values are set to the water value
    input_img = ee.Image('LANDSAT/LT05/C02/T1_L2/LT05_042034_20091016')
    sr_img = landsat.c02_l2_sr(input_img).select(['red', 'nir']).multiply([0, 0]).add([red, nir])
    water_mask = landsat.c02_l2_sr(input_img).select(['QA_PIXEL']).multiply(0).add(1)
    xy = input_img.geometry().centroid().getInfo()['coordinates']
    output = utils.point_image_value(
        landsat.c02_sr_ndi(sr_img, 'nir', 'red', water_mask=water_mask, water_value=water_value), xy, 30
    )
    assert abs(output['ndi'] - water_value) <= tol


def test_c02_sr_ndi_no_water_mask(red=-1, nir=-1, water_value=-0.5, tol=0.000001):
    # The water value should only be applied if the water_mask is set
    input_img = ee.Image('LANDSAT/LT05/C02/T1_L2/LT05_042034_20091016')
    sr_img = landsat.c02_l2_sr(input_img).select(['red', 'nir']).multiply([0, 0]).add([red, nir])
    xy = input_img.geometry().centroid().getInfo()['coordinates']
    output = utils.point_image_value(landsat.c02_sr_ndi(sr_img, 'nir', 'red', water_value=water_value), xy, 30)
    assert abs(output['ndi'] - 0) <= tol


@pytest.mark.parametrize(
    'red, nir, refl_min, expected',
    [
        [0.03, 0.07, 0.02, 0.4],
        [0.03, 0.07, 0.03, 0.4],
        [0.03, 0.07, 0.05, 0.4],
        [0.03, 0.07, 0.07, 0.4],
        [0.03, 0.07, 0.08, 0.0],
    ]
)
def test_c02_sr_ndi_refl_min(red, nir, refl_min, expected, tol=0.000001):
    # Check that output is 0 if either reflectance values can be < than the refl_min parameter
    input_img = ee.Image('LANDSAT/LT05/C02/T1_L2/LT05_042034_20091016')
    sr_img = landsat.c02_l2_sr(input_img).select(['red', 'nir']).multiply([0, 0]).add([red, nir])
    xy = input_img.geometry().centroid().getInfo()['coordinates']
    output = utils.point_image_value(
        landsat.c02_sr_ndi(sr_img, b1_name='nir', b2_name='red', refl_min=refl_min), xy, 30
    )
    assert abs(output['ndi'] - expected) <= tol


@pytest.mark.parametrize(
    'red, nir, refl_max, expected',
    [
        [0.4, 0.6, 1.0, 0.2],
        [0.4, 0.6, 0.6, 0.0],
        [0.4, 0.6, 0.5, 0.0],
        [0.4, 0.6, 0.4, 0.0],
        [0.4, 0.6, 0.3, 0.0],
    ]
)
def test_c02_sr_ndi_refl_max(red, nir, refl_max, expected, tol=0.000001):
    # Check that output is 0 if either reflectance values can be >= than the refl_max parameter
    input_img = ee.Image('LANDSAT/LT05/C02/T1_L2/LT05_042034_20091016')
    sr_img = landsat.c02_l2_sr(input_img).select(['red', 'nir']).multiply([0, 0]).add([red, nir])
    xy = input_img.geometry().centroid().getInfo()['coordinates']
    output = utils.point_image_value(
        landsat.c02_sr_ndi(sr_img, b1_name='nir', b2_name='red', refl_max=refl_max), xy, 30
    )
    assert abs(output['ndi'] - expected) <= tol


def test_c02_sr_ndvi_band_name():
    # Check that the NDVI function works and returns a properly named output
    input_img = ee.Image('LANDSAT/LT05/C02/T1_L2/LT05_042034_20091016')
    sr_img = landsat.c02_l2_sr(input_img).select(['red', 'nir'])
    output = utils.get_info(landsat.c02_sr_ndvi(sr_img).bandNames())
    assert output == ['ndvi']


@pytest.mark.parametrize(
    'red, nir, expected',
    [
        [0.02, 0.9 / 55, -0.1],
        [0.03, 0.07, 0.4],
        [0.01, 0.09, 0.8],
        [1.0, 1.0, 0.0],
        # If the water_mask is not set, negative reflectance pixels will be set to 0
        [-0.1, -0.1, 0.0],
    ]
)
def test_c02_sr_ndi_calculation(red, nir, expected, tol=0.000001):
    # Check the NDVI function works for a couple of the same values
    input_img = ee.Image('LANDSAT/LT05/C02/T1_L2/LT05_042034_20091016')
    sr_img = landsat.c02_l2_sr(input_img).select(['red', 'nir']).multiply([0, 0]).add([red, nir])
    xy = input_img.geometry().centroid().getInfo()['coordinates']
    output = utils.point_image_value(landsat.c02_sr_ndvi(sr_img), xy, 30)
    assert abs(output['ndvi'] - expected) <= tol


@pytest.mark.parametrize(
    "qa_pixel, expected",
    [

        ['0000000000000000', 0],  # Designated Fill
        ['0000000000000001', 0],
        ['0000000000000010', 0],  # Dilated Cloud
        ['0000000000000100', 0],  # Cirrus
        ['0000000000001000', 1],  # Cloud
        ['0000000000010000', 1],  # Cloud Shadow
        ['0000000000100000', 0],  # Snow
        ['0000000001000000', 0],  # Clear
        ['0000000010000000', 0],  # Water
        # Check that any saturated bits are masked
        # ['0000000000100000', 0, 0],  # Snow
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
def test_c02_qa_pixel_mask_defaults(qa_pixel, expected):
    input_img = ee.Image.constant([int(qa_pixel, 2)]).rename(['QA_PIXEL'])
    output_img = landsat.c02_qa_pixel_mask(input_img)
    assert utils.constant_image_value(output_img)['mask'] == expected


@pytest.mark.parametrize(
    "img_value, arg_name, flag_value, expected",
    [
        # The "none" flag_value should test the default condition
        # Dilated clouds
        ['0000000000000010', 'dilate_flag', None, 0],
        ['0000000000000010', 'dilate_flag', False, 0],
        ['0000000000000010', 'dilate_flag', True, 1],
        # Cirrus clouds
        ['0000000000000100', 'cirrus_flag', None, 0],
        ['0000000000000100', 'cirrus_flag', False, 0],
        ['0000000000000100', 'cirrus_flag', True, 1],
        # Shadows
        ['0000000000010000', 'shadow_flag', None, 1],
        ['0000000000010000', 'shadow_flag', False, 0],
        ['0000000000010000', 'shadow_flag', True, 1],
        # Snow
        ['0000000000100000', 'snow_flag', None, 0],
        ['0000000000100000', 'snow_flag', False, 0],
        ['0000000000100000', 'snow_flag', True, 1],
        # Water
        ['0000000010000000', 'water_flag', None, 0],
        ['0000000010000000', 'water_flag', False, 0],
        ['0000000010000000', 'water_flag', True, 1],
    ]
)
def test_c02_qa_pixel_mask_flags(img_value, arg_name, flag_value, expected):
    input_img = ee.Image.constant([int(img_value, 2)]).rename(['QA_PIXEL'])
    input_args = {'input_img': input_img}
    if flag_value is not None:
        input_args[arg_name] = flag_value
    output_img = landsat.c02_qa_pixel_mask(**input_args)
    assert utils.constant_image_value(output_img)['mask'] == expected


@pytest.mark.parametrize(
    "qa_pixel, expected",
    [
        ['0000000000000000', 0],  # Designated Fill
        ['0000000000000001', 0],
        ['0000000010000000', 1],  # Water
    ]
)
def test_c02_qa_mask_defaults(qa_pixel, expected):
    input_img = ee.Image.constant([int(qa_pixel, 2)]).rename(['QA_PIXEL'])
    output_img = landsat.c02_qa_water_mask(input_img)
    assert utils.constant_image_value(output_img)['qa_water_mask'] == expected


@pytest.mark.parametrize(
    "scene_id, time_start",
    [
        ['LC08_030036_20210725', '2021-07-25T17:20:21'],
        ['LT05_044029_20000615', '2000-06-15T18:20:26'],  # No TOA image
    ]
)
def test_c02_cloud_score_mask(scene_id, time_start):
    input_img = (
        ee.Image.constant([1]).rename(['QA_PIXEL'])
        .set({'system:index': scene_id, 'system:time_start': ee.Date(time_start)})
    )
    output_img = landsat.c02_cloud_score_mask(input_img)
    assert utils.get_info(output_img)['bands'][0]['id'] == 'mask'


@pytest.mark.parametrize(
    "image_id, xy, threshold, expected",
    [
        ['LANDSAT/LT05/C02/T1_L2/LT05_042034_20091016', [-120.0, 37.0], 100, 1],
        # Pixel has a cloud score of 56, so mask if threshold is 50 but don't mask at 60
        ['LANDSAT/LT05/C02/T1_L2/LT05_042034_20091016', [-119.963613, 37.217444], 50, 1],
        ['LANDSAT/LT05/C02/T1_L2/LT05_042034_20091016', [-119.963613, 37.217444], 60, 0],
        # To TOA image
        ['LANDSAT/LT05/C02/T1_L2/LT05_044029_20000615', [-120.0, 45.0], 100, 0],
    ]
)
def test_c02_cloud_score_mask_values(image_id, xy, threshold, expected):
    output_img = landsat.c02_cloud_score_mask(ee.Image(image_id), threshold)
    output = utils.point_image_value(output_img, xy, scale=30)
    assert output['mask'] == expected


@pytest.mark.parametrize(
    "qa_radsat, spacecraft_id, expected",
    [
        # Saturated masking is currently True if any RGB band is saturated
        ['0000000000000000', 'LANDSAT_7', 0],  # No saturated bands
        ['0000000000000001', 'LANDSAT_7', 1],  # Blue saturated
        ['0000000000000100', 'LANDSAT_7', 1],  # Red saturated
        ['0000000000000111', 'LANDSAT_7', 1],  # RGB saturated
        ['0000000000001000', 'LANDSAT_7', 0],  # NIR saturated
        ['0000000000000000', 'LANDSAT_8', 0],  # No saturated bands
        ['0000000000000001', 'LANDSAT_8', 0],  # Cirrus saturated
        ['0000000000000010', 'LANDSAT_8', 1],  # Blue saturated
        ['0000000000001000', 'LANDSAT_8', 1],  # Red saturated
        ['0000000000001110', 'LANDSAT_8', 1],  # RGB saturated
        ['0000000000010000', 'LANDSAT_8', 0],  # NIR saturated
    ]
)
def test_c2_qa_radsat_mask(qa_radsat, spacecraft_id, expected):
    input_img = (
        ee.Image.constant([int(qa_radsat, 2)]).rename(['QA_RADSAT'])
        .set({'SPACECRAFT_ID': spacecraft_id})
    )
    output_img = landsat.c02_qa_radsat_mask(input_img)
    assert utils.constant_image_value(output_img)['mask'] == expected


# TODO: Add check for Landsat 8/9
@pytest.mark.parametrize(
    "sr_cloud_qa, spacecraft_id, expected",
    [
        ['0000000000000000', 'LANDSAT_7', 0],  # Clear?
        ['0000000000000001', 'LANDSAT_7', 0],  # Dark Dense Vegetation (DDV)
        ['0000000000000010', 'LANDSAT_7', 1],  # Cloud
        ['0000000000000100', 'LANDSAT_7', 1],  # Cloud Shadow
        ['0000000000001000', 'LANDSAT_7', 1],  # Adjacent to cloud
        ['0000000000010000', 'LANDSAT_7', 1],  # Snow
        ['0000000000100000', 'LANDSAT_7', 0],  # Water
        ['0000000000000010', 'LANDSAT_5', 1],  # Landsat 5 cloud
        # QA_PIXEL * 0 is returned for Landsat 8/9
        ['0000000000000000', 'LANDSAT_8', 0],
        ['0000000000000010', 'LANDSAT_8', 0],
        ['0000000000000010', 'LANDSAT_9', 0],  # Cloud
    ]
)
def test_c02_l2_sr_cloud_qa_mask(sr_cloud_qa, spacecraft_id, expected):
    input_img = (
        ee.Image.constant([int(sr_cloud_qa, 2), int('0000000000000001', 2)])
        .rename(['SR_CLOUD_QA', 'QA_PIXEL'])
        .set({'SPACECRAFT_ID': spacecraft_id})
    )
    output_img = landsat.c02_l2_sr_cloud_qa_mask(input_img)
    assert utils.constant_image_value(output_img)['mask'] == expected


@pytest.mark.parametrize(
    "scene_id, time_start, image_property, match_property, expected",
    [
        ['LC80300362021206LGN00', '2021-07-25T17:20:21', 'LANDSAT_SCENE_ID', 'LANDSAT_SCENE_ID', 1],
        ['LC08_030036_20210725', '2021-07-25T17:20:21', 'system:index', 'system:index', 1],
        # This image does not have a corresponding TOA image
        ['LT05_044029_20000615', '2000-06-15T18:20:26', 'system:index', 'system:index', 0],
    ]
)
def test_c02_matched_toa_coll(scene_id, time_start, image_property, match_property, expected):
    properties = {
        image_property: scene_id,
        'system:time_start': ee.Date(time_start),
    }
    output_coll = landsat.c02_matched_toa_coll(
        ee.Image.constant([1]).rename(['QA_PIXEL']).set(properties),
        image_property, match_property
    )
    assert utils.get_info(output_coll.size()) == expected


@pytest.mark.parametrize(
    "scene_id, time_start, expected",
    [
        ['LC80300362021206LGN00', '2021-07-25T17:20:21', 1],
        ['LT50440292000167XXX02', '2000-06-15T18:20:26', 0],  # No TOA image
    ]
)
def test_c02_matched_toa_coll_default_match_properties(scene_id, time_start, expected):
    # The function currently defaults to using the LANDSAT_SCENE_ID for matching
    properties = {
        'LANDSAT_SCENE_ID': scene_id,
        'system:time_start': ee.Date(time_start),
    }
    output_coll = landsat.c02_matched_toa_coll(
        ee.Image.constant(1).rename(['QA_PIXEL']).set(properties),
    )
    assert utils.get_info(output_coll.size()) == expected


@pytest.mark.parametrize(
    "scene_id, time_start, image_property, match_property, expected",
    [
        ['LC80300362021206LGN00', '2021-07-25T17:20:21', 'LANDSAT_SCENE_ID', 'LANDSAT_SCENE_ID', 1],
        ['LC08_030036_20210725', '2021-07-25T17:20:21', 'system:index', 'system:index', 1],
    ]
)
def test_c02_matched_l2_coll(scene_id, time_start, image_property, match_property, expected):
    properties = {
        image_property: scene_id,
        'system:time_start': ee.Date(time_start),
    }
    output_coll = landsat.c02_matched_l2_coll(
        ee.Image.constant([1]).rename(['QA_PIXEL']).set(properties),
        image_property, match_property
    )
    assert utils.get_info(output_coll.size()) == expected


@pytest.mark.parametrize(
    "scene_id, time_start",
    [
        ['LC80300362021206LGN00', '2021-07-25T17:20:21'],
    ]
)
def test_c02_matched_l2_coll_default_match_properties(scene_id, time_start):
    # The function currently defaults to using the LANDSAT_SCENE_ID for matching
    properties = {
        'LANDSAT_SCENE_ID': scene_id,
        'system:time_start': ee.Date(time_start),
    }
    output_coll = landsat.c02_matched_l2_coll(
        ee.Image.constant(1).rename(['QA_PIXEL']).set(properties),
    )
    assert utils.get_info(output_coll.size()) == 1
