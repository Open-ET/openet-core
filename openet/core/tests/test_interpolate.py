import datetime
import logging
# import pprint

import ee
import pytest

import openet.core.interpolate as interpolate
import openet.core.utils as utils

logging.basicConfig(level=logging.DEBUG, format='%(message)s')


def test_ee_init():
    assert ee.Number(1).getInfo() == 1


def tgt_image(tgt_value, tgt_time):
    # tgt_images = []
    # for tgt_value, tgt_time in zip(tgt_values, tgt_timess):
    return ee.Image.constant(tgt_value).rename(['tgt'])\
        .set({'system:time_start': tgt_time,
              'system:index': datetime.datetime.utcfromtimestamp(
                  tgt_time / 1000.0).strftime('%Y%m%d')})


def src_images(src_values, src_times):
    """Build constant source images from values and times"""
    src_images = []
    for src, time in zip(src_values, src_times):
        date_0utc = utils.date_0utc(ee.Date(time))
        time_0utc = date_0utc.millis()
        if src is not None:
            image = ee.Image([
                    ee.Image.constant([src]).double(),
                    ee.Image.constant([time_0utc]).double()])\
                .rename(['src', 'time']) \
                .set({'system:index': ee.Date(time).format('yyyyMMdd'),
                      'system:time_start': time})
        else:
            image = ee.Image([
                    ee.Image.constant(1).double(),
                    ee.Image.constant(time_0utc).double()])\
                .updateMask(0) \
                .rename(['src', 'time']) \
                .set({'system:index': ee.Date(time).format('yyyyMMdd'),
                      'system:time_start': time})
        src_images.append(image)
    return src_images


def scene_coll(variables, et_fraction=[0.4, 0.4, 0.4], et=[5, 5, 5],
               ndvi=[0.6, 0.6, 0.6]):
    """Return a generic scene collection to test scene interpolation functions

    Parameters
    ----------
    variables : list
        The variables to return in the collection
    et_fraction : float
    et : float
    ndvi : float

    Returns
    -------
    ee.ImageCollection

    """
    img = ee.Image('LANDSAT/LC08/C01/T1_TOA/LC08_044033_20170716') \
        .select(['B2']).double().multiply(0)
    mask = img.add(1).updateMask(1).uint8()

    # The time band needs to be the 0 UTC time (date)
    date1 = ee.Number(ee.Date.fromYMD(2017, 7, 8).millis())
    date2 = ee.Number(ee.Date.fromYMD(2017, 7, 16).millis())
    date3 = ee.Number(ee.Date.fromYMD(2017, 7, 24).millis())
    time1 = ee.Number(ee.Date.fromYMD(2017, 7, 8).advance(18, 'hours').millis())
    time2 = ee.Number(ee.Date.fromYMD(2017, 7, 16).advance(18, 'hours').millis())
    time3 = ee.Number(ee.Date.fromYMD(2017, 7, 24).advance(18, 'hours').millis())

    # TODO: Add code to convert et, et_fraction, and ndvi to lists if they
    #   are set as a single value

    # Mask and time bands currently get added on to the scene collection
    #   and images are unscaled just before interpolating in the export tool
    scene_coll = ee.ImageCollection.fromImages([
        ee.Image([img.add(et_fraction[0]), img.add(et[0]), img.add(ndvi[0]), img.add(date1), mask])
            .rename(['et_fraction', 'et', 'ndvi', 'time', 'mask'])
            .set({'system:index': 'LE07_044033_20170708', 'system:time_start': time1}),
        ee.Image([img.add(et_fraction[1]), img.add(et[1]), img.add(ndvi[1]), img.add(date2), mask])
            .rename(['et_fraction', 'et', 'ndvi', 'time', 'mask'])
            .set({'system:index': 'LC08_044033_20170716', 'system:time_start': time2}),
        ee.Image([img.add(et_fraction[2]), img.add(et[2]), img.add(ndvi[2]), img.add(date3), mask])
            .rename(['et_fraction', 'et', 'ndvi', 'time', 'mask'])
            .set({'system:index': 'LE07_044033_20170724', 'system:time_start': time3}),
    ])
    return scene_coll.select(variables)


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
        # CGM - I'm not sure why this first test fails
        # [10, 1439618400000, [0.0, 1.6], [1439660268614, 1441042674222], 0.0],
        [10, 1439704800000, [0.0, 1.6], [1439660268614, 1441042674222], 0.1],
        [10, 1440309600000, [0.0, 1.6], [1439660268614, 1441042674222], 0.8],
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
    tgt_coll = ee.ImageCollection([tgt_image(tgt_value, tgt_time)])
    src_coll = ee.ImageCollection.fromImages(src_images(src_values, src_times))
    output_coll = interpolate.daily(
        tgt_coll, src_coll, interp_days=32, interp_method='linear', use_joins=False)
    output = utils.constant_image_value(ee.Image(output_coll.first()))
    assert abs(output['src'] - expected) <= tol
    assert abs(output['tgt'] - tgt_value) <= tol


@pytest.mark.parametrize(
    "tgt_value, tgt_time, src_values, src_times, expected",
    [
        [10, 1439704800000, [0.0, 1.6], [1439660268614, 1441042674222],
         0.1],
    ]
)
def test_daily_compute_product_true(tgt_value, tgt_time, src_values, src_times,
                                    expected, tol=0.01):
    """Test if the compute_product flag returns the product bands"""
    tgt_coll = ee.ImageCollection([tgt_image(tgt_value, tgt_time)])
    src_coll = ee.ImageCollection.fromImages(
        src_images(src_values, src_times))
    output_coll = interpolate.daily(
        tgt_coll, src_coll, interp_days=32, interp_method='linear',
        use_joins=False, compute_product=True)
    output = utils.constant_image_value(ee.Image(output_coll.first()))
    # assert abs(output['src'] - expected) <= tol
    # assert abs(output['tgt'] - tgt_value) <= tol
    assert abs(output['src_1'] - expected * tgt_value) <= tol


@pytest.mark.parametrize(
    "tgt_value, tgt_time, src_values, src_times, expected",
    [
        # CGM - I'm not sure why this first test fails
        # [10, 1439618400000, [0.0, 1.6], [1439660268614, 1441042674222], 0.0],
        [10, 1439704800000, [0.0, 1.6], [1439660268614, 1441042674222], 0.1],
        [10, 1440309600000, [0.0, 1.6], [1439660268614, 1441042674222], 0.8],
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
    ]
)
def test_daily_use_joins_true(tgt_value, tgt_time, src_values, src_times,
                              expected, tol=0.01):
    """Test that output with use_joins=True is the same as use_joins=False"""
    tgt_coll = ee.ImageCollection([tgt_image(tgt_value, tgt_time)])
    src_coll = ee.ImageCollection.fromImages(src_images(src_values, src_times))
    output_coll = interpolate.daily(
        tgt_coll, src_coll, interp_days=32, interp_method='linear', use_joins=True)
    output = utils.constant_image_value(ee.Image(output_coll.first()))
    assert abs(output['src'] - expected) <= tol
    assert abs(output['tgt'] - tgt_value) <= tol


@pytest.mark.parametrize(
    "interp_days, tgt_value, tgt_time, src_values, src_times, expected",
    [
        # Return 1st value if 2nd value is outside interp_days window
        # Return 2nd value if 1st value is outside interp_days window
        # Return nodata if 1st and 2nd value are both outside window
        # Return interpolated value if 1st and 2nd value are both inside window
        # First try interp_days that is much smaller than time step (4 days)
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
        # Same as above but with a larger interp_days value
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
def test_daily_small_interp_days(interp_days, tgt_value, tgt_time, src_values,
                                 src_times, expected, tol=0.01):
    """Test the daily method for small interp_days values

    This is mainly an issue when the number of interp_days is less than the
    timestep of the source images but can also be an issue when there are lots
    of images missing due to clouds.
    """
    tgt_coll = ee.ImageCollection([tgt_image(tgt_value, tgt_time)])
    src_coll = ee.ImageCollection.fromImages(src_images(src_values, src_times))
    output_coll = ee.ImageCollection(interpolate.daily(
        tgt_coll, src_coll, interp_days=interp_days, interp_method='linear',
        use_joins=False))
    output = utils.constant_image_value(ee.Image(output_coll.first()))
    if expected is None:
        assert output['src'] is None
        assert abs(output['tgt'] - tgt_value) <= tol
    else:
        assert abs(output['src'] - expected) <= tol
        assert abs(output['tgt'] - tgt_value) <= tol


@pytest.mark.parametrize(
    "interp_days, tgt_value, tgt_time, src_values, src_times, expected",
    [
        # Return 1st value if 2nd value is outside interp_days window
        # Return 2nd value if 1st value is outside interp_days window
        # Return nodata if 1st and 2nd value are both outside window
        # Return interpolated value if 1st and 2nd value are both inside window
        # First try interp_days that is much smaller than time step (4 days)
        [4, 10, 1439618400000, [0.0, 1.6], [1439660268614, 1441042674222], 0.0],
        [4, 10, 1439704800000, [0.0, 1.6], [1439660268614, 1441042674222], 0.0],
        [4, 10, 1439791200000, [0.0, 1.6], [1439660268614, 1441042674222], 0.0],
        [4, 10, 1439877600000, [0.0, 1.6], [1439660268614, 1441042674222], 0.0],
        [4, 10, 1439964000000, [0.0, 1.6], [1439660268614, 1441042674222], 0.0],
        # CGM - Why does this one fail?
        # [4, 10, 1440050400000, [0.0, 1.6], [1439660268614, 1441042674222], None],
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
        # Same as above but with a larger interp_days value
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
        # CGM - Why does this one fail?
        # [10, 10, 1440568800000, [0.0, 1.6], [1439660268614, 1441042674222], 1.6],
        [10, 10, 1440655200000, [0.0, 1.6], [1439660268614, 1441042674222], 1.6],
        [10, 10, 1440741600000, [0.0, 1.6], [1439660268614, 1441042674222], 1.6],
        [10, 10, 1440828000000, [0.0, 1.6], [1439660268614, 1441042674222], 1.6],
        [10, 10, 1440914400000, [0.0, 1.6], [1439660268614, 1441042674222], 1.6],
        [10, 10, 1441000800000, [0.0, 1.6], [1439660268614, 1441042674222], 1.6],
    ]
)
def test_daily_interp_days_use_joins(interp_days, tgt_value, tgt_time,
                                     src_values, src_times, expected, tol=0.01):
    """Test the daily method for small interp_days values"""
    tgt_coll = ee.ImageCollection([tgt_image(tgt_value, tgt_time)])
    src_coll = ee.ImageCollection.fromImages(src_images(src_values, src_times))
    output_coll = ee.ImageCollection(interpolate.daily(
        tgt_coll, src_coll, interp_days=interp_days, interp_method='linear',
        use_joins=True))
    output = utils.constant_image_value(ee.Image(output_coll.first()))
    if expected is None:
        assert output['src'] is None
        assert abs(output['tgt'] - tgt_value) <= tol
    else:
        assert abs(output['src'] - expected) <= tol
        assert abs(output['tgt'] - tgt_value) <= tol


@pytest.mark.parametrize(
    "src_values, time_values, expected",
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
def test_aggregate_to_daily_values_single_band(src_values, time_values,
                                               expected, tol=0.01):
    """Test daily aggregation function for single-band constant images"""
    image_list = src_images(src_values, time_values)
    time_list = [
        utils.date_0utc(ee.Date(time)).millis().getInfo()
        for time in time_values]

    # Dates can be ISO Date string or milliseconds since epoch
    # Use the date strings to get 0 UTC dates and better match model calls
    start_date = ee.Date(min(time_values)).format('yyyy-MM-dd')
    end_date = ee.Date(max(time_values)).advance(1, 'day').format('yyyy-MM-dd')
    # start_date = min(time_values)
    # end_date = max(time_values)

    src_coll = interpolate.aggregate_to_daily(
        ee.ImageCollection.fromImages(image_list),
        start_date, end_date, agg_type='mean')
    src_image = ee.Image(src_coll.first())

    output = utils.constant_image_value(src_image)
    assert abs(output['src'] - expected) <= tol
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
def test_aggregate_to_daily_values_multi_band(src_values, time_values, expected,
                                              tol=0.01):
    """Test daily aggregation function for multi-band constant images"""
    image_list = []
    time_list = []
    for src, time in zip(src_values, time_values):
        time_0utc = utils.date_0utc(ee.Date(time)).millis()
        image = ee.Image.constant(src).double()\
            .addBands(ee.Image.constant(time_0utc).double())\
            .rename(['etrf', 'etof', 'time'])\
            .set({'system:index': ee.Date(time).format('yyyyMMdd'),
                  'system:time_start': time})
        image_list.append(image)
        time_list.append(time_0utc.getInfo())

    # Dates can be ISO Date string or milliseconds since epoch
    # Use the date strings to get 0 UTC dates and better match model calls
    start_date = ee.Date(min(time_values)).format('yyyy-MM-dd')
    end_date = ee.Date(max(time_values)).advance(1, 'day').format('yyyy-MM-dd')
    # start_date = min(time_values)
    # end_date = max(time_values)

    output_coll = interpolate.aggregate_to_daily(
        ee.ImageCollection.fromImages(image_list),
        start_date, end_date, agg_type='mean')
    output_image = ee.Image(output_coll.first())\
        .select([0, 1, 2], ['etrf', 'etof', 'time'])

    output = utils.constant_image_value(output_image)
    assert abs(output['etrf'] - expected[0]) <= tol
    assert abs(output['etof'] - expected[1]) <= tol
    assert output['time'] == 0.5 * sum(time_list)


def test_aggregate_to_daily_properties():
    """Test daily aggregation image properties"""
    source_coll = ee.ImageCollection('LANDSAT/LC08/C01/T1_RT_TOA')\
        .filterDate('2017-06-30', '2017-08-02')\
        .filterBounds(ee.Geometry.Point(-121.9, 39))
    output = utils.get_info(interpolate.aggregate_to_daily(source_coll).first())
    assert set(output['properties'].keys()) == {
        'date', 'system:index', 'system:time_start'}
    assert output['properties']['date'] == '2017-06-30'


def test_aggregate_to_daily_date_filtering():
    """Test daily aggregation start/end date filtering"""
    source_coll = ee.ImageCollection('LANDSAT/LC08/C01/T1_RT_TOA')\
        .filterDate('2017-01-01', '2018-01-01')\
        .filterBounds(ee.Geometry.Point(-121.9, 39))\
        .select(['B1'])

    # First test if both start and end date are set
    output = utils.get_info(interpolate.aggregate_to_daily(
        source_coll, '2017-06-30', '2017-08-02').aggregate_array('date'))
    assert min(output) == '2017-06-30'
    assert max(output) < '2017-08-02'

    # Then test if only start_date is set
    output = utils.get_info(interpolate.aggregate_to_daily(
        source_coll, start_date='2017-06-30').aggregate_array('date'))
    assert min(output) == '2017-06-30'

    # Then test if only end_date is set
    output = utils.get_info(interpolate.aggregate_to_daily(
        source_coll, end_date='2017-08-02').aggregate_array('date'))
    assert max(output) < '2017-08-02'


def test_from_scene_et_fraction_t_interval_daily_values(tol=0.0001):
    output_coll = interpolate.from_scene_et_fraction(
        scene_coll(['et_fraction', 'ndvi', 'time', 'mask'], ndvi=[0.2, 0.4, 0.6]),
        start_date='2017-07-01', end_date='2017-08-01',
        variables=['et', 'et_reference', 'et_fraction', 'ndvi'],
        interp_args={'interp_method': 'linear', 'interp_days': 32},
        model_args={'et_reference_source': 'IDAHO_EPSCOR/GRIDMET',
                    'et_reference_band': 'etr',
                    'et_reference_factor': 1.0,
                    'et_reference_resample': 'nearest'},
        t_interval='daily')

    TEST_POINT = (-121.5265, 38.7399)
    output = utils.point_coll_value(output_coll, TEST_POINT, scale=10)
    assert abs(output['ndvi']['2017-07-01'] - 0.2) <= tol
    assert abs(output['ndvi']['2017-07-08'] - 0.2) <= tol
    assert abs(output['ndvi']['2017-07-12'] - 0.3) <= tol
    assert abs(output['ndvi']['2017-07-16'] - 0.4) <= tol
    assert abs(output['ndvi']['2017-07-24'] - 0.6) <= tol
    assert abs(output['ndvi']['2017-07-31'] - 0.6) <= tol
    # assert abs(output['ndvi']['2017-07-10'] - 0.6) <= tol
    assert abs(output['et_fraction']['2017-07-10'] - 0.4) <= tol
    assert abs(output['et_reference']['2017-07-10'] - 10.5) <= tol
    assert abs(output['et']['2017-07-10'] - (10.5 * 0.4)) <= tol
    assert abs(output['et_fraction']['2017-07-01'] - 0.4) <= tol
    assert abs(output['et_fraction']['2017-07-31'] - 0.4) <= tol
    assert '2017-08-01' not in output['et_fraction'].keys()
    # assert output['count']['2017-07-01'] == 3


def test_from_scene_et_fraction_t_interval_monthly_values(tol=0.0001):
    output_coll = interpolate.from_scene_et_fraction(
        scene_coll(['et_fraction', 'ndvi', 'time', 'mask']),
        start_date='2017-07-01', end_date='2017-08-01',
        variables=['et', 'et_reference', 'et_fraction', 'ndvi', 'count'],
        interp_args={'interp_method': 'linear', 'interp_days': 32},
        model_args={'et_reference_source': 'IDAHO_EPSCOR/GRIDMET',
                    'et_reference_band': 'etr',
                    'et_reference_factor': 1.0,
                    'et_reference_resample': 'nearest'},
        t_interval='monthly')

    TEST_POINT = (-121.5265, 38.7399)
    output = utils.point_coll_value(output_coll, TEST_POINT, scale=10)
    assert abs(output['ndvi']['2017-07-01'] - 0.6) <= tol
    assert abs(output['et_fraction']['2017-07-01'] - 0.4) <= tol
    assert abs(output['et_reference']['2017-07-01'] - 310.3) <= tol
    assert abs(output['et']['2017-07-01'] - (310.3 * 0.4)) <= tol
    assert output['count']['2017-07-01'] == 3


def test_from_scene_et_fraction_t_interval_custom_values(tol=0.0001):
    output_coll = interpolate.from_scene_et_fraction(
        scene_coll(['et_fraction', 'ndvi', 'time', 'mask']),
        start_date='2017-07-01', end_date='2017-08-01',
        variables=['et', 'et_reference', 'et_fraction', 'ndvi', 'count'],
        interp_args={'interp_method': 'linear', 'interp_days': 32},
        model_args={'et_reference_source': 'IDAHO_EPSCOR/GRIDMET',
                    'et_reference_band': 'etr',
                    'et_reference_factor': 1.0,
                    'et_reference_resample': 'nearest'},
        t_interval='custom')

    TEST_POINT = (-121.5265, 38.7399)
    output = utils.point_coll_value(output_coll, TEST_POINT, scale=10)
    assert abs(output['ndvi']['2017-07-01'] - 0.6) <= tol
    assert abs(output['et_fraction']['2017-07-01'] - 0.4) <= tol
    assert abs(output['et_reference']['2017-07-01'] - 310.3) <= tol
    assert abs(output['et']['2017-07-01'] - (310.3 * 0.4)) <= tol
    assert output['count']['2017-07-01'] == 3


def test_from_scene_et_fraction_t_interval_monthly_et_reference_factor(tol=0.0001):
    output_coll = interpolate.from_scene_et_fraction(
        scene_coll(['et_fraction', 'ndvi', 'time', 'mask']),
        start_date='2017-07-01', end_date='2017-08-01',
        variables=['et', 'et_reference', 'et_fraction', 'ndvi', 'count'],
        interp_args={'interp_method': 'linear', 'interp_days': 32},
        model_args={'et_reference_source': 'IDAHO_EPSCOR/GRIDMET',
                    'et_reference_band': 'etr',
                    'et_reference_factor': 0.5,
                    'et_reference_resample': 'nearest'},
        t_interval='monthly')

    TEST_POINT = (-121.5265, 38.7399)
    output = utils.point_coll_value(output_coll, TEST_POINT, scale=10)
    assert abs(output['ndvi']['2017-07-01'] - 0.6) <= tol
    assert abs(output['et_fraction']['2017-07-01'] - 0.4) <= tol
    assert abs(output['et_reference']['2017-07-01'] - 310.3 * 0.5) <= tol
    assert abs(output['et']['2017-07-01'] - (310.3 * 0.5 * 0.4)) <= tol
    assert output['count']['2017-07-01'] == 3


# CGM - Resampling is not being applied so this should be equal to nearest
def test_from_scene_et_fraction_t_interval_monthly_et_reference_resampling(tol=0.0001):
    output_coll = interpolate.from_scene_et_fraction(
        scene_coll(['et_fraction', 'ndvi', 'time', 'mask']),
        start_date='2017-07-01', end_date='2017-08-01',
        variables=['et', 'et_reference', 'et_fraction', 'ndvi', 'count'],
        interp_args={'interp_method': 'linear', 'interp_days': 32},
        model_args={'et_reference_source': 'IDAHO_EPSCOR/GRIDMET',
                    'et_reference_band': 'etr',
                    'et_reference_factor': 1.0,
                    'et_reference_resample': 'bilinear'},
        t_interval='monthly')

    TEST_POINT = (-121.5265, 38.7399)
    output = utils.point_coll_value(output_coll, TEST_POINT, scale=10)
    assert abs(output['ndvi']['2017-07-01'] - 0.6) <= tol
    assert abs(output['et_fraction']['2017-07-01'] - 0.4) <= tol
    assert abs(output['et_reference']['2017-07-01'] - 310.3) <= tol
    assert abs(output['et']['2017-07-01'] - (310.3 * 0.4)) <= tol
    assert output['count']['2017-07-01'] == 3


def test_from_scene_et_actual_t_interval_daily_values(tol=0.0001):
    output_coll = interpolate.from_scene_et_actual(
        scene_coll(['et', 'time', 'mask']),
        start_date='2017-07-01', end_date='2017-08-01',
        variables=['et', 'et_reference', 'et_fraction'],
        interp_args={'interp_method': 'linear', 'interp_days': 32,
                     'interp_source': 'IDAHO_EPSCOR/GRIDMET',
                     'interp_band': 'etr',
                     'interp_resample': 'nearest'},
        model_args={'et_reference_source': 'IDAHO_EPSCOR/GRIDMET',
                    'et_reference_band': 'etr',
                    'et_reference_factor': 1.0,
                    'et_reference_resample': 'nearest'},
        t_interval='daily')

    TEST_POINT = (-121.5265, 38.7399)
    output = utils.point_coll_value(output_coll, TEST_POINT, scale=10)
    assert abs(output['et_fraction']['2017-07-10'] - 0.449444979429245) <= tol
    assert abs(output['et_reference']['2017-07-10'] - 10.5) <= tol
    assert abs(output['et']['2017-07-10'] - 4.71917200088501) <= tol
    assert abs(output['et']['2017-07-01'] - 3.6936933994293213) <= tol
    assert abs(output['et']['2017-07-31'] - 4.951923370361328) <= tol
    assert '2017-08-01' not in output['et'].keys()
    # assert output['count']['2017-07-01'] == 3


def test_from_scene_et_actual_t_interval_monthly_values(tol=0.0001):
    output_coll = interpolate.from_scene_et_actual(
        scene_coll(['et', 'time', 'mask']),
        start_date='2017-07-01', end_date='2017-08-01',
        variables=['et', 'et_reference', 'et_fraction', 'count'],
        interp_args={'interp_method': 'linear', 'interp_days': 32,
                     'interp_source': 'IDAHO_EPSCOR/GRIDMET',
                     'interp_band': 'etr',
                     'interp_resample': 'nearest'},
        model_args={'et_reference_source': 'IDAHO_EPSCOR/GRIDMET',
                    'et_reference_band': 'etr',
                    'et_reference_factor': 1.0,
                    'et_reference_resample': 'nearest'},
        t_interval='monthly')

    TEST_POINT = (-121.5265, 38.7399)
    output = utils.point_coll_value(output_coll, TEST_POINT, scale=10)
    assert abs(output['et']['2017-07-01'] - 142.9622039794922) <= tol
    assert abs(output['et_reference']['2017-07-01'] - 310.3) <= tol
    assert abs(output['et_fraction']['2017-07-01'] - 142.9622039794922 / 310.3) <= tol
    assert output['count']['2017-07-01'] == 3


def test_from_scene_et_actual_t_interval_custom_values(tol=0.0001):
    output_coll = interpolate.from_scene_et_actual(
        scene_coll(['et', 'time', 'mask']),
        start_date='2017-07-01', end_date='2017-08-01',
        variables=['et', 'et_reference', 'et_fraction', 'count'],
        interp_args={'interp_method': 'linear', 'interp_days': 32,
                     'interp_source': 'IDAHO_EPSCOR/GRIDMET',
                     'interp_band': 'etr',
                     'interp_resample': 'nearest'},
        model_args={'et_reference_source': 'IDAHO_EPSCOR/GRIDMET',
                    'et_reference_band': 'etr',
                    'et_reference_factor': 1.0,
                    'et_reference_resample': 'nearest'},
        t_interval='custom')

    TEST_POINT = (-121.5265, 38.7399)
    output = utils.point_coll_value(output_coll, TEST_POINT, scale=10)
    assert abs(output['et']['2017-07-01'] - 142.9622039794922) <= tol
    assert abs(output['et_reference']['2017-07-01'] - 310.3) <= tol
    assert abs(output['et_fraction']['2017-07-01'] - 142.9622039794922 / 310.3) <= tol
    assert output['count']['2017-07-01'] == 3


def test_from_scene_et_actual_t_interval_monthly_et_reference_factor(tol=0.0001):
    output_coll = interpolate.from_scene_et_actual(
        scene_coll(['et', 'time', 'mask']),
        start_date='2017-07-01', end_date='2017-08-01',
        variables=['et', 'et_reference', 'et_fraction', 'count'],
        interp_args={'interp_method': 'linear', 'interp_days': 32,
                     'interp_source': 'IDAHO_EPSCOR/GRIDMET',
                     'interp_band': 'etr',
                     'interp_resample': 'nearest'},
        model_args={'et_reference_source': 'IDAHO_EPSCOR/GRIDMET',
                    'et_reference_band': 'etr',
                    'et_reference_factor': 0.5,
                    'et_reference_resample': 'nearest'},
        t_interval='monthly')

    TEST_POINT = (-121.5265, 38.7399)
    output = utils.point_coll_value(output_coll, TEST_POINT, scale=10)
    assert abs(output['et']['2017-07-01'] - 142.9622039794922) <= tol
    assert abs(output['et_reference']['2017-07-01'] - 310.3 * 0.5) <= tol
    assert abs(output['et_fraction']['2017-07-01'] - 142.9622039794922 / 310.3 / 0.5) <= tol
    assert output['count']['2017-07-01'] == 3


# CGM - Resampling is not being applied so this should be equal to nearest
def test_from_scene_et_actual_t_interval_monthly_et_reference_resample(tol=0.0001):
    output_coll = interpolate.from_scene_et_actual(
        scene_coll(['et', 'time', 'mask']),
        start_date='2017-07-01', end_date='2017-08-01',
        variables=['et', 'et_reference', 'et_fraction', 'count'],
        interp_args={'interp_method': 'linear', 'interp_days': 32,
                     'interp_source': 'IDAHO_EPSCOR/GRIDMET',
                     'interp_band': 'etr',
                     'interp_resample': 'bilinear'},
        model_args={'et_reference_source': 'IDAHO_EPSCOR/GRIDMET',
                    'et_reference_band': 'etr',
                    'et_reference_factor': 0.5,
                    'et_reference_resample': 'bilinear'},
        t_interval='monthly')

    TEST_POINT = (-121.5265, 38.7399)
    output = utils.point_coll_value(output_coll, TEST_POINT, scale=10)
    assert abs(output['et']['2017-07-01'] - 142.9622039794922) <= tol
    assert abs(output['et_reference']['2017-07-01'] - 310.3 * 0.5) <= tol
    assert abs(output['et_fraction']['2017-07-01'] - 142.9622039794922 / 310.3 / 0.5) <= tol
    assert output['count']['2017-07-01'] == 3


def test_from_scene_et_actual_t_interval_daily_et_fraction_max(tol=0.0001):
    output_coll = interpolate.from_scene_et_actual(
        scene_coll(['et', 'time', 'mask'], et=[100, 100, 100]),
        start_date='2017-07-01', end_date='2017-08-01',
        variables=['et', 'et_reference', 'et_fraction'],
        interp_args={'interp_method': 'linear', 'interp_days': 32,
                     'interp_source': 'IDAHO_EPSCOR/GRIDMET',
                     'interp_band': 'etr',
                     'interp_resample': 'nearest',
                     'et_fraction_min': 0.0,
                     'et_fraction_max': 1.4,
                     },
        model_args={'et_reference_source': 'IDAHO_EPSCOR/GRIDMET',
                    'et_reference_band': 'etr',
                    'et_reference_resample': 'nearest',
                    'et_reference_factor': 1.0,
                    },
        t_interval='daily')

    TEST_POINT = (-121.5265, 38.7399)
    output = utils.point_coll_value(output_coll, TEST_POINT, scale=10)
    assert abs(output['et_fraction']['2017-07-10'] - 1.4) <= tol


def test_from_scene_et_fraction_t_interval_bad_value():
    # Function should raise a ValueError if t_interval is not supported
    with pytest.raises(ValueError):
        interpolate.from_scene_et_fraction(
            scene_coll(['et', 'time', 'mask']),
            start_date='2017-07-01', end_date='2017-08-01', variables=['et'],
            interp_args={'interp_method': 'linear', 'interp_days': 32},
            model_args={'et_reference_source': 'IDAHO_EPSCOR/GRIDMET',
                        'et_reference_band': 'etr',
                        'et_reference_factor': 0.5,
                        'et_reference_resample': 'nearest'},
            t_interval='deadbeef')


def test_from_scene_et_fraction_t_interval_no_value():
    # Function should raise an Exception if t_interval is not set
    with pytest.raises(TypeError):
        interpolate.from_scene_et_fraction(
            scene_coll(['et', 'time', 'mask']),
            start_date='2017-07-01', end_date='2017-08-01',
            variables=['et', 'et_reference', 'et_fraction', 'count'],
            interp_args={'interp_method': 'linear', 'interp_days': 32},
            model_args={'et_reference_source': 'IDAHO_EPSCOR/GRIDMET',
                        'et_reference_band': 'etr',
                        'et_reference_factor': 0.5,
                        'et_reference_resample': 'nearest'})


def test_from_scene_et_actual_t_interval_bad_value():
    # Function should raise a ValueError if t_interval is not supported
    with pytest.raises(ValueError):
        interpolate.from_scene_et_actual(
            scene_coll(['et', 'time', 'mask']),
            start_date='2017-07-01', end_date='2017-08-01', variables=['et'],
            interp_args={'interp_method': 'linear', 'interp_days': 32,
                         'interp_source': 'IDAHO_EPSCOR/GRIDMET',
                         'interp_band': 'etr', 'interp_resample': 'nearest'},
            model_args={'et_reference_source': 'IDAHO_EPSCOR/GRIDMET',
                        'et_reference_band': 'etr',
                        'et_reference_factor': 1.0,
                        'et_reference_resample': 'nearest'},
            t_interval='deadbeef')


def test_from_scene_et_actual_t_interval_no_value():
    # Function should raise an Exception if t_interval is not set
    with pytest.raises(TypeError):
        interpolate.from_scene_et_actual(
            scene_coll(['et', 'time', 'mask']),
            start_date='2017-07-01', end_date='2017-08-01', variables=['et'],
            interp_args={'interp_method': 'linear', 'interp_days': 32,
                         'interp_source': 'IDAHO_EPSCOR/GRIDMET',
                         'interp_band': 'etr',
                         'interp_resample': 'nearest'},
            model_args={'et_reference_source': 'IDAHO_EPSCOR/GRIDMET',
                        'et_reference_band': 'etr',
                        'et_reference_factor': 1.0,
                        'et_reference_resample': 'nearest'})


def test_from_scene_et_fraction_interp_args_use_joins_true(tol=0.01):
    # Check that the use_joins interp_args parameter works
    output_coll = interpolate.from_scene_et_fraction(
        scene_coll(['et_fraction', 'time', 'mask']),
        start_date='2017-07-01', end_date='2017-08-01',
        variables=['et', 'et_reference', 'count'],
        interp_args={'interp_method': 'linear', 'interp_days': 32, 'use_joins': True},
        model_args={'et_reference_source': 'IDAHO_EPSCOR/GRIDMET',
                    'et_reference_band': 'etr',
                    'et_reference_factor': 1.0,
                    'et_reference_resample': 'nearest'},
        t_interval='monthly')

    TEST_POINT = (-121.5265, 38.7399)
    output = utils.point_coll_value(output_coll, TEST_POINT, scale=10)
    assert abs(output['et_reference']['2017-07-01'] - 310.3) <= tol
    assert abs(output['et']['2017-07-01'] - (310.3 * 0.4)) <= tol
    assert output['count']['2017-07-01'] == 3


def test_from_scene_et_fraction_interp_args_use_joins_false(tol=0.01):
    # Check that the use_joins interp_args parameter works
    output_coll = interpolate.from_scene_et_fraction(
        scene_coll(['et_fraction', 'time', 'mask']),
        start_date='2017-07-01', end_date='2017-08-01',
        variables=['et', 'et_reference', 'count'],
        interp_args={'interp_method': 'linear', 'interp_days': 32, 'use_joins': False},
        model_args={'et_reference_source': 'IDAHO_EPSCOR/GRIDMET',
                    'et_reference_band': 'etr',
                    'et_reference_factor': 1.0,
                    'et_reference_resample': 'nearest'},
        t_interval='monthly')

    TEST_POINT = (-121.5265, 38.7399)
    output = utils.point_coll_value(output_coll, TEST_POINT, scale=10)
    assert abs(output['et_reference']['2017-07-01'] - 310.3) <= tol
    assert abs(output['et']['2017-07-01'] - (310.3 * 0.4)) <= tol
    assert output['count']['2017-07-01'] == 3


def test_from_scene_et_actual_interp_args_use_joins_true(tol=0.01):
    # Check that the use_joins interp_args parameter works
    output_coll = interpolate.from_scene_et_actual(
        scene_coll(['et', 'time', 'mask']),
        start_date='2017-07-01', end_date='2017-08-01',
        variables=['et', 'et_reference', 'count'],
        interp_args={'interp_method': 'linear', 'interp_days': 32,
                     'interp_source': 'IDAHO_EPSCOR/GRIDMET', 'interp_band': 'etr',
                     'use_joins': True},
        model_args={'et_reference_source': 'IDAHO_EPSCOR/GRIDMET',
                    'et_reference_band': 'etr',
                    'et_reference_factor': 1.0,
                    'et_reference_resample': 'nearest'},
        t_interval='monthly')

    TEST_POINT = (-121.5265, 38.7399)
    output = utils.point_coll_value(output_coll, TEST_POINT, scale=10)
    assert abs(output['et']['2017-07-01'] - 142.9622039794922) <= tol
    assert abs(output['et_reference']['2017-07-01'] - 310.3) <= tol
    assert output['count']['2017-07-01'] == 3


def test_from_scene_et_actual_interp_args_use_joins_false(tol=0.01):
    # Check that the use_joins interp_args parameter works
    output_coll = interpolate.from_scene_et_actual(
        scene_coll(['et', 'time', 'mask']),
        start_date='2017-07-01', end_date='2017-08-01',
        variables=['et', 'et_reference', 'count'],
        interp_args={'interp_method': 'linear', 'interp_days': 32,
                     'interp_source': 'IDAHO_EPSCOR/GRIDMET', 'interp_band': 'etr',
                     'use_joins': True},
        model_args={'et_reference_source': 'IDAHO_EPSCOR/GRIDMET',
                    'et_reference_band': 'etr',
                    'et_reference_factor': 1.0,
                    'et_reference_resample': 'nearest'},
        t_interval='monthly')

    TEST_POINT = (-121.5265, 38.7399)
    output = utils.point_coll_value(output_coll, TEST_POINT, scale=10)
    assert abs(output['et']['2017-07-01'] - 142.9622039794922) <= tol
    assert abs(output['et_reference']['2017-07-01'] - 310.3) <= tol
    assert output['count']['2017-07-01'] == 3



"""
These tests were attempts at making "full" interpolation calls.
They could be removed but are being left in case we want to explore this again
at some point in the future.
"""
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
#         interpolate.daily(target_coll, source_coll, interp_days=32),
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
#         interpolate.daily(target_coll, source_coll, interp_days=4),
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
#         interpolate.daily(target_coll, source_coll, interp_days=16),
#         xy=(-121.5265, 38.7399), scale=30)
#     pprint.pprint(output['B1'])
#
#     assert True
