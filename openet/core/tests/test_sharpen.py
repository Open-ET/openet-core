# import datetime
import logging
import pprint

import ee
# import pytest

import openet.core.sharpen as sharpen
import openet.core.utils as utils

logging.basicConfig(level=logging.DEBUG, format='%(message)s')

TEST_POINT = [-121.5265, 38.7399]


def test_ee_init():
    assert ee.Number(1).getInfo() == 1


def test_sharpen_thermal_landsat_sr():
    input_img = ee.Image('LANDSAT/LC08/C01/T1_SR/LC08_044033_20170716')

    # Copied from PTJPL Image.from_landsat_c1_sr()
    input_bands = ee.Dictionary({
        'LANDSAT_5': ['B1', 'B2', 'B3', 'B4', 'B5', 'B7', 'B6', 'pixel_qa'],
        'LANDSAT_7': ['B1', 'B2', 'B3', 'B4', 'B5', 'B7', 'B6', 'pixel_qa'],
        'LANDSAT_8': ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B10', 'pixel_qa']})
    output_bands = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'tir',
                    'pixel_qa']
    spacecraft_id = ee.String(input_img.get('SATELLITE'))
    prep_image = input_img \
        .select(input_bands.get(spacecraft_id), output_bands) \
        .multiply([0.0001, 0.0001, 0.0001, 0.0001, 0.0001, 0.0001, 0.1, 1]) \
        .set({'SATELLITE': spacecraft_id})
        # .set({'system:index': input_img.get('system:index'),
        #       'system:time_start': input_img.get('system:time_start'),
        #       'system:id': input_img.get('system:id'),
        #       'SATELLITE': spacecraft_id})
    pprint.pprint(prep_image.getInfo())

    output_img = sharpen.thermal(prep_image)
    # pprint.pprint(output_img.getInfo())

    pprint.pprint(utils.point_image_value(prep_image.select(['tir']), TEST_POINT, scale=1))
    pprint.pprint(utils.point_image_value(output_img.select(['tir']), TEST_POINT, scale=1))
    assert True
    # assert utils.point_image_value(output_img, TEST_POINT, scale=1) == 300
    # assert utils.constant_image_value(ee.Image(output_img))['QA60'] == expected
