from datetime import datetime
import types

import ee
import pytest

import openet.core.utils as utils


def arg_valid_date():
    assert utils.arg_valid_date('2020-03-10') == datetime(2020, 3, 10)


def arg_valid_date_exception():
    with pytest.raises(Exception):
        assert utils.arg_valid_date('3/10/2010')


# TODO: Write this test
# def arg_valid_file():
#     assert False


def test_get_info():
    assert utils.get_info(ee.Number(1)) == 1


def test_get_info_zero():
    assert utils.get_info(ee.Number(0)) == 0


def test_get_info_empty_list():
    assert utils.get_info(ee.List([])) == []


def test_affine_transform():
    output = utils.get_info(utils.affine_transform(ee.Image('NASA/NASADEM_HGT/001')))
    assert output == [0.0002777777777777778, 0, -179.0001388888889, 0, -0.0002777777777777778, 61.00013888888889]


# TODO: Write this test
# def test_build_parent_folders():
#     assert False


def test_date_0utc(date='2015-07-13'):
    assert utils.get_info(utils.date_0utc(
        ee.Date(date).advance(2, 'hour')).format('yyyy-MM-dd')) == date


def test_date_range_type():
    output = utils.date_range(
        datetime(2020, 1, 1), datetime(2020, 1, 3))
    assert isinstance(output, types.GeneratorType)


@pytest.mark.parametrize(
    'start_dt, end_dt, expected',
    [
        [datetime(2020, 1, 1), datetime(2020, 1, 3), 3],
        [datetime(2003, 12, 30), datetime(2004, 1, 3), 5],
        [datetime(2004, 2, 28), datetime(2004, 3, 1), 3],
        [datetime(2001, 1, 1), datetime(2002, 1, 1), 366],
    ]
)
def test_date_range_defaults(start_dt, end_dt, expected):
    # For now just test that the size of the range is correct
    assert len(list(utils.date_range(start_dt, end_dt))) == expected


@pytest.mark.parametrize(
    'start_dt, end_dt, days, expected',
    [
        [datetime(2001, 1, 1), datetime(2001, 1, 1), 2, 1],
        [datetime(2001, 1, 1), datetime(2001, 1, 2), 2, 1],
        [datetime(2001, 1, 1), datetime(2001, 1, 3), 2, 2],
        [datetime(2001, 1, 1), datetime(2001, 1, 4), 2, 2],
    ]
)
def test_date_range_days(start_dt, end_dt, days, expected):
    print(list(utils.date_range(start_dt, end_dt, days=days)))
    assert len(list(utils.date_range(start_dt, end_dt, days=days))) == expected


@pytest.mark.parametrize(
    'start_dt, end_dt, skip_leap_days, expected',
    [
        [datetime(2004, 2, 28), datetime(2004, 3, 1), True, 2],
    ]
)
def test_date_range_skip_leap_days(start_dt, end_dt, skip_leap_days, expected):
    assert len(list(utils.date_range(
        start_dt, end_dt, skip_leap_days=skip_leap_days))) == expected


@pytest.mark.parametrize(
    'start_dt, end_dt, exclusive_end_dates, expected',
    [
        [
            datetime(2004, 2, 1), datetime(2004, 2, 28), False,
            [(datetime(2004, 2, 1), datetime(2004, 2, 28))]
        ],
        [
            datetime(2004, 2, 1), datetime(2004, 2, 28), True,
            [(datetime(2004, 2, 1), datetime(2004, 2, 29))]
        ],
        [
            datetime(2005, 2, 1), datetime(2005, 2, 28), True,
            [(datetime(2005, 2, 1), datetime(2005, 3, 1))]
        ],
        [
            datetime(2004, 2, 1), datetime(2005, 2, 28), False,
            [
                (datetime(2004, 2, 1), datetime(2004, 12, 31)),
                (datetime(2005, 1, 1), datetime(2005, 2, 28))
            ]
        ],
        [
            datetime(2005, 2, 1), datetime(2006, 2, 28), True,
            [
                (datetime(2005, 2, 1), datetime(2006, 1, 1)),
                (datetime(2006, 1, 1), datetime(2006, 3, 1))
            ]
        ],
    ]
)
def test_date_years(start_dt, end_dt, exclusive_end_dates, expected):
    assert list(utils.date_years(start_dt, end_dt, exclusive_end_dates)) == expected


def test_dilate_default():
    # Check that default dilate is for a single pixel
    # -75.4375, 35.5125 is edge pixel of NLDAS mask
    mask = ee.ImageCollection("NASA/NLDAS/FORA0125_H002").first().select([0], ['mask']).mask()
    output = utils.dilate(mask)
    assert utils.point_image_value(mask, [-75.4375, 35.5125], 14000)['mask'] == 1
    assert utils.point_image_value(mask, [-75.4375 + 0.125, 35.5125], 14000)['mask'] == 0
    assert utils.point_image_value(output, [-75.4375 + 0.125, 35.5125], 14000)['mask'] == 1
    assert utils.point_image_value(output, [-75.4375 + 0.250, 35.5125], 14000)['mask'] == 0


@pytest.mark.parametrize(
    'pixels, xy, expected',
    [
        # Starting location is an active pixel on the edge of the mask
        [1, [-75.4375 + (1 * 0.125), 35.5125], 1],
        [1, [-75.4375 + (2 * 0.125), 35.5125], 0],
        [2, [-75.4375 + (2 * 0.125), 35.5125], 1],
        [2, [-75.4375 + (3 * 0.125), 35.5125], 0],
        [10, [-75.4375 + (10 * 0.125), 35.5125], 1],
        [10, [-75.4375 + (11 * 0.125), 35.5125], 0],
    ]
)
def test_dilate_pixels_parameter(pixels, xy, expected):
    mask = ee.ImageCollection("NASA/NLDAS/FORA0125_H002").first().select([0], ['mask']).mask()
    output = utils.dilate(mask, pixels=pixels)
    assert utils.point_image_value(output, xy, 14000)['mask'] == expected


def test_erode_default():
    # Check that default erode is for a single pixel
    # -75.4375, 35.7075 is edge pixel of NLDAS mask
    mask = ee.ImageCollection("NASA/NLDAS/FORA0125_H002").first().select([0], ['mask']).mask()
    output = utils.erode(mask)
    assert utils.point_image_value(mask, [-75.4375, 35.6875], 14000)['mask'] == 1
    assert utils.point_image_value(mask, [-75.4375 - 0.125, 35.6875], 14000)['mask'] == 1
    assert utils.point_image_value(output, [-75.4375, 35.6875], 14000)['mask'] == 0
    assert utils.point_image_value(output, [-75.4375 - 0.125, 35.6875], 14000)['mask'] == 1


@pytest.mark.parametrize(
    'pixels, xy, expected',
    [
        # Starting location is an active pixel on the edge of the mask
        # Higher pixel value don't work linearly at this test spot
        [1, [-75.4375, 35.6875], 0],
        [1, [-75.4375 - (1 * 0.125), 35.6875], 1],
        [2, [-75.4375 - (1 * 0.125), 35.6875], 0],
        [2, [-75.4375 - (2 * 0.125), 35.6875], 1],
        [4, [-75.4375 - (3 * 0.125), 35.6875], 0],
        [4, [-75.4375 - (4 * 0.125), 35.6875], 1],
    ]
)
def test_erode_pixels_parameter(pixels, xy, expected):
    mask = ee.ImageCollection("NASA/NLDAS/FORA0125_H002").first().select([0], ['mask']).mask()
    output = utils.erode(mask, pixels=pixels)
    assert utils.point_image_value(output, xy, 14000)['mask'] == expected


# TODO: Write this test
# def test_delay_task():
#     assert False


# TODO: Write this test
# def test_get_ee_assets():
#     assert False


def test_get_ee_assets_exception():
    with pytest.raises(Exception):
        assert utils.get_ee_assets('deadbeef', retries=1)


# TODO: Write this test
# def test_get_ee_tasks():
#     assert False


# TODO: Write this test
# def test_ee_task_start():
#     assert False


@pytest.mark.parametrize(
    'input_value, expected',
    [
        [300, True],
        ['300', True],
        [300.25, True],
        ['300.25', True],
        ['a', False],
    ]
)
def test_is_number(input_value, expected):
    assert utils.is_number(input_value) == expected


def test_millis():
    assert utils.millis(datetime(2015, 7, 13)) == 1436745600000


def test_parse_landsat_id():
    assert utils.parse_landsat_id('LC08_030036_20210725') == ('LC08', 30, 36, 2021, 7, 25)


@pytest.mark.parametrize(
    'input_value, expected',
    [
        ['1', [1]],
        ['1, 2', [1, 2]],
        ['1-3,5', [1, 2, 3, 5]],
        ['1-3,5, 9-10', [1, 2, 3, 5, 9, 10]],
    ]
)
def test_parse_int_set(input_value, expected):
    assert utils.parse_int_set(input_value) == set(expected)


@pytest.mark.parametrize(
    'input_value, expected',
    [
        [{'p042r032'}, '42:[32]'],
        [['p042r032', 'p042r032'], '42:[32]'],
        [{'p042r032', 'p042r033'}, '42:[32,33]'],
        [{'p042r032', 'p042r033', 'p042r034'}, '42:[32-34]'],
        [{'p042r032', 'p042r033', 'p042r034', 'p043r034'}, '42:[32-34],43:[34]'],
    ]
)
def test_wrs2_set_2_str(input_value, expected):
    assert utils.wrs2_set_2_str(input_value) == expected


@pytest.mark.parametrize(
    'input_value, expected',
    [
        ['42:[32]', {'p042r032'}],
        ['42:[32,33]', {'p042r032', 'p042r033'}],
        ['42:[32-34]', {'p042r032', 'p042r033', 'p042r034'}],
        ['42:[32-34],43:[34]', {'p042r032', 'p042r033', 'p042r034', 'p043r034'}],
    ]
)
def test_wrs2_str_2_set(input_value, expected):
    assert utils.wrs2_str_2_set(input_value) == expected


@pytest.mark.parametrize(
    'input_value, expected',
    [
        ['1', [1]],
        ['1, 2', [1, 2]],
        ['1-3,5', [1, 2, 3, 5]],
        ['1-3,5,9-10', [1, 2, 3, 5, 9, 10]],
    ]
)
def test_str_ranges_2_list(input_value, expected):
    assert utils.str_ranges_2_list(input_value) == expected


@pytest.mark.parametrize(
    'input_value, expected',
    [
        [[1], '1'],
        [[1, 2], '1,2'],
        [[1, 2, 3, 5], '1-3,5'],
        [[1, 2, 3, 5, 9, 10], '1-3,5,9,10'],
    ]
)
def test_list_2_str_ranges(input_value, expected):
    assert utils.list_2_str_ranges(input_value) == expected


def test_ver_str_2_num():
    assert utils.ver_str_2_num('0.20.6') == [0, 20, 6]


def test_constant_image_value(expected=10.123456789, tol=0.000001):
    output = utils.constant_image_value(ee.Image.constant(expected))
    assert abs(output['constant'] - expected) <= tol


def test_constant_image_value_band_name(expected=10.123456789, tol=0.000001):
    """Test that a custom band name is carried through"""
    input_img = ee.Image.constant(expected).rename('foo')
    output = utils.constant_image_value(input_img)
    assert abs(output['foo'] - expected) <= tol


def test_constant_image_value_multiband(expected=10.123456789, tol=0.000001):
    """Test that a multiband image returns multiple values"""
    input_img = ee.Image.constant([expected, expected + 1])
    output = utils.constant_image_value(input_img)
    assert abs(output['constant_0'] - expected) <= tol
    assert abs(output['constant_1'] - (expected + 1)) <= tol


def test_constant_image_value_multiband_bands(expected=10.123456789, tol=0.000001):
    """Test that the band names are carried through on a multiband image"""
    input_img = ee.Image.constant([expected, expected + 1]).rename(['foo', 'bar'])
    output = utils.constant_image_value(input_img)
    assert abs(output['foo'] - expected) <= tol
    assert abs(output['bar'] - (expected + 1)) <= tol


@pytest.mark.parametrize(
    'image_id, xy, scale, expected, tol',
    [
        ['USGS/3DEP/10m', [-106.03249, 37.17777], 30, 2364.169, 0.001],
        ['USGS/3DEP/10m', [-106.03249, 37.17777], 10, 2364.138, 0.001],
        ['USGS/3DEP/10m', [-106.03249, 37.17777], 1, 2364.138, 0.001],
        ['NASA/NASADEM_HGT/001', [-106.03249, 37.17777], 30, 2361, 0.001],
    ]
)
def test_point_image_value(image_id, xy, scale, expected, tol):
    output = utils.point_image_value(ee.Image(image_id).select(['elevation'], ['output']), xy, scale)
    assert abs(output['output'] - expected) <= tol


@pytest.mark.parametrize(
    'image_id, image_date, xy, scale, expected, tol',
    [
        ['USGS/3DEP/10m', '2012-04-04', [-106.03249, 37.17777], 30, 2364.169, 0.001],
        ['USGS/3DEP/10m', '2012-04-04', [-106.03249, 37.17777], 10, 2364.097, 0.001],
        ['USGS/3DEP/10m', '2012-04-04', [-106.03249, 37.17777], 1, 2364.138, 0.001],
        ['NASA/NASADEM_HGT/001', '2012-04-04', [-106.03249, 37.17777], 30, 2361, 0.001],
    ]
)
def test_point_coll_value(image_id, image_date, xy, scale, expected, tol):
    # The image must have a system:time_start for this function to work correctly
    input_img = (
        ee.Image(image_id).select(['elevation'], ['output'])
        .set({'system:time_start': ee.Date(image_date).millis()})
    )
    output = utils.point_coll_value(ee.ImageCollection([input_img]), xy, scale)
    assert abs(output['output'][image_date] - expected) <= tol


def test_point_coll_value_no_system_time_start_exception():
    # The function should raise an exception for images with no system:time_start
    input_img = ee.Image('USGS/3DEP/10m').select(['elevation'], ['output'])
    with pytest.raises(Exception):
        utils.point_coll_value(ee.ImageCollection([input_img]), [-106, 37], 30)
