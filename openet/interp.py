import calendar
import logging
import sys

import ee

system_properties = ['system:index', 'system:time_start']


def daily(target_coll, source_coll, interp_days=32, interp_method='linear'):
    """Generate daily ETa collection from ETo and ETf collections

    Parameters
    ----------
    target_coll : ee.ImageCollection
        Source images will be interpolated to each target image time_start.
        Target images should have a daily time step.  This will typically be
        the reference ET (ETr) collection.
    source_coll : ee.ImageCollection
        Images that will be interpolated to the target image collection.
        This will typically be the fraction of reference ET (ETrF) collection.
    interp_days : int, optional
        Number of days before and after each image date to include in the
        interpolation (the default is 32).
    interp_method : {'linear'}, optional
        Interpolation method (the default is 'linear').

    Returns
    -------
    ee.ImageCollection() of daily interpolated images

    Raises
    ------
    ValueError
        If `interp_method` is not a supported method.

    """
    # Add TIME_0UTC as a separate band to each image for the mosaic
    source_mod_coll = source_coll.map(add_time_band)

    # Filters for joining the neighboring Landsat images in time
    # Need to add one extra day since target time_start may be offset from source
    #   (i.e. GRIDMET may be 7 UTC but Landsat is ~18 UTC
    #   Does it need to be added to both filters?
    # Which one should be < / > and which should be <= / >=
    # We should probably use TIME_0UTC here instead of system:time_start
    prev_filter = ee.Filter.And(
        ee.Filter.maxDifference(
            difference=(interp_days + 1) * 24 * 60 * 60 * 1000,
            leftField='system:time_start', rightField='system:time_start'),
        ee.Filter.greaterThan(
            leftField='system:time_start', rightField='system:time_start'))
    next_filter = ee.Filter.And(
        ee.Filter.maxDifference(
            difference=(interp_days + 1) * 24 * 60 * 60 * 1000.0,
            leftField='system:time_start', rightField='system:time_start'),
        ee.Filter.lessThanOrEquals(
            leftField='system:time_start', rightField='system:time_start'))

    # Join the neighboring Landsat images in time
    target_coll = ee.ImageCollection(
        ee.Join.saveAll('prev', 'system:time_start', True).apply(
            target_coll, source_mod_coll, prev_filter))
    target_coll = ee.ImageCollection(
        ee.Join.saveAll('next', 'system:time_start', False).apply(
            target_coll, source_mod_coll, next_filter))

    # Map the interpolation function over the joine image collection
    if interp_method.lower() == 'linear':
        interp_coll = ee.ImageCollection(target_coll.map(_linear))
    # elif interp_type.lower() == 'nearest':
    #     interp_coll = ee.ImageCollection(target_coll.map(_nearest))
    else:
        raise ValueError('invalid interpolation method: {}'.format(interp_method))

    return interp_coll


def _linear(image):
    """Linearly interpolate source images to target image time_start

    Parameters
    ----------
    image : ee.Image
        Function will use the first band in the image as reference ET.
        Input image must have join properties 'prev' and 'next'.
        prev: list of images with bands: value and time
        next: list of images with bands: value and time

    Returns
    -------
    ee.Image of interpolated values with band name 'src'

    Notes
    -----
    This function is intended to be mapped over an image collection and can
    only take one input parameter.

    """
    target_image = ee.Image(image).select(0)

    time_0utc = date_to_time_0utc(ee.Date(image.get('system:time_start')))
    time_image = ee.Image.constant(time_0utc).double().rename(['time'])

    # For mosaic, joined images were sorted with closest image in time last
    prev_qm_image = ee.ImageCollection.fromImages(
        ee.List(target_image.get('prev'))).mosaic()
    next_qm_image = ee.ImageCollection.fromImages(
        ee.List(target_image.get('next'))).mosaic()

    # Is it safe to assume the bands stay in order?
    prev_value_image = ee.Image(prev_qm_image.select(0)).double()
    next_value_image = ee.Image(next_qm_image.select(0)).double()
    prev_time_image = ee.Image(prev_qm_image.select('time')).double()
    next_time_image = ee.Image(next_qm_image.select('time')).double()

    # Fill masked values with values from the opposite image
    # Something like this is needed to ensure there are always two images
    #   to interpolate between
    # For large data gaps, this will cause a flat line instead of a ramp
    prev_time_mosaic = ee.Image(ee.ImageCollection.fromImages([
        next_time_image, prev_time_image]).mosaic())
    next_time_mosaic = ee.Image(ee.ImageCollection.fromImages([
        prev_time_image, next_time_image]).mosaic())
    prev_value_mosaic = ee.Image(ee.ImageCollection.fromImages([
        next_value_image, prev_value_image]).mosaic())
    next_value_mosaic = ee.Image(ee.ImageCollection.fromImages([
        prev_value_image, next_value_image]).mosaic())

    # Calculate time ratio of the current image between other cloud free images
    time_ratio_image = time_image.subtract(prev_time_mosaic)\
        .divide(next_time_mosaic.subtract(prev_time_mosaic))

    # Interpolate values to the current image time
    interp_value_image = next_value_mosaic.subtract(prev_value_mosaic)\
        .multiply(time_ratio_image).add(prev_value_mosaic)

    return interp_value_image.multiply(target_image)\
        .copyProperties(image, system_properties)
        # .select([0], ['et']) \

def aggregate_daily(image_coll, start_date, end_date, agg_type='mean'):
    """Aggregate images by day

    The primary purpose of this function is to join separate Landsat images
    from the same path into a single daily image.

    Parameters
    ----------
    image_coll : ee.ImageCollection
        Input image collection.
    start_date :  date, number, string
        Start date.  Needs to be an EE readable date (i.e. ISO Date string
        or milliseconds).
    end_date :  date, number, string
        End date.  Needs to be an EE readable date (i.e. ISO Date string or
        milliseconds).
    agg_type : {'mean'}, optional
        Aggregation type (the default is 'mean').

    Returns
    -------
    ee.ImageCollection()

    Notes
    -----
    This function should be used to mosaic Landsat images from same path
        but different rows.
    Aggregation is currently hardcoded to 'mean'.
    system:time_start of returned images will be 0 UTC (not the image time).

    """
    # Build a collection of date "features" to join to
    date_list = ee.List.sequence(
        ee.Date(start_date).millis(),
        ee.Date(end_date).millis(),
        # ee.Date(end_date).advance(1, 'day').millis(),
        24 * 3600 * 1000)
    def set_date(time):
        return ee.Feature(None, {
            'system:index': ee.Date(time).format('yyyy-MM-dd'),
            'system:time_start': ee.Number(time).int64(),
            'DATE': ee.Date(time).format('yyyy-MM-dd')})

    # Add a date property to the image collection
    def set_image_date(img):
        return ee.Image(img.set(
            'DATE', ee.Date(img.get('system:time_start')).format('yyyy-MM-dd')))

    join_coll = ee.FeatureCollection(
        ee.Join.saveAll('join').apply(
            ee.FeatureCollection(date_list.map(set_date)),
            ee.ImageCollection(image_coll.map(set_image_date)),
            ee.Filter.equals(leftField='DATE', rightField='DATE')))

    def aggregate_func(ftr):
        # The composite image time will be 0 UTC (not Landsat time)
        # if agg_type.lower() == 'mean':
        return ee.Image(
            ee.ImageCollection.fromImages(ftr.get('join')).mean()
                .copyProperties(ftr, system_properties + ['DATE']))

    return ee.ImageCollection(join_coll.map(aggregate_func))


def date_to_time_0utc(date):
    """Get the 0 UTC time_start for a date

    Parameters
    ----------
    date : ee.Date

    Returns
    -------
    ee.Number

    Notes
    -----
    Extra operations are needed since update() does not set milliseconds to 0.

    """
    return date.update(hour=0, minute=0, second=0).millis() \
        .divide(1000).floor().multiply(1000)


def add_time_band(image):
    """Add TIME_0UTC as a separate image band for quality mosaic

    Parameters
    ----------
    image : ee.Image

    Returns
    -------
    ee.Image

    Notes
    -----
    Mask time band with image mask.
    Intentionally using TIME_0UTC (instead of system:time_start)
        so that joins and interpolation happen evenly per day
    """
    time_0utc = date_to_time_0utc(ee.Date(image.get('system:time_start')))
    return image.addBands([
        image.select([0]).double().multiply(0).add(time_0utc).rename(['time'])
    ])
