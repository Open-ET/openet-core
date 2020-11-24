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


def test_constant_image_value(tol=0.000001):
    expected = 10.123456789
    input_img = ee.Image.constant(expected)
    output = utils.constant_image_value(input_img)
    assert abs(output['constant'] - expected) <= tol


def test_constant_image_value_band_name(tol=0.000001):
    """Test that a custom band name is carried through"""
    expected = 10.123456789
    input_img = ee.Image.constant(expected).rename('foo')
    output = utils.constant_image_value(input_img)
    assert abs(output['foo'] - expected) <= tol


def test_constant_image_value_multiband(tol=0.000001):
    """Test that a multiband image returns multiple values"""
    expected = 10.123456789
    input_img = ee.Image.constant([expected, expected + 1])
    output = utils.constant_image_value(input_img)
    assert abs(output['constant_0'] - expected) <= tol
    assert abs(output['constant_1'] - (expected + 1)) <= tol


def test_constant_image_value_multiband_bands(tol=0.000001):
    """Test that the band names are carried through on a multiband image"""
    expected = 10.123456789
    input_img = ee.Image.constant([expected, expected + 1])\
        .rename(['foo', 'bar'])
    output = utils.constant_image_value(input_img)
    assert abs(output['foo'] - expected) <= tol
    assert abs(output['bar'] - (expected + 1)) <= tol


def test_point_image_value(tol=0.001):
    expected = 2364.351
    output = utils.point_image_value(
        ee.Image('USGS/NED'), [-106.03249, 37.17777])
    assert abs(output['elevation'] - expected) <= tol


def test_point_coll_value(tol=0.001):
    expected = 2364.351
    output = utils.point_coll_value(
        ee.ImageCollection([ee.Image('USGS/NED')]), [-106.03249, 37.17777])
    assert abs(output['elevation']['2012-04-04'] - expected) <= tol
