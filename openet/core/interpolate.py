# import datetime
# import logging

import ee
# from dateutil.relativedelta import *

from . import utils
# import openet.core.utils as utils


def daily(target_coll, source_coll, interp_days=32, interp_method='linear',
          use_joins=False):
    """Interpolate non-daily source images to a daily target image collection

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
    use_joins : bool, optional
        If True, the source collection will be joined to the target collection
        before mapping/interpolation and the source images will be extracted
        from the join properties ('prev' and 'next').
        Setting use_joins=True should be more memory efficient.
        If False, the source images will be built by filtering the source
        collection separately for each image in the target collection
        (inside the mapped function).

    Returns
    -------
    ee.ImageCollection() of daily interpolated images

    Raises
    ------
    ValueError
        If `interp_method` is not a supported method.

    """

    prev_filter = ee.Filter.And(
        ee.Filter.maxDifference(
            difference=(interp_days + 1) * 24 * 60 * 60 * 1000,
            leftField='system:time_start',
            rightField='system:time_start',
        ),
        ee.Filter.greaterThan(
            leftField='system:time_start',
            rightField='system:time_start',
        )
    )

    next_filter = ee.Filter.And(
        ee.Filter.maxDifference(
            difference=(interp_days + 1) * 24 * 60 * 60 * 1000,
            leftField='system:time_start',
            rightField='system:time_start',
        ),
        ee.Filter.lessThanOrEquals(
            leftField='system:time_start',
            rightField='system:time_start',
        )
    )

    if use_joins:
        # Join the neighboring Landsat images in time
        target_coll = ee.ImageCollection(
            ee.Join.saveAll(
                matchesKey='prev',
                ordering='system:time_start',
                ascending=True,
                outer=True,
            ).apply(
                primary=target_coll,
                secondary=source_coll,
                condition=prev_filter,
            )
        )

        target_coll = ee.ImageCollection(
            ee.Join.saveAll(
                matchesKey='next',
                ordering='system:time_start',
                ascending=False,
                outer=True,
            ).apply(
                primary=target_coll,
                secondary=source_coll,
                condition=next_filter,
            )
        )

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

            if use_joins:
                # Build separate mosaics for before and after the target date
                prev_qm_image = ee.ImageCollection\
                    .fromImages(ee.List(ee.Image(image).get('prev')))\
                    .merge(ee.ImageCollection(prev_qm_mask))\
                    .sort('system:time_start', True)\
                    .mosaic()
                next_qm_image = ee.ImageCollection\
                    .fromImages(ee.List(ee.Image(image).get('next')))\
                    .merge(ee.ImageCollection(next_qm_mask))\
                    .sort('system:time_start', False)\
                    .mosaic()
            else:
                # Build separate collections for before and after the target date
                prev_qm_coll = source_coll\
                    .filterDate(utc0_date.advance(-interp_days, 'day'), utc0_date)\
                    .merge(ee.ImageCollection(prev_qm_mask))
                next_qm_coll = source_coll\
                    .filterDate(utc0_date, utc0_date.advance(interp_days + 1, 'day'))\
                    .merge(ee.ImageCollection(next_qm_mask))

                # Flatten the previous/next collections to single images
                # The closest image in time should be on "top"
                # CGM - Is the previous collection already sorted?
                # prev_qm_image = prev_qm_coll.mosaic()
                prev_qm_image = prev_qm_coll.sort('system:time_start', True)\
                    .mosaic()
                next_qm_image = next_qm_coll.sort('system:time_start', False)\
                    .mosaic()

            # DEADBEEF - It might be easier to interpolate all bands instead of
            #   separating the value and time bands
            # prev_value_image = ee.Image(prev_qm_image).double()
            # next_value_image = ee.Image(next_qm_image).double()

            # Interpolate all bands except the "time" band
            prev_bands = prev_qm_image.bandNames()\
                .filter(ee.Filter.notEquals('item', 'time'))
            next_bands = next_qm_image.bandNames()\
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
            time_ratio_image = time_image.subtract(prev_time_mosaic)\
                .divide(next_time_mosaic.subtract(prev_time_mosaic))

            # Interpolate values to the current image time
            interp_value_image = next_value_mosaic.subtract(prev_value_mosaic)\
                .multiply(time_ratio_image).add(prev_value_mosaic)

            return interp_value_image.addBands([target_image])\
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
            'date': start_date.format('yyyy-MM-dd'),
        })

    return ee.ImageCollection(date_list.map(aggregate_func))


"""
This function is currently being defined in the model.interpolate modules but  
could be defined here if we find that it is the same for all the models.
"""
# def from_scene_et_fraction(scene_coll, start_date, end_date, variables,
#                            model_args, t_interval='custom',
#                            interp_method='linear', interp_days=32,
#                            _interp_vars=['et_fraction', 'ndvi'],
#                            use_joins=False):
#     """
#
#     Parameters
#     ----------
#     scene_coll : ee.ImageCollection
#
#     start_date : str
#
#     end_date : str
#
#     variables : list
#         List of variables that will be returned in the Image Collection.
#     model_args : dict
#
#     t_interval : {'daily', 'monthly', 'annual', 'custom'}, optional
#         Time interval over which to interpolate and aggregate values
#         The default is 'custom' which means the aggregation time period
#         will be controlled by the start and end date parameters.
#     interp_method : {'linear}, optional
#         Interpolation method.  The default is 'linear'.
#     interp_days : int, str, optional
#         Number of extra days before the start date and after the end date
#         to include in the interpolation calculation. The default is 32.
#     _interp_vars : list, optional
#         The variables that can be interpolated to daily timesteps.
#         The default is to interpolate the 'et_fraction' and 'ndvi' bands.
#
#     Returns
#     -------
#     ee.ImageCollection
#
#     Raises
#     ------
#     ValueError
#
#     """
#
#     # Check that the input parameters are valid
#     if t_interval.lower() not in ['daily', 'monthly', 'annual', 'custom']:
#         raise ValueError('unsupported t_interval: {}'.format(t_interval))
#     elif interp_method.lower() not in ['linear']:
#         raise ValueError('unsupported interp_method: {}'.format(
#             interp_method))
#
#     if type(interp_days) is str and utils.is_number(interp_days):
#         interp_days = int(interp_days)
#     elif not type(interp_days) is int:
#         raise TypeError('interp_days must be an integer')
#     elif interp_days <= 0:
#         raise ValueError('interp_days must be a positive integer')
#
#     if not variables:
#         raise ValueError('variables parameter must be set')
#
#     # Adjust start/end dates based on t_interval
#     # Increase the date range to fully include the time interval
#     start_dt = datetime.datetime.strptime(start_date, '%Y-%m-%d')
#     end_dt = datetime.datetime.strptime(end_date, '%Y-%m-%d')
#     if t_interval.lower() == 'annual':
#         start_dt = datetime.datetime(start_dt.year, 1, 1)
#         # Covert end date to inclusive, flatten to beginning of year,
#         # then add a year which will make it exclusive
#         end_dt -= relativedelta(days=+1)
#         end_dt = datetime.datetime(end_dt.year, 1, 1)
#         end_dt += relativedelta(years=+1)
#     elif t_interval.lower() == 'monthly':
#         start_dt = datetime.datetime(start_dt.year, start_dt.month, 1)
#         end_dt -= relativedelta(days=+1)
#         end_dt = datetime.datetime(end_dt.year, end_dt.month, 1)
#         end_dt += relativedelta(months=+1)
#     start_date = start_dt.strftime('%Y-%m-%d')
#     end_date = end_dt.strftime('%Y-%m-%d')
#
#     # The start/end date for the interpolation include more days
#     # (+/- interp_days) than are included in the ETr collection
#     interp_start_dt = start_dt - datetime.timedelta(days=interp_days)
#     interp_end_dt = end_dt + datetime.timedelta(days=interp_days)
#     interp_start_date = interp_start_dt.date().isoformat()
#     interp_end_date = interp_end_dt.date().isoformat()
#
#     # Get reference ET source
#     if 'et_reference_source' in model_args.keys():
#         et_reference_source = model_args['et_reference_source']
#     else:
#         raise ValueError('et_reference_source was not set')
#
#     # Get reference ET band name
#     if 'et_reference_band' in model_args.keys():
#         et_reference_band = model_args['et_reference_band']
#     else:
#         raise ValueError('et_reference_band was not set')
#
#     # Get reference ET factor
#     if 'et_reference_factor' in model_args.keys():
#         et_reference_factor = model_args['et_reference_factor']
#     else:
#         et_reference_factor = 1.0
#         logging.debug('et_reference_factor was not set, default to 1.0')
#         # raise ValueError('et_reference_factor was not set')
#
#     # Get reference ET resample
#     if 'et_reference_resample' in model_args.keys():
#         et_reference_resample = model_args['et_reference_resample']
#     else:
#         et_reference_resample = 'nearest'
#         logging.debug(
#             'et_reference_resample was not set, default to nearest')
#         # raise ValueError('et_reference_resample was not set')
#
#     if type(et_reference_source) is str:
#         # Assume a string source is an single image collection ID
#         #   not an list of collection IDs or ee.ImageCollection
#         daily_et_reference_coll = ee.ImageCollection(et_reference_source) \
#             .filterDate(start_date, end_date) \
#             .select([et_reference_band], ['et_reference'])
#     # elif isinstance(et_reference_source, computedobject.ComputedObject):
#     #     # Interpret computed objects as image collections
#     #     daily_et_reference_coll = ee.ImageCollection(et_reference_source)\
#     #         .select([et_reference_band])\
#     #         .filterDate(self.start_date, self.end_date)
#     else:
#         raise ValueError('unsupported et_reference_source: {}'.format(
#             et_reference_source))
#
#     # TODO: Need to add time and mask to the scene collection
#     # The time band is always needed for interpolation
#     interp_vars = _interp_vars + ['time']
#
#     # DEADBEEF - I don't think this is needed since interp_vars is hardcoded
#     # # Initialize variable list to only variables that can be interpolated
#     # interp_vars = list(set(interp_vars) & set(variables))
#     #
#     # # To return ET, the ETf must be interpolated
#     # if 'et' in variables and 'et_fraction' not in interp_vars:
#     #     interp_vars.append('et_fraction')
#     #
#     # # With the current interp.daily() function,
#     # #   something has to be interpolated in order to return et_reference
#     # if 'et_reference' in variables and 'et_fraction' not in interp_vars:
#     #     interp_vars.append('et_fraction')
#
#     # Filter scene collection to the interpolation range
#     # This probably isn't needed since scene_coll was built to this range
#     # scene_coll = scene_coll.filterDate(interp_start_date, interp_end_date)
#
#     # For count, compute the composite/mosaic image for the mask band only
#     if 'count' in variables:
#         aggregate_coll = aggregate_daily(
#             image_coll = scene_coll.select(['mask']),
#             start_date=start_date, end_date=end_date)
#         # The following is needed because the aggregate collection can be
#         #   empty if there are no scenes in the target date range but there
#         #   are scenes in the interpolation date range.
#         # Without this the count image will not be built but the other
#         #   bands will be which causes a non-homogeneous image collection.
#         aggregate_coll = aggregate_coll.merge(
#             ee.Image.constant(0).rename(['mask'])
#                 .set({'system:time_start': ee.Date(start_date).millis()}))
#
#     # Interpolate to a daily time step
#     # NOTE: the daily function is not computing ET (ETf x ETr)
#     #   but is returning the target (ETr) band
#     daily_coll = daily(
#         target_coll=daily_et_reference_coll,
#         source_coll=scene_coll.select(interp_vars),
#         interp_method=interp_method, interp_days=interp_days,
#         use_joins=use_joins,
#     )
#
#     # Compute ET from ETf and ETr (if necessary)
#     # The check for et_fraction is needed since it is back computed from ET and ETr
#     # if 'et' in variables or 'et_fraction' in variables:
#     def compute_et(img):
#         """This function assumes ETr and ETf are present"""
#         et_img = img.select(['et_fraction']).multiply(
#             img.select(['et_reference']))
#         return img.addBands(et_img.double().rename('et'))
#
#     daily_coll = daily_coll.map(compute_et)
#
#     def aggregate_image(agg_start_date, agg_end_date, date_format):
#         """Aggregate the daily images within the target date range
#
#         Parameters
#         ----------
#         agg_start_date: str
#             Start date (inclusive).
#         agg_end_date : str
#             End date (exclusive).
#         date_format : str
#             Date format for system:index (uses EE JODA format).
#
#         Returns
#         -------
#         ee.Image
#
#         Notes
#         -----
#         Since this function takes multiple inputs it is being called
#         for each time interval by separate mappable functions
#
#         """
#         # if 'et' in variables or 'et_fraction' in variables:
#         et_img = daily_coll.filterDate(agg_start_date, agg_end_date) \
#             .select(['et']).sum()
#         # if 'et_reference' in variables or 'et_fraction' in variables:
#         et_reference_img = daily_coll.filterDate(agg_start_date,
#                                                  agg_end_date) \
#             .select(['et_reference']).sum()
#
#         if et_reference_factor:
#             et_img = et_img.multiply(et_reference_factor)
#             et_reference_img = et_reference_img.multiply(
#                 et_reference_factor)
#
#         # DEADBEEF - This doesn't seem to be doing anything
#         if et_reference_resample in ['bilinear', 'bicubic']:
#             et_reference_img = et_reference_img.resample(
#                 et_reference_resample)
#
#         image_list = []
#         if 'et' in variables:
#             image_list.append(et_img.float())
#         if 'et_reference' in variables:
#             image_list.append(et_reference_img.float())
#         if 'et_fraction' in variables:
#             # Compute average et fraction over the aggregation period
#             image_list.append(
#                 et_img.divide(et_reference_img).rename(
#                     ['et_fraction']).float())
#         if 'ndvi' in variables:
#             # Compute average ndvi over the aggregation period
#             ndvi_img = daily_coll \
#                 .filterDate(agg_start_date, agg_end_date) \
#                 .mean().select(['ndvi']).float()
#             image_list.append(ndvi_img)
#         if 'count' in variables:
#             count_img = aggregate_coll \
#                 .filterDate(agg_start_date, agg_end_date) \
#                 .select(['mask']).sum().rename('count').uint8()
#             image_list.append(count_img)
#
#         return ee.Image(image_list) \
#             .set({
#             'system:index': ee.Date(agg_start_date).format(date_format),
#             'system:time_start': ee.Date(agg_start_date).millis()})
#         #     .set(interp_properties)\
#
#     # Combine input, interpolated, and derived values
#     if t_interval.lower() == 'daily':
#         def agg_daily(daily_img):
#             # CGM - Double check that this time_start is a 0 UTC time.
#             # It should be since it is coming from the interpolate source
#             #   collection, but what if source is GRIDMET (+6 UTC)?
#             agg_start_date = ee.Date(daily_img.get('system:time_start'))
#             # CGM - This calls .sum() on collections with only one image
#             return aggregate_image(
#                 agg_start_date=agg_start_date,
#                 agg_end_date=ee.Date(agg_start_date).advance(1, 'day'),
#                 date_format='YYYYMMdd')
#
#         return ee.ImageCollection(daily_coll.map(agg_daily))
#
#     elif t_interval.lower() == 'monthly':
#         def month_gen(iter_start_dt, iter_end_dt):
#             iter_dt = iter_start_dt
#             # Conditional is "less than" because end date is exclusive
#             while iter_dt < iter_end_dt:
#                 yield iter_dt.strftime('%Y-%m-%d')
#                 iter_dt += relativedelta(months=+1)
#
#         month_list = ee.List(list(month_gen(start_dt, end_dt)))
#
#         def agg_monthly(agg_start_date):
#             return aggregate_image(
#                 agg_start_date=agg_start_date,
#                 agg_end_date=ee.Date(agg_start_date).advance(1, 'month'),
#                 date_format='YYYYMM')
#
#         return ee.ImageCollection(month_list.map(agg_monthly))
#
#     elif t_interval.lower() == 'annual':
#         def year_gen(iter_start_dt, iter_end_dt):
#             iter_dt = iter_start_dt
#             while iter_dt < iter_end_dt:
#                 yield iter_dt.strftime('%Y-%m-%d')
#                 iter_dt += relativedelta(years=+1)
#
#         year_list = ee.List(list(year_gen(start_dt, end_dt)))
#
#         def agg_annual(agg_start_date):
#             return aggregate_image(
#                 agg_start_date=agg_start_date,
#                 agg_end_date=ee.Date(agg_start_date).advance(1, 'year'),
#                 date_format='YYYY')
#
#         return ee.ImageCollection(year_list.map(agg_annual))
#
#     elif t_interval.lower() == 'custom':
#         # Returning an ImageCollection to be consistent
#         return ee.ImageCollection(aggregate_image(
#             agg_start_date=start_date, agg_end_date=end_date,
#             date_format='YYYYMMdd'))


# @deprecated
# def aggregate_daily_with_joins(image_coll, start_date, end_date,
#                                agg_type='mean'):
#     """Aggregate images by day (using joins)
#
#     The primary purpose of this function is to join separate Landsat images
#     from the same path into a single daily image.
#
#     Parameters
#     ----------
#     image_coll : ee.ImageCollection
#         Input image collection.
#     start_date :  date, number, string
#         Start date.
#         Needs to be an EE readable date (i.e. ISO Date string or milliseconds).
#     end_date :  date, number, string
#         End date.
#         Needs to be an EE readable date (i.e. ISO Date string or milliseconds).
#     agg_type : {'mean'}, optional
#         Aggregation type (the default is 'mean').
#         Currently only a 'mean' aggregation type is supported.
#
#     Returns
#     -------
#     ee.ImageCollection()
#
#     Notes
#     -----
#     This function should be used to mosaic Landsat images from same path
#         but different rows.
#     system:time_start of returned images will be 0 UTC (not the image time).
#
#     """
#     # Build a collection of time "features" to join to
#     # "Flatten" dates to 0 UTC time
#     if start_date and end_date:
#         date_list = ee.List.sequence(
#             ee.Date(start_date).millis(), ee.Date(end_date).millis(),
#             24 * 3600 * 1000)
#     # elif start_date:
#     #    end_date = ee.Date(ee.Image(image_coll.limit(
#     #        1, 'system:time_start', False).first()).get('system:time_start')
#     #    end_date = ee.Date(end_date.format('yyyy-MM-dd')).advance(1, 'day')
#     #    # end_date = ee.Date.fromYMD(end_date.get('year'), end_date.get('month'),
#     #    #                            end_date.get('day')).advance(1, 'day')
#     #    date_list = ee.List.sequence(
#     #        ee.Date(start_date).millis(), end_date.millis(), 24 * 3600 * 1000)
#     # elif end_date:
#     #    start_date = ee.Date(start_date.format('yyyy-MM-dd')).advance(1, 'day')
#     #    # start_date = ee.Date.fromYMD(
#     #    #     start_date.get('year'), start_date.get('month'),
#     #    #     start_date.get('day')).advance(1, 'day')
#     #    date_list = ee.List.sequence(
#     #        start_date.millis(), ee.Date(end_date).millis(), 24 * 3600 * 1000)
#     # else:
#     #    start_date = ee.Date(start_date.format('yyyy-MM-dd')).advance(1, 'day')
#     #    end_date = ee.Date(ee.Image(image_coll.limit(
#     #        1, 'system:time_start', False).first()).get('system:time_start')
#     #    end_date = ee.Date(end_date.format('yyyy-MM-dd')).advance(1, 'day')
#     #    date_list = ee.List.sequence(
#     #        ee.Date(start_date).millis(), ee.Date(end_date).millis(),
#     #        24 * 3600 * 1000)
#
#     def set_date(time):
#         return ee.Feature(None, {
#             'system:index': ee.Date(time).format('yyyyMMdd'),
#             'system:time_start': ee.Number(time).int64(),
#             'date': ee.Date(time).format('yyyy-MM-dd')})
#
#     # Add a date property to the image collection
#     def set_image_date(img):
#         return ee.Image(img.set({
#             'date': ee.Date(img.get('system:time_start')).format('yyyy-MM-dd')}))
#
#     join_coll = ee.FeatureCollection(
#         ee.Join.saveAll('join').apply(
#             ee.FeatureCollection(date_list.map(set_date)),
#             ee.ImageCollection(image_coll.map(set_image_date)),
#             ee.Filter.equals(leftField='date', rightField='date')))
#
#     def aggregate_func(ftr):
#         # The composite image time will be 0 UTC (not Landsat time)
#         agg_coll = ee.ImageCollection.fromImages(ftr.get('join'))
#
#         # if agg_type.lower() == 'mean':
#         agg_img = agg_coll.mean()
#         # elif agg_type.lower() == 'median':
#         #     agg_img = agg_coll.median()
#
#         return agg_img.set({
#             'system:index': ftr.get('system:index'),
#             'system:time_start': ftr.get('system:time_start'),
#             'date': ftr.get('date'),
#         })
#
#     return ee.ImageCollection(join_coll.map(aggregate_func))
