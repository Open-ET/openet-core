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
        [10, 1439704800000, [0.0, 1.6], [1439660268614, 1441042674222], 1.0],
        [10, 1440309600000, [0.0, 1.6], [1439660268614, 1441042674222], 8.0],
        # This fails?
        [10, 1441000800000, [0.0, 1.6], [1439660268614, 1441042674222], 16.0],

        # Test if one side of the range is totally nodata
        [10, 1439704800000, [0.0, None], [1439660268614, 1441042674222], 0.0],
        [10, 1439704800000, [None, 1.6], [1439660268614, 1441042674222], 16.0],

        # Test with multiple dates
        [10, 1439704800000, [0.0, 1.6, 3.2, 4.8],
         [1438277862725, 1439660268614, 1441042674222, 1442425082323], 17.0],
        [10, 1439704800000, [0.0, None, 3.2, 4.8],
         [1438277862725, 1439660268614, 1441042674222, 1442425082323], 17.0],
        [10, 1439704800000, [0.0, 1.6, None, 4.8],
         [1438277862725, 1439660268614, 1441042674222, 1442425082323], 17.0],

        # Test with real data
        [
            4.8153934,
            # 4/10/2015
            1428645600000,
            [0.0, 0.0, 0.0, 0.329212732, 0.124609835, 0.268005646],
            # 2/14/2015, 3/10/2015, 3/26/2015, 4/11/2015, 5/29/2015, 6/6/2015
            [1423872000000, 1425945600000, 1427328000000, 1428710400000, 1432857600000, 1433548800000],
            0.308636806 * 4.8153934
        ],
    ]
)
def test_linear_func(tgt_value, tgt_time, src_values, src_times, expected,
                     tol=0.01):
    """"""
    # logging.debug('Testing linear interpolator function using constant image')
    # logging.debug('  Target value:  {}'.format(tgt_value))
    # logging.debug('  Target times:  {}'.format(tgt_time))
    # logging.debug('  Source values: {}'.format(src_values))
    # logging.debug('  Source times:  {}'.format(src_times))
    # logging.debug('  Output:        {}'.format(expected))

    # Compute 0 UTC target time_start
    tgt_time_0utc = utils.millis(
        datetime.datetime.utcfromtimestamp(tgt_time / 1000).date())
    # logging.debug('  Target time:   {}'.format(tgt_time_0utc))

    # Shift source time stamps to 0 UTC
    src_times = [
        utils.millis(datetime.datetime.utcfromtimestamp(t / 1000).date())
        for t in src_times]
    # logging.debug('  Source times:  {}'.format(src_times))

    tgt_img = ee.Image.constant(tgt_value).select([0], ['et_reference']) \
        .setMulti({'system:time_start': tgt_time})

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
    tgt_img = tgt_img.setMulti({'prev': prev_images, 'next': next_images})

    output = utils.constant_image_value(ee.Image(interp._linear(tgt_img)))
    # logging.debug('  Target values: {}'.format(expected))
    # logging.debug('  Output values: {}'.format(output))
    assert abs(output - expected) <= tol


def test_daily_coll(tol=0.01):
    # For now, use one of the test cases from test_linear_func()
    tgt_value = 10
    tgt_time = 1440309600000  # 2015-08-23
    src_values = [0.0, 1.6]
    src_times = [1439660268614, 1441042674222]  # 2015-08-15, 2015-08-31
    expected = 8

    tgt_coll = ee.ImageCollection([
        ee.Image.constant(tgt_value) \
            .select([0]) \
            .setMulti({
                'system:time_start': tgt_time,
            })
        ])
    src_coll = ee.ImageCollection([
        ee.Image.constant(value).select([0]) \
            .setMulti({
                'system:time_start': time,
                'SCENE_ID': 'test',
            })
        for time, value in zip(src_times, src_values)])

    output_coll = ee.ImageCollection(interp.daily(
        tgt_coll, src_coll, interp_days=64, interp_method='linear'))

    output = utils.constant_image_value(ee.Image(output_coll.first()))
    # logging.debug('  Target values: {}'.format(expected))
    # logging.debug('  Output values: {}'.format(output))
    assert abs(output - expected) <= tol


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
            image = ee.Image(
                ee.Image.constant(etf).double().setMulti({
                    'system:index': ee.Date(time).format('yyyyMMdd'),
                    'system:time_start': time,
            }))
        else:
            image = ee.Image(
                ee.Image.constant(1).double().updateMask(0).setMulti({
                    'system:index': ee.Date(time).format('yyyyMMdd'),
                    'system:time_start': time,
                }))
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
    # logging.debug('  Target values: {}'.format(expected))
    # logging.debug('  Output values: {}'.format(output))
    assert abs(output - expected) <= tol
