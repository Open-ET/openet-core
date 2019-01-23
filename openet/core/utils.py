import calendar

import ee


# Should these be test fixtures instead?
# I'm not sure how to make them fixtures and allow input parameters

def constant_image_value(image, crs='EPSG:32613', scale=1, bands=[]):
    """Extract the output value from a calculation done with constant images

    This function is a little confusing since it returns a list of values if
        the input image is multiband or a single value for a single band image.
    It would probably be easier to always return the output dictionary or
        a list of values.

    """
    output = ee.Image(image)

    if bands:
        output = output.rename(bands)
    else:
        bands = output.bandNames().getInfo()

    output = output\
        .reduceRegion(
            reducer=ee.Reducer.first(), scale=scale,
            geometry=ee.Geometry.Rectangle([0, 0, 10, 10], crs, False))\
        .getInfo()

    if len(output.keys()) > 1:
        return [output[k] for k in bands]
    else:
        return list(output.values())[0]


def point_image_value(image, xy, scale=1):
    """Extract the output value from a calculation at a point"""
    return ee.Image(image).rename(['output'])\
        .reduceRegion(
            reducer=ee.Reducer.first(), geometry=ee.Geometry.Point(xy),
            scale=scale)\
        .getInfo()['output']


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
