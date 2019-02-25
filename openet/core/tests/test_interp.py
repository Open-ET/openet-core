import datetime
import logging
import pprint

import ee
import pytest

import openet.core.interp as interp
import openet.core.utils as utils

logging.basicConfig(level=logging.DEBUG, format='%(message)s')


def test_ee_init():
    assert ee.Number(1).getInfo() == 1


@pytest.mark.parametrize(
    # GRIDMET start times are 7 UTC
    #   1439532000000 - 2015-08-14
    #   1439618400000 - 2015-08-15
    #   1439704800000 - 2015-08-16
    #   1439791200000 - 2015-08-17
    #   1439877600000 - 2015-08-18
    #   1440309600000 - 2015-08-23
    #   1441000800000 - 2015-08-31

    # Landsat start_times are ~18 UTC
    #   1438277862725 - 2015-07-30
    #   1439660268614 - 2015-08-15
    #   1441042674222 - 2015-08-31
    #   1442425082323 - 2015-09-16

    "tgt_value, tgt_time, src_values, src_times, expected",
    [
        # Test normal interpolation between two images
        # [10, 1439618400000, [0.0, 1.6], [1439660268614, 1441042674222], 0.0],
        [10, 1439704800000, [0.0, 1.6], [1439660268614, 1441042674222], 0.1],
        [10, 1440309600000, [0.0, 1.6], [1439660268614, 1441042674222], 0.8],
        # This fails?
        [10, 1441000800000, [0.0, 1.6], [1439660268614, 1441042674222], 1.6],

        # Test if one side of the range is totally nodata
        [10, 1439704800000, [0.0, None], [1439660268614, 1441042674222], 0.0],
        [10, 1439704800000, [None, 1.6], [1439660268614, 1441042674222], 1.6],

        # Test with multiple dates
        [10, 1439704800000, [0.0, 1.6, 3.2, 4.8],
         [1438277862725, 1439660268614, 1441042674222, 1442425082323], 1.7],
        [10, 1439704800000, [0.0, None, 3.2, 4.8],
         [1438277862725, 1439660268614, 1441042674222, 1442425082323], 1.7],
        [10, 1439704800000, [0.0, 1.6, None, 4.8],
         [1438277862725, 1439660268614, 1441042674222, 1442425082323], 1.7],

        # Test with real data
        [
            4.8153934,
            # 4/10/2015
            1428645600000,
            [0.0, 0.0, 0.0, 0.329212732, 0.124609835, 0.268005646],
            # 2/14/2015, 3/10/2015, 3/26/2015, 4/11/2015, 5/29/2015, 6/6/2015
            [1423872000000, 1425945600000, 1427328000000,
             1428710400000, 1432857600000, 1433548800000],
            0.308636806
        ],
    ]
)
def test_daily_collection(tgt_value, tgt_time, src_values, src_times,
                          expected, tol=0.01):
    """Test the daily method for collections of constant images"""
    tgt_coll = ee.ImageCollection([
        ee.Image.constant(tgt_value).rename(['tgt'])\
            .set({'system:time_start': tgt_time})])

    src_images = []
    for src, time in zip(src_values, src_times):
        date_0utc = utils.date_0utc(ee.Date(time))
        time_0utc = date_0utc.millis()
        if src is not None:
            image = ee.Image.constant([src, time_0utc]).double() \
                .rename(['src', 'time']) \
                .set({
                    'system:index': ee.Date(time).format('yyyyMMdd'),
                    'system:time_start': time})
        else:
            image = ee.Image.constant([1, time_0utc]).double().updateMask(0) \
                .rename(['src', 'time']) \
                .set({
                    'system:index': ee.Date(time).format('yyyyMMdd'),
                    'system:time_start': time})
        src_images.append(image)
    src_coll = ee.ImageCollection.fromImages(src_images)

    output_coll = interp.daily(
        tgt_coll, src_coll, interp_days=32, interp_method='linear')

    output = utils.constant_image_value(ee.Image(output_coll.first()))
    assert abs(output['src'] - expected) <= tol
    assert abs(output['tgt'] - tgt_value) <= tol


@pytest.mark.parametrize(
    "interp_days, tgt_value, tgt_time, src_values, src_times, expected",
    [
        # Commented out half the tests that seemed redundant
        [4, 10, 1439618400000, [0.0, 1.6], [1439660268614, 1441042674222], 0.0],
        [4, 10, 1439704800000, [0.0, 1.6], [1439660268614, 1441042674222], 0.0],
        [4, 10, 1439791200000, [0.0, 1.6], [1439660268614, 1441042674222], 0.0],
        [4, 10, 1439877600000, [0.0, 1.6], [1439660268614, 1441042674222], 0.0],
        [4, 10, 1439964000000, [0.0, 1.6], [1439660268614, 1441042674222], 0.0],
        [4, 10, 1440050400000, [0.0, 1.6], [1439660268614, 1441042674222], None],
        [4, 10, 1440136800000, [0.0, 1.6], [1439660268614, 1441042674222], None],
        [4, 10, 1440223200000, [0.0, 1.6], [1439660268614, 1441042674222], None],
        [4, 10, 1440309600000, [0.0, 1.6], [1439660268614, 1441042674222], None],
        [4, 10, 1440396000000, [0.0, 1.6], [1439660268614, 1441042674222], None],
        [4, 10, 1440482400000, [0.0, 1.6], [1439660268614, 1441042674222], None],
        [4, 10, 1440568800000, [0.0, 1.6], [1439660268614, 1441042674222], None],
        [4, 10, 1440655200000, [0.0, 1.6], [1439660268614, 1441042674222], 1.6],
        [4, 10, 1440741600000, [0.0, 1.6], [1439660268614, 1441042674222], 1.6],
        [4, 10, 1440828000000, [0.0, 1.6], [1439660268614, 1441042674222], 1.6],
        [4, 10, 1440914400000, [0.0, 1.6], [1439660268614, 1441042674222], 1.6],
        [4, 10, 1441000800000, [0.0, 1.6], [1439660268614, 1441042674222], 1.6],
        [10, 10, 1439618400000, [0.0, 1.6], [1439660268614, 1441042674222], 0.0],
        [10, 10, 1439704800000, [0.0, 1.6], [1439660268614, 1441042674222], 0.0],
        [10, 10, 1439791200000, [0.0, 1.6], [1439660268614, 1441042674222], 0.0],
        [10, 10, 1439877600000, [0.0, 1.6], [1439660268614, 1441042674222], 0.0],
        [10, 10, 1439964000000, [0.0, 1.6], [1439660268614, 1441042674222], 0.0],
        [10, 10, 1440050400000, [0.0, 1.6], [1439660268614, 1441042674222], 0.0],
        [10, 10, 1440136800000, [0.0, 1.6], [1439660268614, 1441042674222], 0.6],
        [10, 10, 1440223200000, [0.0, 1.6], [1439660268614, 1441042674222], 0.7],
        [10, 10, 1440309600000, [0.0, 1.6], [1439660268614, 1441042674222], 0.8],
        [10, 10, 1440396000000, [0.0, 1.6], [1439660268614, 1441042674222], 0.9],
        [10, 10, 1440482400000, [0.0, 1.6], [1439660268614, 1441042674222], 1.0],
        [10, 10, 1440568800000, [0.0, 1.6], [1439660268614, 1441042674222], 1.6],
        [10, 10, 1440655200000, [0.0, 1.6], [1439660268614, 1441042674222], 1.6],
        [10, 10, 1440741600000, [0.0, 1.6], [1439660268614, 1441042674222], 1.6],
        [10, 10, 1440828000000, [0.0, 1.6], [1439660268614, 1441042674222], 1.6],
        [10, 10, 1440914400000, [0.0, 1.6], [1439660268614, 1441042674222], 1.6],
        [10, 10, 1441000800000, [0.0, 1.6], [1439660268614, 1441042674222], 1.6],
    ]
)
def test_daily_interp_days(interp_days, tgt_value, tgt_time, src_values,
                           src_times, expected, tol=0.01):
    """Test the daily method for small interp_days values"""
    tgt_coll = ee.ImageCollection([
        ee.Image.constant(tgt_value).rename(['tgt'])\
            .set({'system:time_start': tgt_time,
                  'system:index': datetime.datetime.utcfromtimestamp(
                      tgt_time / 1000.0).strftime('%Y-%m-%d')})])
    src_coll = ee.ImageCollection([
        ee.Image.constant([value, utils.date_0utc(ee.Date(time)).millis()])\
            .double().rename(['src', 'time'])\
            .set({'system:time_start': time,
                  'system:index': datetime.datetime.utcfromtimestamp(
                      time / 1000.0).strftime('%Y-%m-%d')})
        for time, value in zip(src_times, src_values)])

    output_coll = ee.ImageCollection(interp.daily(
        tgt_coll, src_coll, interp_days=interp_days, interp_method='linear'))

    output = utils.constant_image_value(ee.Image(output_coll.first()))
    if expected is None:
        assert output['src'] is None
        assert abs(output['tgt'] - tgt_value) <= tol
    else:
        assert abs(output['src'] - expected) <= tol
        assert abs(output['tgt'] - tgt_value) <= tol


@pytest.mark.parametrize(
    #
    "etf_values, time_values, expected",
    [
        # Test compositing/mosaicing between two images on the same day
        #     and in the same path, but different rows.
        # LC80330332015227LGN00 -> 1439660244726
        # LC80330342015227LGN00 -> 1439660268614
        [[10.0, 20.0], [1439660244726, 1439660268614], 15.0],
        [[10.0, 20.0], [1439660268614, 1439660244726], 15.0],
        [[20.0, 10.0], [1439660244726, 1439660268614], 15.0],
        [[None, 20.0], [1439660244726, 1439660268614], 20.0],
        [[10.0, None], [1439660244726, 1439660268614], 10.0],
    ]
)
def test_aggregate_daily_values_single_band(etf_values, time_values, expected,
                                            tol=0.01):
    """Test daily aggregation function for single-band constant images"""
    image_list = []
    time_list = []
    for etf, time in zip(etf_values, time_values):
        date_0utc = utils.date_0utc(ee.Date(time))
        time_0utc = date_0utc.millis()
        if etf is not None:
            image = ee.Image.constant([etf, time_0utc]).double()\
                .rename(['etf', 'time'])\
                .set({
                    'system:index': ee.Date(time).format('yyyyMMdd'),
                    'system:time_start': time})
        else:
            image = ee.Image.constant(1).double().updateMask(0)\
                .addBands(ee.Image.constant(time_0utc).double())\
                .rename(['etf', 'time'])\
                .set({
                    'system:index': ee.Date(time).format('yyyyMMdd'),
                    'system:time_start': time})
        image_list.append(image)
        time_list.append(time_0utc.getInfo())

    # Dates can be ISO Date string or milliseconds since epoch
    # Use the date strings to get 0 UTC dates and better match model calls
    start_date = ee.Date(min(time_values)).format('yyyy-MM-dd')
    end_date = ee.Date(max(time_values)).advance(1, 'day').format('yyyy-MM-dd')
    # start_date = min(time_values)
    # end_date = max(time_values)

    etf_coll = interp.aggregate_daily(
        ee.ImageCollection.fromImages(image_list),
        start_date, end_date, agg_type='mean')
    etf_image = ee.Image(etf_coll.first())

    output = utils.constant_image_value(etf_image)
    assert abs(output['etf'] - expected) <= tol
    assert output['time'] == 0.5 * sum(time_list)


@pytest.mark.parametrize(
    "src_values, time_values, expected",
    [
        # Test compositing/mosaicing between two images on the same day
        #     and in the same path, but different rows.
        # LC80330332015227LGN00 -> 1439660244726
        # LC80330342015227LGN00 -> 1439660268614
        [[[10, 20], [20, 30]], [1439660244726, 1439660268614], [15.0, 25.0]],
    ]
)
def test_aggregate_daily_values_multi_band(src_values, time_values, expected,
                                           tol=0.01):
    """Test daily aggregation function for multi-band constant images"""
    image_list = []
    time_list = []
    for src, time in zip(src_values, time_values):
        time_0utc = utils.date_0utc(ee.Date(time)).millis()
        image = ee.Image.constant(src + [time_0utc])\
            .rename(['etrf', 'etof', 'time']).double()\
            .set({
                'system:index': ee.Date(time).format('yyyyMMdd'),
                'system:time_start': time})
        image_list.append(image)
        time_list.append(time_0utc.getInfo())

    # Dates can be ISO Date string or milliseconds since epoch
    # Use the date strings to get 0 UTC dates and better match model calls
    start_date = ee.Date(min(time_values)).format('yyyy-MM-dd')
    end_date = ee.Date(max(time_values)).advance(1, 'day').format(
        'yyyy-MM-dd')
    # start_date = min(time_values)
    # end_date = max(time_values)

    output_coll = interp.aggregate_daily(
        ee.ImageCollection.fromImages(image_list),
        start_date, end_date, agg_type='mean')
    output_image = ee.Image(output_coll.first())\
        .select([0, 1, 2], ['etrf', 'etof', 'time'])

    output = utils.constant_image_value(output_image)
    assert abs(output['etrf'] - expected[0]) <= tol
    assert abs(output['etof'] - expected[1]) <= tol
    assert output['time'] == 0.5 * sum(time_list)


def test_aggregate_daily_properties():
    """Test daily aggregation image properties"""
    source_coll = ee.ImageCollection('LANDSAT/LC08/C01/T1_RT_TOA')\
        .filterDate('2017-06-30', '2017-08-02')\
        .filterBounds(ee.Geometry.Point(-121.9, 39))
    output = utils.getinfo(interp.aggregate_daily(source_coll).first())
    assert set(output['properties'].keys()) == set([
        'DATE', 'system:index', 'system:time_start'])
    assert output['properties']['DATE'] == '2017-06-30'


def test_aggregate_daily_date_filtering():
    """Test daily aggregation start/end date filtering"""
    source_coll = ee.ImageCollection('LANDSAT/LC08/C01/T1_RT_TOA')\
        .filterDate('2017-01-01', '2018-01-01')\
        .filterBounds(ee.Geometry.Point(-121.9, 39))\
        .select(['B1'])

    # First test if both start and end date are set
    output = utils.getinfo(interp.aggregate_daily(
        source_coll, '2017-06-30', '2017-08-02').aggregate_array('DATE'))
    assert min(output) == '2017-06-30'
    assert max(output) < '2017-08-02'

    # Then test if only start_date is set
    output = utils.getinfo(interp.aggregate_daily(
        source_coll, start_date='2017-06-30').aggregate_array('DATE'))
    assert min(output) == '2017-06-30'

    # Then test if only end_date is set
    output = utils.getinfo(interp.aggregate_daily(
        source_coll, end_date='2017-08-02').aggregate_array('DATE'))
    assert max(output) < '2017-08-02'


# def test_daily_values_collection_a():
#     """Test the daily interpolation using real images"""
#     target_coll = ee.ImageCollection('IDAHO_EPSCOR/GRIDMET')\
#         .filterDate('2017-06-30', '2017-08-02')\
#         .select(['etr'])
#     source_coll = ee.ImageCollection('LANDSAT/LC08/C01/T1_RT_TOA')\
#         .filterDate('2017-06-30', '2017-08-02')\
#         .filterBounds(ee.Geometry.Point(-121.9, 39))\
#         .select(['B1'])
#
#     def add_time_band(image):
#         date_0utc = utils.date_0utc(ee.Date(image.get('system:time_start')))
#         return image.addBands([
#             image.select([0]).double().multiply(0).add(date_0utc.millis())\
#                 .rename(['time'])])
#     source_coll = ee.ImageCollection(source_coll.map(add_time_band))
#
#     # print('\nTARGET')
#     # target_info = utils.point_coll_value(
#     #     target_coll, xy=(-121.5265, 38.7399), scale=30)
#     # pprint.pprint(target_info)
#
#     print('\nSOURCE')
#     source_info = utils.point_coll_value(
#         source_coll, xy=(-121.5265, 38.7399), scale=30)
#     pprint.pprint(source_info)
#
#     print('\nOUTPUT')
#     output = utils.point_coll_value(
#         interp.daily(target_coll, source_coll, interp_days=32),
#         xy=(-121.5265, 38.7399), scale=30)
#     pprint.pprint(output['B1'])
#
#     assert True
#
#
# def test_daily_values_collection_b():
#     """Test the daily interpolation for short interp_days values"""
#     target_coll = ee.ImageCollection('IDAHO_EPSCOR/GRIDMET')\
#         .filterDate('2017-06-30', '2017-08-02')\
#         .select(['etr'])
#     source_coll = ee.ImageCollection('LANDSAT/LC08/C01/T1_RT_TOA')\
#         .filterDate('2017-06-30', '2017-08-02')\
#         .filterBounds(ee.Geometry.Point(-121.9, 39))\
#         .select(['B1'])
#
#     def add_time_band(image):
#         date_0utc = utils.date_0utc(ee.Date(image.get('system:time_start')))
#         return image.addBands([
#             image.select([0]).double().multiply(0).add(date_0utc.millis())\
#                 .rename(['time'])])
#     source_coll = ee.ImageCollection(source_coll.map(add_time_band))
#
#     # print('\nTARGET')
#     # target_info = utils.point_coll_value(
#     #     target_coll, xy=(-121.5265, 38.7399), scale=30)
#     # pprint.pprint(target_info)
#
#     print('\nSOURCE')
#     source_info = utils.point_coll_value(
#         source_coll, xy=(-121.5265, 38.7399), scale=30)
#     pprint.pprint(source_info)
#
#     print('\nOUTPUT')
#     output = utils.point_coll_value(
#         interp.daily(target_coll, source_coll, interp_days=4),
#         xy=(-121.5265, 38.7399), scale=30)
#     pprint.pprint(output['B1'])
#
#     assert True
#
#
# def test_daily_values_collection_c():
#     """Test if the daily interpolation holds the last known value"""
#     target_coll = ee.ImageCollection('IDAHO_EPSCOR/GRIDMET')\
#         .filterDate('2017-07-01', '2017-08-05')\
#         .select(['etr'])
#     source_coll = ee.ImageCollection('LANDSAT/LC08/C01/T1_RT_TOA')\
#         .filterDate('2017-06-30', '2017-07-17')\
#         .filterBounds(ee.Geometry.Point(-121.9, 39))\
#         .select(['B1'])
#
#     def add_time_band(image):
#         date_0utc = utils.date_0utc(ee.Date(image.get('system:time_start')))
#         return image.addBands([
#             image.select([0]).double().multiply(0).add(date_0utc.millis())\
#                 .rename(['time'])])
#     source_coll = ee.ImageCollection(source_coll.map(add_time_band))
#
#     # print('\nTARGET')
#     # target_info = utils.point_coll_value(
#     #     target_coll, xy=(-121.5265, 38.7399), scale=30)
#     # pprint.pprint(target_info)
#
#     print('\nSOURCE')
#     source_info = utils.point_coll_value(
#         source_coll, xy=(-121.5265, 38.7399), scale=30)
#     pprint.pprint(source_info)
#
#     print('\nOUTPUT')
#     output = utils.point_coll_value(
#         interp.daily(target_coll, source_coll, interp_days=16),
#         xy=(-121.5265, 38.7399), scale=30)
#     pprint.pprint(output['B1'])
#
#     assert True