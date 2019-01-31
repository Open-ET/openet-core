import datetime
import logging

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
        [10, 1439618400000, [0.0, 1.6], [1439660268614, 1441042674222], 0.0],
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
def test_linear_func(tgt_value, tgt_time, src_values, src_times, expected,
                     tol=0.01):
    """"""
    # Compute 0 UTC target time_start
    tgt_time_0utc = utils.millis(
        datetime.datetime.utcfromtimestamp(tgt_time / 1000).date())
    # logging.debug('  Target time:   {}'.format(tgt_time_0utc))

    # Shift source time stamps to 0 UTC
    src_times = [
        utils.millis(datetime.datetime.utcfromtimestamp(t / 1000).date())
        for t in src_times]
    # logging.debug('  Source times:  {}'.format(src_times))

    tgt_img = ee.Image.constant(tgt_value).select([0], ['tgt'])\
        .set({'system:time_start': tgt_time})

    src_prev = []
    src_next = []
    for src_t, src_v in sorted(zip(src_times, src_values)):
        if src_t <= tgt_time:
            src_prev.append([src_v, src_t])
        else:
            src_next.append([src_v, src_t])
    # Need filler values if there aren't any values/times
    if not src_prev:
        src_prev.append([None, 1])
    if not src_next:
        src_next.append([None, 1])

    # Mosaic grabs the last image in the join, so reverse sort the
    #   next images so that the closest image in time is last
    src_next = src_next[::-1]

    prev_images = ee.List([
        ee.Image([
            ee.Image.constant(src_v).double(),
            ee.Image.constant(src_t).double()
        ]).select([0, 1], ['src', 'time'])
        if src_v is not None else
        ee.Image([
            ee.Image.constant(1).double(),
            ee.Image.constant(src_t).double()
        ]).select([0, 1], ['src', 'time']).updateMask(0)
        for src_v, src_t in src_prev])
    next_images = ee.List([
        ee.Image([
            ee.Image.constant(src_v).double(),
            ee.Image.constant(src_t).double()
        ]).select([0, 1], ['src', 'time'])
        if src_v is not None else
        ee.Image([
            ee.Image.constant(1).double(),
            ee.Image.constant(src_t).double()
        ]).select([0, 1], ['src', 'time']).updateMask(0)
        for src_v, src_t in src_next])

    # "Join" source images to target image
    tgt_img = tgt_img.set({'prev': prev_images, 'next': next_images})

    output_img = ee.Image(interp._linear(tgt_img))
    output = utils.constant_image_value(output_img)
    assert abs(output['src'] - expected) <= tol
    assert abs(output['tgt'] - tgt_value) <= tol


@pytest.mark.parametrize(
    "tgt_value, tgt_time, src_prev, src_next, src_times, expected",
    [
        [10, 1439704800000, [0.0, 0.0], [1.6, 2.0],
         [1439660268614, 1441042674222], [0.1, 0.125]],
        [10, 1440309600000, [0.0, 0.0], [1.6, 2.0],
         [1439660268614, 1441042674222], [0.8, 1.0]],
    ]
)
def test_linear_multiband(tgt_value, tgt_time, src_prev, src_next, src_times,
                          expected,tol=0.01):
    """"""

    # Compute 0 UTC target time_start
    tgt_time_0utc = utils.millis(
        datetime.datetime.utcfromtimestamp(tgt_time / 1000).date())
    # logging.debug('  Target time:   {}'.format(tgt_time_0utc))

    # Shift source time stamps to 0 UTC
    src_times = [
        utils.millis(datetime.datetime.utcfromtimestamp(t / 1000).date())
        for t in src_times]

    tgt_img = ee.Image.constant(tgt_value)\
        .select([0], ['etr'])\
        .set({'system:time_start': tgt_time})

    prev_images = ee.List([
        ee.Image([
            ee.Image.constant(src_prev[0]).double(),
            ee.Image.constant(src_prev[1]).double(),
            ee.Image.constant(src_times[0]).double()
        ]).rename(['etrf', 'etof', 'time'])])
    next_images = ee.List([
        ee.Image([
            ee.Image.constant(src_next[0]).double(),
            ee.Image.constant(src_next[1]).double(),
            ee.Image.constant(src_times[1]).double()
        ]).rename(['etrf', 'etof', 'time'])])

    # "Join" source images to target image
    tgt_img = tgt_img.set({'prev': prev_images, 'next': next_images})

    output = utils.constant_image_value(ee.Image(interp._linear(tgt_img)))
    assert abs(output['etrf'] - expected[0]) <= tol
    assert abs(output['etof'] - expected[1]) <= tol


def test_daily_coll(tol=0.01):
    # For now, use one of the test cases from test_linear_func()
    tgt_value = 10
    tgt_time = 1440309600000  # 2015-08-23
    src_values = [0.0, 1.6]
    src_times = [1439660268614, 1441042674222]  # 2015-08-15, 2015-08-31
    expected = 0.8

    tgt_coll = ee.ImageCollection([
        ee.Image.constant(tgt_value)\
            .select([0], ['tgt'])\
            .set({
                'system:time_start': tgt_time,
            })
        ])
    src_coll = ee.ImageCollection([
        ee.Image.constant(value).select([0], ['src'])\
            .set({
                'system:time_start': time,
                'SCENE_ID': 'test',
            })
        for time, value in zip(src_times, src_values)])

    output_coll = ee.ImageCollection(interp.daily(
        tgt_coll, src_coll, interp_days=64, interp_method='linear'))

    output = utils.constant_image_value(ee.Image(output_coll.first()))
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
        [[20.0, 10.0], [1439660268614, 1439660244726], 15.0],
        [[None, 20.0], [1439660244726, 1439660268614], 20.0],
        [[10.0, None], [1439660244726, 1439660268614], 10.0],
    ]
)
def test_aggregate_daily(etf_values, time_values, expected, tol=0.01):
    # logging.debug('Testing daily aggregation function using constant images')
    image_list = []
    for etf, time in zip(etf_values, time_values):
        if etf is not None:
            image = ee.Image.constant(etf).double().set({
                    'system:index': ee.Date(time).format('yyyyMMdd'),
                    'system:time_start': time,
            })
        else:
            image = ee.Image.constant(1).double().updateMask(0).set({
                    'system:index': ee.Date(time).format('yyyyMMdd'),
                    'system:time_start': time,
                })
        image_list.append(image)

    # Dates can be ISO Date string or milliseconds since epoch
    start_date = min(time_values)
    end_date = max(time_values)
    # start_date = ee.Date(min(time_values)).format('yyyy-MM-dd')
    # end_date = ee.Date(max(time_values)).format('yyyy-MM-dd')

    etf_coll = interp.aggregate_daily(
        ee.ImageCollection.fromImages(image_list),
        start_date, end_date, agg_type='mean')
    etf_image = ee.Image(etf_coll.first()).select([0], ['etf'])

    output = utils.constant_image_value(etf_image)
    print(output)
    assert abs(output['etf'] - expected) <= tol


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
def test_aggregate_daily_multiband(src_values, time_values, expected, tol=0.01):
    # logging.debug('Testing daily aggregation function using constant images')
    image_list = []
    for src, time in zip(src_values, time_values):
        image = ee.Image.constant(src).double().set({
                'system:index': ee.Date(time).format('yyyyMMdd'),
                'system:time_start': time,
        })
        image_list.append(image)

    # Dates can be ISO Date string or milliseconds since epoch
    start_date = min(time_values)
    end_date = max(time_values)
    # start_date = ee.Date(min(time_values)).format('yyyy-MM-dd')
    # end_date = ee.Date(max(time_values)).format('yyyy-MM-dd')

    output_coll = interp.aggregate_daily(
        ee.ImageCollection.fromImages(image_list),
        start_date, end_date, agg_type='mean')
    output_image = ee.Image(output_coll.first())\
        .select([0, 1], ['etrf', 'etof'])

    output = utils.constant_image_value(output_image)
    assert abs(output['etrf'] - expected[0]) <= tol
    assert abs(output['etof'] - expected[1]) <= tol
