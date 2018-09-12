# import calendar
import datetime
import logging

import ee
import pytest

import openet.interp as interp

# import openet.common as common
# import openet.interpolate as interpolate

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

    "etr_value,etr_time,etf_values,etf_times,expected",
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
        ]
    ]
)
def test_linear_et_func(etr_value, etr_time, etf_values, etf_times, expected,
                        tol=0.01):
    """"""
    logging.debug('Testing linear interpolator function using constant image')

    logging.debug('  ETr: {}'.format(etr_value))
    logging.debug('  ETr times: {}'.format(etr_time))
    logging.debug('  ETf: {}'.format(etf_values))
    logging.debug('  ETf times: {}'.format(etf_times))
    logging.debug('  Output: {}'.format(expected))

    # Compute 0 UTC ETr time_start
    etr_time_0utc = interp.millis(
        datetime.datetime.utcfromtimestamp(etr_time / 1000).date())
    logging.debug('  ETr time: {}'.format(etr_time_0utc))

    # Shift ETf time stamps to 0 UTC
    etf_times = [
        interp.millis(datetime.datetime.utcfromtimestamp(t / 1000).date())
        for t in etf_times]
    logging.debug('  ETf times: {}'.format(etf_times))

    etr = ee.Image.constant(etr_value).select([0], ['et_reference']) \
        .setMulti({'system:time_start': etr_time})

    etf_prev = []
    etf_next = []
    for etf_t, etf_v in sorted(zip(etf_times, etf_values)):
        print(etf_t, etf_v)
        if etf_t <= etr_time:
            etf_prev.append([etf_v, etf_t])
        else:
            etf_next.append([etf_v, etf_t])
    # Need filler values if there aren't any values/times
    if not etf_prev:
        etf_prev.append([None, 1])
    if not etf_next:
        etf_next.append([None, 1])

    # Mosaic grabs the last image in the join, so reverse sort the
    #   next images so that the closest image in time is last
    etf_next = etf_next[::-1]

    prev_images = ee.List([
        ee.Image([
            ee.Image.constant(etf_v).double(),
            ee.Image.constant(etf_t).double()
        ]).select([0, 1], ['etf', 'time'])
        if etf_v is not None else
        ee.Image([
            ee.Image.constant(1).double(),
            ee.Image.constant(etf_t).double()
        ]).select([0, 1], ['etf', 'time']).updateMask(0)
        for etf_v, etf_t in etf_prev])
    next_images = ee.List([
        ee.Image([
            ee.Image.constant(etf_v).double(),
            ee.Image.constant(etf_t).double()
        ]).select([0, 1], ['etf', 'time'])
        if etf_v is not None else
        ee.Image([
            ee.Image.constant(1).double(),
            ee.Image.constant(etf_t).double()
        ]).select([0, 1], ['etf', 'time']).updateMask(0)
        for etf_v, etf_t in etf_next])

    # "Join" etf images to reference ET image
    etr = etr.setMulti({'prev': prev_images, 'next': next_images})

    output = ee.Image(interp.linear_et(etr)).reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=ee.Geometry.Rectangle([0, 0, 10, 10], 'EPSG:32613', False),
        scale=1).getInfo()['et']
    # output = ee.ImageCollection([et]) \
    #     .getRegion(ee.Geometry.Point([0.5, 0.5]), 1).getInfo()[1][4]
    logging.debug('  Target values: {}'.format(expected))
    logging.debug('  Output values: {}'.format(output))
    assert abs(output - expected) <= tol


def test_interp_et_coll(tol=0.01):
    # For now, use one of the test cases from test_linear_et_func()
    etr_value = 10
    etr_time = 1440309600000  # 2015-08-23
    etf_values = [0.0, 1.6]
    etf_times = [1439660268614, 1441042674222]  # 2015-08-15, 2015-08-31
    expected = 8

    et_reference_coll = ee.ImageCollection([
        ee.Image.constant(etr_value) \
            .select([0], ['et_reference']) \
            .setMulti({
                'system:time_start': etr_time,
            })
        ])
    et_fraction_coll = ee.ImageCollection([
        ee.Image.constant(value).select([0], ['etf']) \
            .setMulti({
                'system:time_start': time,
                'SCENE_ID': 'test',
            })
        for time, value in zip(etf_times, etf_values)])

    eta_coll = ee.ImageCollection(interp.interpolate(
        et_reference_coll, et_fraction_coll, interp_days=64,
        interp_type='linear'))

    output = ee.Image(eta_coll.first()).reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=ee.Geometry.Rectangle([0, 0, 10, 10], 'EPSG:32613', False),
        scale=1).getInfo()['et']
    # output = ee.ImageCollection(eta_coll) \
    #     .getRegion(ee.Geometry.Point([0.5, 0.5]), 1).getInfo()[1][4]
    logging.debug('  Target values: {}'.format(expected))
    logging.debug('  Output values: {}'.format(output))
    assert abs(output - expected) <= tol


@pytest.mark.parametrize(
    #
    "etf_values,time_values,expected",
    [
        # Test compositing/mosaicing between two images on the same day
        #     and in the same path, but different rows.
        # LC80330332015227LGN00 -> 1439660244726
        # LC80330342015227LGN00 -> 1439660268614
        [[10.0, 20.0], [1439660244726, 1439660268614], 15.0],
        [[20.0, 10.0], [1439660268614, 1439660244726], 15.0],
        [[None, 20.0], [1439660244726, 1439660268614], 20.0],
        [[10.0, None], [1439660244726, 1439660268614], 10.0]
    ]
)
def test_aggregate_daily(etf_values, time_values, expected, tol=0.01):
    """"""
    logging.debug('Testing daily aggregation function using constant images')

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

    output = etf_image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=ee.Geometry.Rectangle([0, 0, 10, 10], 'EPSG:32613', False),
        scale=1).getInfo()['etf']

    # output = ee.ImageCollection([etf])\
    #     .getRegion(ee.Geometry.Point([0.5, 0.5]), 1).getInfo()[1][4]
    logging.debug('  Target values: {}'.format(expected))
    logging.debug('  Output values: {}'.format(output))
    assert abs(output - expected) <= tol


# @pytest.mark.parametrize(
#     #
#     "agg_type,values,expected",
#     [
#         ['count', [[1, 1]] * 12, [2.0] * 12],
#         ['count', [[1, 1]] * 5 + [[1]] + [[1, 1]] * 6, [2.0] * 5 + [1.0] + [2.0] * 6],
#         ['count', [[1, 1]] * 5 + [[None]] + [[1, 1]] * 6, [2.0] * 5 + [0.0] + [2.0] * 6]
#     ]
# )
# def test_aggregate_monthly(agg_type, values, expected):
#     """"""
#     logging.debug('Testing monthly aggregation function using constant images')
#
#     image_list = []
#     for month_i, month_values in enumerate(values):
#         for month_value in month_values:
#             if month_value is not None:
#                 image = ee.Image(ee.Image.constant(month_value).double()) \
#                     .setMulti({'MONTH': month_i + 1})
#             else:
#                 image = ee.Image(ee.Image.constant(1).double().updateMask(0)) \
#                     .setMulti({'MONTH': month_i + 1})
#             image_list.append(image)
#
#     image_coll = ee.ImageCollection.fromImages(image_list)
#     month_image = interp.aggregate_monthly(image_coll, agg_type)
#
#     output = month_image.reduceRegion(
#         reducer=ee.Reducer.mean(),
#         geometry=ee.Geometry.Rectangle([0, 0, 10, 10], 'EPSG:32613', False),
#         scale=1).getInfo()
#     output = [v for k, v in sorted(output.items())]
#
#     logging.debug('  Target values: {}'.format(expected))
#     logging.debug('  Output values: {}'.format(output))
#     assert output == expected
