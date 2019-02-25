import ee

from . import utils
# import openet.core.utils as utils


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

    # # DEADBEEF - This module is assuming that the time band is already in
    # #   the source collection.
    # # Uncomment the following to add a time band here instead.
    # def add_utc0_time_band(image):
    #     date_0utc = utils.date_0utc(ee.Date(image.get('system:time_start')))
    #     return image.addBands([
    #         image.select([0]).double().multiply(0).add(date_0utc.millis())\
    #             .rename(['time'])])
    # source_coll = ee.ImageCollection(source_coll.map(add_utc0_time_band))

    if interp_method.lower() == 'linear':
        def _linear(image):
            """Linearly interpolate source images to target image time_start(s)

            Parameters
            ----------
            image : ee.Image.
                The first band in the image will be used as the "target" image
                and will be returned with the output image.

            Returns
            -------
            ee.Image of interpolated values with band name 'src'

            Notes
            -----
            The source collection images must have a time band.
            This function is intended to be mapped over an image collection and
                can only take one input parameter.

            """
            target_image = ee.Image(image).select(0).double()
            target_date = ee.Date(image.get('system:time_start'))

            # All filtering will be done based on 0 UTC dates
            utc0_date = utils.date_0utc(target_date)
            # utc0_time = target_date.update(hour=0, minute=0, second=0)\
            #     .millis().divide(1000).floor().multiply(1000)
            time_image = ee.Image.constant(utc0_date.millis()).double()

            # Build nodata images/masks that can be placed at the front/back of
            #   of the qm image collections in case the collections are empty.
            bands = source_coll.first().bandNames()
            prev_qm_mask = ee.Image.constant(ee.List.repeat(1, bands.length()))\
                .double().rename(bands).updateMask(0)\
                .set({
                    'system:time_start': utc0_date.advance(
                        -interp_days - 1, 'day').millis()})
            next_qm_mask = ee.Image.constant(ee.List.repeat(1, bands.length()))\
                .double().rename(bands).updateMask(0)\
                .set({
                    'system:time_start': utc0_date.advance(
                        interp_days + 2, 'day').millis()})

            # Build separate collections for before and after the target date
            prev_qm_coll = source_coll.filterDate(
                    utc0_date.advance(-interp_days, 'day'), utc0_date)\
                .merge(ee.ImageCollection(prev_qm_mask))
            next_qm_coll = source_coll.filterDate(
                    utc0_date, utc0_date.advance(interp_days + 1, 'day'))\
                .merge(ee.ImageCollection(next_qm_mask))

            # Flatten the previous/next collections to single images
            # The closest image in time should be on "top"
            # CGM - Is the previous collection already sorted?
            # prev_qm_image = prev_qm_coll.mosaic()
            prev_qm_image = prev_qm_coll.sort('system:time_start', True).mosaic()
            next_qm_image = next_qm_coll.sort('system:time_start', False).mosaic()

            # DEADBEEF - It might be easier to interpolate all bands instead of
            #   separating the value and time bands
            # prev_value_image = ee.Image(prev_qm_image).double()
            # next_value_image = ee.Image(next_qm_image).double()

            # Interpolate all bands except the "time" band
            prev_bands = prev_qm_image.bandNames()\
                .filter(ee.Filter.notEquals('item', 'time'))
            next_bands = next_qm_image.bandNames() \
                .filter(ee.Filter.notEquals('item', 'time'))
            prev_value_image = ee.Image(prev_qm_image.select(prev_bands)).double()
            next_value_image = ee.Image(next_qm_image.select(next_bands)).double()
            prev_time_image = ee.Image(prev_qm_image.select('time')).double()
            next_time_image = ee.Image(next_qm_image.select('time')).double()

            # Fill masked values with values from the opposite image
            # Something like this is needed to ensure there are always two
            #   values to interpolate between
            # For data gaps, this will cause a flat line instead of a ramp
            prev_time_mosaic = ee.Image(ee.ImageCollection.fromImages([
                next_time_image, prev_time_image]).mosaic())
            next_time_mosaic = ee.Image(ee.ImageCollection.fromImages([
                prev_time_image, next_time_image]).mosaic())
            prev_value_mosaic = ee.Image(ee.ImageCollection.fromImages([
                next_value_image, prev_value_image]).mosaic())
            next_value_mosaic = ee.Image(ee.ImageCollection.fromImages([
                prev_value_image, next_value_image]).mosaic())

            # Calculate time ratio of the current image between other cloud free images
            time_ratio_image = time_image.subtract(prev_time_mosaic) \
                .divide(next_time_mosaic.subtract(prev_time_mosaic))

            # Interpolate values to the current image time
            interp_value_image = next_value_mosaic.subtract(prev_value_mosaic) \
                .multiply(time_ratio_image).add(prev_value_mosaic)

            # CGM
            # Should/can the target image be mapped to the interpolated image?
            # Is there a clean way of computing ET here?
            return interp_value_image \
                .addBands(target_image) \
                .set({
                    'system:index': image.get('system:index'),
                    'system:time_start': image.get('system:time_start'),
                    # 'system:time_start': utc0_time,
            })

        interp_coll = ee.ImageCollection(target_coll.map(_linear))
    # elif interp_method.lower() == 'nearest':
    #     interp_coll = ee.ImageCollection(target_coll.map(_nearest))
    else:
        raise ValueError('invalid interpolation method: {}'.format(interp_method))

    return interp_coll


def aggregate_daily(image_coll, start_date=None, end_date=None,
                    agg_type='mean'):
    """Aggregate images by day without using joins

    The primary purpose of this function is to join separate Landsat images
    from the same path into a single daily image.

    Parameters
    ----------
    image_coll : ee.ImageCollection
        Input image collection.
    start_date :  date, number, string, optional
        Start date.
        Needs to be an EE readable date (i.e. ISO Date string or milliseconds).
    end_date :  date, number, string, optional
        Exclusive end date.
        Needs to be an EE readable date (i.e. ISO Date string or milliseconds).
    agg_type : {'mean'}, optional
        Aggregation type (the default is 'mean').
        Currently only a 'mean' aggregation type is supported.

    Returns
    -------
    ee.ImageCollection()

    Notes
    -----
    This function should be used to mosaic Landsat images from same path
        but different rows.
    system:time_start of returned images will be 0 UTC (not the image time).

    """
    if start_date and end_date:
        test_coll = image_coll.filterDate(ee.Date(start_date), ee.Date(end_date))
    elif start_date:
        test_coll = image_coll.filter(ee.Filter.greaterThanOrEquals(
            'system:time_start', ee.Date(start_date).millis()))
    elif end_date:
        test_coll = image_coll.filter(ee.Filter.lessThan(
            'system:time_start', ee.Date(end_date).millis()))
    else:
        test_coll = image_coll

    # Build a list of dates in the image_coll
    def get_date(time):
        return ee.Date(ee.Number(time)).format('yyyy-MM-dd')

    date_list = ee.List(test_coll.aggregate_array('system:time_start'))\
        .map(get_date).distinct().sort()

    def aggregate_func(date_str):
        start_date = ee.Date(ee.String(date_str))
        end_date = start_date.advance(1, 'day')
        agg_coll = image_coll.filterDate(start_date, end_date)

        # if agg_type.lower() == 'mean':
        agg_img = agg_coll.mean()
        # elif agg_type.lower() == 'median':
        #     agg_img = agg_coll.median()

        return agg_img.set({
            'system:index': start_date.format('yyyyMMdd'),
            'system:time_start': start_date.millis(),
            'DATE': start_date.format('yyyy-MM-dd'),
        })

    return ee.ImageCollection(date_list.map(aggregate_func))


# DEADBEEF - This function is no longer being used
# @deprecated
def aggregate_daily_with_joins(image_coll, start_date, end_date,
                               agg_type='mean'):
    """Aggregate images by day (using joins)

    The primary purpose of this function is to join separate Landsat images
    from the same path into a single daily image.

    Parameters
    ----------
    image_coll : ee.ImageCollection
        Input image collection.
    start_date :  date, number, string
        Start date.
        Needs to be an EE readable date (i.e. ISO Date string or milliseconds).
    end_date :  date, number, string
        End date.
        Needs to be an EE readable date (i.e. ISO Date string or milliseconds).
    agg_type : {'mean'}, optional
        Aggregation type (the default is 'mean').
        Currently only a 'mean' aggregation type is supported.

    Returns
    -------
    ee.ImageCollection()

    Notes
    -----
    This function should be used to mosaic Landsat images from same path
        but different rows.
    system:time_start of returned images will be 0 UTC (not the image time).

    """
    # Build a collection of time "features" to join to
    # "Flatten" dates to 0 UTC time
    if start_date and end_date:
        date_list = ee.List.sequence(
            ee.Date(start_date).millis(), ee.Date(end_date).millis(),
            24 * 3600 * 1000)
    # elif start_date:
    #    end_date = ee.Date(ee.Image(image_coll.limit(
    #        1, 'system:time_start', False).first()).get('system:time_start')
    #    end_date = ee.Date(end_date.format('yyyy-MM-dd')).advance(1, 'day')
    #    # end_date = ee.Date.fromYMD(end_date.get('year'), end_date.get('month'),
    #    #                            end_date.get('day')).advance(1, 'day')
    #    date_list = ee.List.sequence(
    #        ee.Date(start_date).millis(), end_date.millis(), 24 * 3600 * 1000)
    # elif end_date:
    #    start_date = ee.Date(start_date.format('yyyy-MM-dd')).advance(1, 'day')
    #    # start_date = ee.Date.fromYMD(
    #    #     start_date.get('year'), start_date.get('month'),
    #    #     start_date.get('day')).advance(1, 'day')
    #    date_list = ee.List.sequence(
    #        start_date.millis(), ee.Date(end_date).millis(), 24 * 3600 * 1000)
    # else:
    #    start_date = ee.Date(start_date.format('yyyy-MM-dd')).advance(1, 'day')
    #    end_date = ee.Date(ee.Image(image_coll.limit(
    #        1, 'system:time_start', False).first()).get('system:time_start')
    #    end_date = ee.Date(end_date.format('yyyy-MM-dd')).advance(1, 'day')
    #    date_list = ee.List.sequence(
    #        ee.Date(start_date).millis(), ee.Date(end_date).millis(),
    #        24 * 3600 * 1000)

    def set_date(time):
        return ee.Feature(None, {
            'system:index': ee.Date(time).format('yyyyMMdd'),
            'system:time_start': ee.Number(time).int64(),
            'DATE': ee.Date(time).format('yyyy-MM-dd')})

    # Add a date property to the image collection
    def set_image_date(img):
        return ee.Image(img.set({
            'DATE': ee.Date(img.get('system:time_start')).format('yyyy-MM-dd')}))

    join_coll = ee.FeatureCollection(
        ee.Join.saveAll('join').apply(
            ee.FeatureCollection(date_list.map(set_date)),
            ee.ImageCollection(image_coll.map(set_image_date)),
            ee.Filter.equals(leftField='DATE', rightField='DATE')))

    def aggregate_func(ftr):
        # The composite image time will be 0 UTC (not Landsat time)
        agg_coll = ee.ImageCollection.fromImages(ftr.get('join'))

        # if agg_type.lower() == 'mean':
        agg_img = agg_coll.mean()
        # elif agg_type.lower() == 'median':
        #     agg_img = agg_coll.median()

        return agg_img.set({
            'system:index': ftr.get('system:index'),
            'system:time_start': ftr.get('system:time_start'),
            'DATE': ftr.get('DATE'),
        })

    return ee.ImageCollection(join_coll.map(aggregate_func))
