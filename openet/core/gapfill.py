import pprint

import ee


def filled_monthly_et(
        input_coll,
        img_date,
        etf_climo_img,
        etf_default_img,
        fill_months=4,
        etf_input_band='et_fraction',
        eto_input_band='et_reference',
        et_input_band='et',
        etf_climo_band='et_fraction',
        #etf_default_band='et_fraction',
):
    """Filled Monthly ET using Conor's Method

    Parameters
    ----------
    input_coll : ee.ImageCollection
        Input image collection generated using compute_monthly_et_fraction().
        Input images must contain "et", "et_fraction", and "et_reference" bands.
    img_date : datetime.pyi
    etf_climo_img : ee.Image
        ET fraction climatology image generated using the compute_monthly_climatology().
    etf_default_img : ee.Image
        ET fraction default (or fallback) image generated using the veget_etf().
    fill_months : int
        Number of months to use for filling before and after the target image date.
        The default is 4.
    etf_input_band : str
        Name of the band in the input collection containing the ET fraction image.
        The default is "et_fraction".
    eto_input_band : str
        Name of the band in the input collection containing the reference ET image.
        The default is "et_reference".
    et_input_band : str
        Name of the band in the input collection containing the ET image.
        The default is "et".
    etf_climo_band : str
        Name of the band in the climatology image containing the ET fraction image.
        The default is "et_fraction".

    Returns
    -------
    ee.ImageCollection

    Notes
    -----
    Output ET values will be rounded to the nearest integer

    """
    img_date = ee.Date(img_date)

    # Note, filtering this way would need to be adjusted for daily data
    source_img = (
        input_coll
        .filterDate(img_date.advance(-1, 'day'), img_date.advance(1, 'day'))
        .first()
    )

    # Number of months to use for filling before and after the target image date
    fill_start_date = img_date.advance(-fill_months, 'months')
    fill_end_date = img_date.advance(fill_months + 1, 'months')

    climo_img = ee.Image(etf_climo_img)
    # TODO: Check if the climo_mask is actually needed in mosaic_prep
    climo_mask = climo_img.select(['count']).gte(1)

    # Collect all the source bands and joined images that will be mosaiced
    # Set an index band based on the number of month offsets
    # The images will be masked with the image mask and climo mask
    def mosaic_prep(img):
        img = ee.Image(img)
        img_date = ee.Date(img.get('system:time_start'))

        # TODO: Check if this should be a constant image or mapped onto the source image
        index_img = ee.Image.constant(
            img_date.difference(ee.Date.fromYMD(2016, 1, 1), 'month').round()
        )
        # index_img = (
        #     img.select([0]).multiply(0)
        #     .add(img_date.difference(ee.Date.fromYMD(2016, 1, 1), 'month').round())
        # )

        return (
            img.select([etf_input_band])
            .addBands([climo_img.select([etf_climo_band], ['climo']), index_img.rename('index')])
            .double()
            .updateMask(climo_mask.And(img.select(['et_fraction']).mask()))
            .set({
                'mgrs_tile': img.get('mgrs_tile'),
                'month': img_date.get('month'),
                'system:time_start': img.get('system:time_start'),
            })
        )

    # Collections before and after target date
    prev_coll = input_coll.filterDate(fill_start_date, img_date).map(mosaic_prep)
    next_coll = input_coll.filterDate(img_date.advance(1, 'month'), fill_end_date).map(mosaic_prep)

    # Place a zero image at the back of the previous and next collections
    # Using the source image climo so that the mask for the end images will match the source
    blank_img = (
        climo_img.select([etf_climo_band] * 3, [etf_input_band, 'climo', 'index'])
        .double().multiply(0)
    )
    prev_coll = prev_coll.merge(ee.ImageCollection(
        blank_img.set({'system:time_start': img_date.advance(-fill_months - 1, 'months').millis()})
    ))
    next_coll = next_coll.merge(ee.ImageCollection(
        blank_img.set({'system:time_start': img_date.advance(fill_months + 2, 'months').millis()})
    ))

    # Mosaic to get the closest unmasked value in time
    prev_img = ee.Image(ee.ImageCollection(prev_coll).sort('system:time_start', True).mosaic())
    next_img = ee.Image(ee.ImageCollection(next_coll).sort('system:time_start', False).mosaic())

    value_prev = prev_img.select([etf_input_band])
    value_next = next_img.select([etf_input_band])
    climo_prev = prev_img.select(['climo'])
    climo_next = next_img.select(['climo'])

    index_prev = prev_img.select(['index'])
    index_next = next_img.select(['index'])

    # Building the index as a constant image since this index is being subtracted
    #   from the prev and next images below
    index_tgt = ee.Image.constant(img_date.difference(ee.Date.fromYMD(2016, 1, 1), 'month').round().int())

    # Swapping the order in the previous weight calculation
    #   so that target index is being subtracted from the previous image
    w_prev = index_prev.subtract(index_tgt).add(1).exp().multiply(0.5)
    # w_prev = index_tgt.subtract(index_prev).multiply(-1).add(1).exp().multiply(0.5)
    w_next = index_next.subtract(index_tgt).multiply(-1).add(1).exp().multiply(0.5)

    # Compute the filled ETf using Conor's Method
    etf_filled_img = (
        climo_img.select([etf_climo_band])
        .add(value_prev.subtract(climo_prev).multiply(w_prev))
        .add(value_next.subtract(climo_next).multiply(w_next))
    )

    # # TODO: Check if clamping the final ETf image is needed
    # # Clamp the filled ETf image
    # etf_filled_img = etf_filled_img.max(0)
    # # etf_filled_img = etf_filled_img.min(maximum_etf)

    # Get the ETo for computing ET
    eto_img = ee.Image(source_img.select(eto_input_band))

    # Compute the filled ET
    et_filled_img = etf_filled_img.multiply(eto_img).round().int().max(0).rename(['et_filled'])

    # Get the original unfilled ET for computing a filled mask and returning with the filled ET image
    et_unfilled_img = source_img.select([et_input_band], ['et_unfilled'])

    # Default ET image
    et_default_img = etf_default_img.multiply(eto_img).round().int().max(0)

    # The final filled image should only use the fill value if there is not an unfilled value
    et_output_img = (
        et_unfilled_img.addBands([et_filled_img, et_default_img])
        .reduce(ee.Reducer.firstNonNull())
    )
    mask_output_img = (
        et_unfilled_img.gt(-9999)
        .addBands([et_filled_img.multiply(0).add(2), et_default_img.multiply(0).add(3)])
        .reduce(ee.Reducer.firstNonNull())
    )

    # TODO: Check for any other properties that need to be updated
    return ee.Image(
        et_unfilled_img.addBands([et_output_img, mask_output_img])
        .rename(['et_unfilled', 'et_filled', 'filled_mask'])
        .set({
            'fill_months': fill_months,
            # 'core_version': openet.core.__version__,
            # 'system:time_start': img_date.millis(),
            # 'tool_name': TOOL_NAME,
            # 'tool_version': TOOL_VERSION,
        })
    )


def compute_monthly_et_fraction(
        et_coll, eto_coll, et_band='et', eto_band='et_reference',
):
    """Compute ET fraction for each ET image

    Parameters
    ----------
    et_coll : ee.ImageCollection
        The source ET collection.
    eto_coll : ee.ImageCollection
        Reference ET collection for computing ET fraction.
    et_band : str
        Name of the band in the ET collection that contains the ET image.
    eto_band : str
        Name of the band in the reference ET collection that contains the
        reference ET image.

    Returns
    -------
    ee.ImageCollection

    """
    # Join the reference ET collection to the ET collection
    # Use a 2 day max difference filter in case the monthly data doesn't start at 0 UTC
    # TODO: Add a date string to both of these collections to simplify joining
    #   It might make the most sense to add "start_date" and "end_date" to the reference ET collection
    max_diff_filter = ee.Filter.maxDifference(**{
        'difference': 2 * 24 * 60 * 60 * 1000,
        'leftField': 'system:time_start',
        'rightField': 'system:time_start'
    })
    join_coll = (
        ee.Join.saveFirst(**{'matchKey': 'match'})
        .apply(et_coll, eto_coll.select([eto_band]), max_diff_filter)
    )

    def image_etf(img):
        """Compute ETf and return ET, ETf, and ETo"""
        img = ee.Image(img)
        img_date = ee.Date(img.get('system:time_start'))

        eto_img = (
            ee.Image(img.get('match'))
            .select([eto_band], ['et_reference'])
            .resample('bilinear')
        )
        etf_img = img.select([et_band]).divide(eto_img).rename(['et_fraction'])

        return (
            img.select([et_band], ['et']).addBands([etf_img, eto_img])
            .set({
                'mgrs_tile': img.get('mgrs_tile'),
                'month': img_date.get('month'),
                'system:time_start': img_date.millis(),
            })
        )

    return ee.ImageCollection(join_coll.map(image_etf))


def compute_monthly_climatology(
        input_coll,
        month,
        climo_year_start,
        climo_year_end,
        climo_min_count=3,
        input_band='et_fraction',
        output_band='et_fraction',
):
    """Compute the ET fraction climatology for the target month

    Parameters
    ----------
    input_coll : ee.ImageCollection
    month : int
        Climatology target month.
    climo_start_year : int
        Climatology start year passed to ee.Filter.calendarRange().
    climo_end_year : int
        Climatology end year (inclusive) passed to ee.Filter.calendarRange().
    climo_min_count : int
        Minimum number of years required to compute a filled value.
        Pixels with fewer years will be masked.  The default is 3.
    input_band : str
        Name of the band in the input collection that contains the ET fraction.
    output_band : str
        Name of the ET fraction band in the output image.

    Returns
    -------
    ee.Image

    """
    # TODO: Add additional error checking and validation on climo year parameters?
    #   Could check that the years are in the collection, or start is before end?
    climo_img = (
        ee.Image(
            input_coll.select([input_band])
            .filter(ee.Filter.calendarRange(month, month, 'month'))
            .filter(ee.Filter.calendarRange(climo_year_start, climo_year_end, 'year'))
            # CGM - The source collection should already be filtered to the MGRS tile
            # .filterMetadata('mgrs_tile', 'equals', mgrs_tile)
            .reduce(ee.Reducer.mean().combine(ee.Reducer.count(), sharedInputs=True))
        )
        .rename([output_band, 'count'])
        .set({
            'climo_min_count': climo_min_count,
            'climo_year_start': climo_year_start,
            'climo_year_end': climo_year_end,
            'month': month,
            'system:time_start': ee.Date.fromYMD(2001, month, 1).millis(),
        })
    )

    return climo_img.updateMask(climo_img.select(['count']).gte(climo_min_count))


def veget_etf_climatology(month):
    """VegET monthly climatology ETf to use as the fallback/default value if no climo is available

    Parameters
    ----------
    month : int

    Returns
    -------
    ee.Image

    """
    veget_coll_id = 'projects/openet/assets/veget/conus/climo'

    return (
        ee.ImageCollection(veget_coll_id)
        .filterMetadata('month_i', 'equals', month)
        .first()
        .resample('bilinear')
        .rename(['et_fraction'])
        .set({'default_etf_source': veget_coll_id})
    )


def nalcms_etf():
    """NALCMS landuse based ETf to use as the fallback/default value if no climo is available

    Returns
    -------
    ee.Image

    """
    nalcms_image_id = 'USGS/NLCD_RELEASES/2020_REL/NALCMS'
    naclms_etf_remap = [
        [1, 0.1],   #  1  Temperate or sub-polar needleleaf forest
        [2, 0.1],   #  2  Sub-polar taiga needleleaf forest
        [3, 0.1],   #  3  Tropical or sub-tropical broadleaf evergreen forest
        [4, 0.1],   #  4  Tropical or sub-tropical broadleaf deciduous forest
        [5, 0.1],   #  5  Temperate or sub-polar broadleaf deciduous forest
        [6, 0.2],   #  6  Mixed forest
        [7, 0.1],   #  7  Tropical or sub-tropical shrubland
        [8, 0.1],   #  8  Temperate or sub-polar shrubland
        [9, 0.1],   #  9  Tropical or sub-tropical grassland
        [10, 0.1],  # 10  Temperate or sub-polar grassland
        [11, 0.1],  # 11  Sub-polar or polar shrubland-lichen-moss
        [12, 0.1],  # 12  Sub-polar or polar grassland-lichen-moss
        [13, 0.1],  # 13  Sub-polar or polar barren-lichen-moss
        [14, 0.1],  # 14  Wetland
        [15, 0.1],  # 15  Cropland
        [16, 0.01], # 16  Barren land
        [17, 0.1],  # 17  Urban and built-up
        [18, 0.8],  # 18  Water
        [19, 0.1],  # 19  Snow and ice
    ]

    return (
        ee.Image(nalcms_image_id)
        .remap([x[0] for x in naclms_etf_remap], [x[1] for x in naclms_etf_remap])
        .rename(['et_fraction'])
        .set({'default_etf_source': nalcms_image_id})
    )
