import calendar

import ee


# Should these be test fixtures instead?
# I'm not sure how to make them fixtures and allow input parameters

def constant_image_value(image, crs='EPSG:32613', scale=1):
    """Extract the output value from a calculation done with constant images"""
    return ee.Image(image)\
        .reduceRegion(
            reducer=ee.Reducer.first(), scale=scale,
            geometry=ee.Geometry.Rectangle([0, 0, 10, 10], crs, False))\
        .getInfo()


def point_image_value(image, xy, scale=1):
    """Extract the output value from a calculation at a point"""
    return ee.Image(image)\
        .reduceRegion(
            reducer=ee.Reducer.first(), geometry=ee.Geometry.Point(xy),
            scale=scale)\
        .getInfo()


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
