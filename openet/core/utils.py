import calendar
import logging
from time import sleep

import ee


def getinfo(ee_obj, n=4):
    """Make an exponential back off getInfo call on an Earth Engine object"""
    output = None
    for i in range(1, n):
        try:
            output = ee_obj.getInfo()
        except Exception as e:
            logging.info('    Resending query ({}/10)'.format(i))
            logging.debug('    {}'.format(e))
            sleep(i ** 2)
        if output:
            break
    return output


# TODO: Import from common.utils
# Should these be test fixtures instead?
# I'm not sure how to make them fixtures and allow input parameters
def constant_image_value(image, crs='EPSG:32613', scale=1):
    """Extract the output value from a calculation done with constant images"""
    return getinfo(ee.Image(image).reduceRegion(
        reducer=ee.Reducer.first(), scale=scale,
        geometry=ee.Geometry.Rectangle([0, 0, 10, 10], crs, False)))


def point_image_value(image, xy, scale=1):
    """Extract the output value from a calculation at a point"""
    return getinfo(ee.Image(image).reduceRegion(
        reducer=ee.Reducer.first(), geometry=ee.Geometry.Point(xy),
        scale=scale))


def millis(input_dt):
    """Convert datetime to milliseconds since epoch

    Parameters
    ----------
    input_df : datetime

    Returns
    -------
    int

    """
    return 1000 * int(calendar.timegm(input_dt.timetuple()))
