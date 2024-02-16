import datetime
import types

import ee
import pytest

import openet.core.utils as utils


def arg_valid_date():
    assert utils.arg_valid_date('2020-03-10') == datetime.datetime(2020, 3, 10)


def arg_valid_date_exception():
    with pytest.raises(Exception):
        assert utils.arg_valid_date('3/10/2010')


# def arg_valid_file():
#     assert False


def test_get_info():
    assert utils.get_info(ee.Number(1)) == 1


def test_get_info_zero():
    assert utils.get_info(ee.Number(0)) == 0


def test_get_info_empty_list():
    assert utils.get_info(ee.List([])) == []


def test_date_0utc(date='2015-07-13'):
    assert utils.get_info(utils.date_0utc(
        ee.Date(date).advance(2, 'hour')).format('yyyy-MM-dd')) == date


def test_date_range_type():
    output = utils.date_range(
        datetime.datetime(2020, 1, 1), datetime.datetime(2020, 1, 3))
    assert isinstance(output, types.GeneratorType)


@pytest.mark.parametrize(
    'start_dt, end_dt, expected',
    [
        [datetime.datetime(2020, 1, 1), datetime.datetime(2020, 1, 3), 3],
        [datetime.datetime(2003, 12, 30), datetime.datetime(2004, 1, 3), 5],
        [datetime.datetime(2004, 2, 28), datetime.datetime(2004, 3, 1), 3],
        [datetime.datetime(2001, 1, 1), datetime.datetime(2002, 1, 1), 366],
    ]
)
def test_date_range_defaults(start_dt, end_dt, expected):
    # For now just test that the size of the range is correct
    assert len(list(utils.date_range(start_dt, end_dt))) == expected


@pytest.mark.parametrize(
    'start_dt, end_dt, days, expected',
    [
        [datetime.datetime(2001, 1, 1), datetime.datetime(2001, 1, 1), 2, 1],
        [datetime.datetime(2001, 1, 1), datetime.datetime(2001, 1, 2), 2, 1],
        [datetime.datetime(2001, 1, 1), datetime.datetime(2001, 1, 3), 2, 2],
        [datetime.datetime(2001, 1, 1), datetime.datetime(2001, 1, 4), 2, 2],
    ]
)
def test_date_range_days(start_dt, end_dt, days, expected):
    print(list(utils.date_range(start_dt, end_dt, days=days)))
    assert len(list(utils.date_range(start_dt, end_dt, days=days))) == expected


@pytest.mark.parametrize(
    'start_dt, end_dt, skip_leap_days, expected',
    [
        [datetime.datetime(2004, 2, 28), datetime.datetime(2004, 3, 1), True, 2],
        # [datetime.datetime(2000, 2, 28), datetime.datetime(2000, 3, 1), True, 2],
    ]
)
def test_date_range_skip_leap_days(start_dt, end_dt, skip_leap_days, expected):
    assert len(list(utils.date_range(
        start_dt, end_dt, skip_leap_days=skip_leap_days))) == expected


# def test_delay_task():
#     assert False


# def test_get_ee_assets():
#     assert False


def test_get_ee_assets_exception():
    with pytest.raises(Exception):
        assert utils.get_ee_assets('deadbeef', retries=1)


# def test_get_ee_tasks():
#     assert False


# def test_ee_task_start():
#     assert False


@pytest.mark.parametrize(
    # Note: These are made up values
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
    assert utils.millis(datetime.datetime(2015, 7, 13)) == 1436745600000


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
        ['USGS/NED', [-106.03249, 37.17777], 10, 2364.351, 0.001],
        ['USGS/NED', [-106.03249, 37.17777], 1, 2364.351, 0.001],
    ]
)
def test_point_image_value(image_id, xy, scale, expected, tol):
    output = utils.point_image_value(ee.Image(image_id).rename('output'), xy)
    assert abs(output['output'] - expected) <= tol


@pytest.mark.parametrize(
    'image_id, image_date, xy, scale, expected, tol',
    [
        # CGM - This test stopped working for a scale of 1 and returns a different
        #   value for a scale of 10 than the point_image_value() function above.
        # This function uses getRegion() instead of a reduceRegion() call,
        #   so there might have been some sort of change in getRegion().
        ['USGS/NED', '2012-04-04', [-106.03249, 37.17777], 10, 2364.286, 0.001],
        # CGM - The default scale of 1 now returns None/Null for some reason
        # ['USGS/NED', '2012-04-04', [-106.03249, 37.17777], 1, 2364.351, 0.001],
    ]
)
def test_point_coll_value(image_id, image_date, xy, scale, expected, tol):
    input_img = ee.Image(image_id).rename(['output'])
    output = utils.point_coll_value(ee.ImageCollection([input_img]), xy, scale)
    assert abs(output['output'][image_date] - expected) <= tol
