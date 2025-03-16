import ee


def c02_l2_sr(input_img):
    """Prepare a Collection 2 Level 2 image to surface reflectance [0-1] and LST [K] values

    Parameters
    ----------
    input_img : ee.Image
        Image from a Landsat Collection 2 Level 2 image collection with SPACECRAFT_ID property
        (e.g. LANDSAT/LC08/C02/T1_L2).

    Returns
    -------
    ee.Image

    """
    # Use the SPACECRAFT_ID property identify each Landsat type
    spacecraft_id = ee.String(input_img.get('SPACECRAFT_ID'))

    # Rename bands to generic names
    input_bands = ee.Dictionary({
        'LANDSAT_4': ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7', 'ST_B6', 'QA_PIXEL', 'QA_RADSAT'],
        'LANDSAT_5': ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7', 'ST_B6', 'QA_PIXEL', 'QA_RADSAT'],
        'LANDSAT_7': ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7', 'ST_B6', 'QA_PIXEL', 'QA_RADSAT'],
        'LANDSAT_8': ['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7', 'ST_B10', 'QA_PIXEL', 'QA_RADSAT'],
        'LANDSAT_9': ['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7', 'ST_B10', 'QA_PIXEL', 'QA_RADSAT'],
    })
    output_bands = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'lst', 'QA_PIXEL', 'QA_RADSAT']

    return (
        input_img
        .select(input_bands.get(spacecraft_id), output_bands)
        .multiply([0.0000275, 0.0000275, 0.0000275, 0.0000275, 0.0000275, 0.0000275, 0.00341802, 1, 1])
        .add([-0.2, -0.2, -0.2, -0.2, -0.2, -0.2, 149.0, 0, 0])
        .set({
            'system:time_start': input_img.get('system:time_start'),
            'system:index': input_img.get('system:index'),
            'SPACECRAFT_ID': spacecraft_id,
            'LANDSAT_PRODUCT_ID': input_img.get('LANDSAT_PRODUCT_ID'),
            'LANDSAT_SCENE_ID': input_img.get('LANDSAT_SCENE_ID'),
            # 'CLOUD_COVER_LAND': input_img.get('CLOUD_COVER_LAND'),
        })
    )


def c02_sr_ndvi(sr_img, water_mask=None, gsw_extent_flag=False):
    """Landsat Collection 2 normalized difference vegetation index (NDVI)

    A specialized function is needed for Collection 2 since the reflectance values can be both
    negative and greater than 1, which causes problems in the gee .normalizedDifference() function.

    Parameters
    ----------
    sr_img : ee.Image
        "Prepped" Landsat image with standardized band names of "nir" and "red".
    water_mask : ee.Image
        Mask used to identify pixels with negative or very low reflectance that will be set to -0.1.
    gsw_extent_flag : bool
        If True, apply the global surface water extent mask to the QA_PIXEL water mask
        to help avoid misclassified shadows being included in the water mask.

    Returns
    -------
    ee.Image

    """
    # Force the input values to be at greater than or equal to zero
    #   since C02 surface reflectance values can be negative
    #   but the normalizedDifference function will return nodata
    ndvi_img = sr_img.max(0).normalizedDifference(['nir', 'red'])

    b1 = sr_img.select(['nir'])
    b2 = sr_img.select(['red'])

    # Assume that very high reflectance values are unreliable for computing the index
    #   and set the output value to 0
    # Threshold value could be set lower, but for now only trying to catch saturated pixels
    ndvi_img = ndvi_img.where(b1.gte(1).Or(b2.gte(1)), 0)

    # Assume that low reflectance values are unreliable for computing the index and set to 0
    ndvi_img = ndvi_img.where(b1.lt(0.01).And(b2.lt(0.01)), 0)

    # If both reflectance values are below the threshold, and if the pixel is flagged as water,
    #   set the output to -0.1 (should this be -1?)
    if water_mask:
        if gsw_extent_flag:
            gsw_extent_mask = ee.Image('JRC/GSW1_4/GlobalSurfaceWater').select(['max_extent']).gte(1)
            water_mask = water_mask.And(gsw_extent_mask)
        ndvi_img = ndvi_img.where(b1.lt(0.01).And(b2.lt(0.01)).And(water_mask), -0.1)

    # Should there be an additional check for if either value was negative?
    # ndvi_img = ndvi_img.where(b1.lt(0).Or(b2.lt(0)), 0)

    return ndvi_img.clamp(-1.0, 1.0).rename(['ndvi'])


def c02_qa_pixel_mask(
        input_img,
        cirrus_flag=False,
        dilate_flag=False,
        shadow_flag=True,
        snow_flag=False,
        water_flag=False,
):
    """Landsat Collection 2 QA_PIXEL band cloud mask

    Parameters
    ----------
    input_img : ee.Image
        Image from a Landsat Collection 2 SR image collection
        with the QA_PIXEL band and the SPACECRAFT_ID property
        (e.g. LANDSAT/LC08/C02/T1_L2).
    cirrus_flag : bool
        If true, mask cirrus pixels (the default is False).
        Note, cirrus bits are only set for Landsat 8 (OLI) images.
    dilate_flag : bool
        If true, mask dilated cloud pixels (the default is False).
    shadow_flag : bool
        If true, mask shadow pixels (the default is True).
    snow_flag : bool
        If true, mask snow pixels (the default is False).
    water_flag : bool
        If true, mask water pixels (the default is False).

    Returns
    -------
    ee.Image

    Notes
    -----
    Assuming Cloud must be set to check Cloud Confidence
    (CGM - Note, this is a bad assumption and is probably causing missed clouds)

        Bits
        0: Fill
            0 for image data
            1 for fill data
        1: Dilated Cloud
            0 for cloud is not dilated or no cloud
            1 for cloud dilation
        2: Cirrus
            0 for no confidence level set or low confidence
            1 for high confidence cirrus
        3: Cloud
            0 for cloud confidence is not high
            1 for high confidence cloud
        4: Cloud Shadow
            0 for Cloud Shadow Confidence is not high
            1 for high confidence cloud shadow
        5: Snow
            0 for Snow/Ice Confidence is not high
            1 for high confidence snow cover
        6: Clear
            0 if Cloud or Dilated Cloud bits are set
            1 if Cloud and Dilated Cloud bits are not set
        7: Water
            0 for land or cloud
            1 for water
        8-9: Cloud Confidence
        10-11: Cloud Shadow Confidence
        12-13: Snow/Ice Confidence
        14-15: Cirrus Confidence

    Confidence values
        00: "No confidence level set"
        01: "Low confidence"
        10: "Medium confidence" (for Cloud Confidence only, otherwise "Reserved")
        11: "High confidence"

    References
    ----------
    https://prd-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/atoms/files/LSDS-1328_Landsat8-9-OLI-TIRS-C2-L2-DFCB-v6.pdf

    """
    qa_img = input_img.select(['QA_PIXEL'])
    mask_img = qa_img.rightShift(3).bitwiseAnd(1).neq(0)
    # The following line could be added to the mask_img call
    #     to include the cloud confidence bits
    # .Or(qa_img.rightShift(8).bitwiseAnd(3).gte(cloud_confidence))

    if cirrus_flag:
        mask_img = mask_img.Or(qa_img.rightShift(2).bitwiseAnd(1).neq(0))
    if dilate_flag:
        mask_img = mask_img.Or(qa_img.rightShift(1).bitwiseAnd(1).neq(0))
    if shadow_flag:
        mask_img = mask_img.Or(qa_img.rightShift(4).bitwiseAnd(1).neq(0))
    if snow_flag:
        mask_img = mask_img.Or(qa_img.rightShift(5).bitwiseAnd(1).neq(0))
    if water_flag:
        mask_img = mask_img.Or(qa_img.rightShift(7).bitwiseAnd(1).neq(0))

    return mask_img.rename(['mask'])


def c02_qa_water_mask(input_img):
    """Landsat Collection 2 QA_PIXEL band water mask

    Parameters
    ----------
    input_img : ee.Image
        Image from a Landsat Collection 2 SR image collection
        with the QA_PIXEL band and the SPACECRAFT_ID property
        (e.g. LANDSAT/LC08/C02/T1_L2).

    Returns
    -------
    ee.Image

    """
    return input_img.select(['QA_PIXEL']).rightShift(7).bitwiseAnd(1).neq(0).rename('qa_water_mask')


def c02_cloud_score_mask(input_img, cloud_score_pct=100):
    """Landsat Collection 2 TOA simple cloud score based cloud mask

    Parameters
    ----------
    input_img : ee.Image
        Image from a Landsat Collection 2 image collection
        (e.g. LANDSAT/LC08/C02/T1_L2).
    cloud_score_pct : float
        Pixels with a simple cloud score values greater than or equal to this
        parameter will be masked (the default is 100).

    Returns
    -------
    ee.Image

    """

    # TODO: Add a check to make sure cloud_score_pct is a number in the range [0-100]

    # Using the system:index requires an extra map call but might be more robust
    #   since the other properties may have been dropped
    toa_coll = c02_matched_toa_coll(input_img, 'system:index', 'system:index')

    output = ee.Algorithms.If(
        toa_coll.size().gt(0),
        ee.Algorithms.Landsat.simpleCloudScore(ee.Image(toa_coll.first()))
            .select('cloud').gte(cloud_score_pct),
        input_img.select('QA_PIXEL').multiply(0),
    )

    return ee.Image(output).rename(['mask'])


def c02_qa_radsat_mask(input_img):
    """Landsat Collection 2 QA_RADSAT band mask for saturated pixels

    Parameters
    ----------
    input_img : ee.Image
        Image from a Landsat Collection 2 image collection
        with the QA_RADSAT band and the SPACECRAFT_ID property
        (e.g. LANDSAT/LC08/C02/T1_L2).

    Returns
    -------
    ee.Image

    """

    # Use the QA_RADSAT band to mask if saturated in any of the RGB bands
    # The RGB bands in Landsat 8/9 are shifted over 1 because of the cirrus band
    # Use the SPACECRAFT_ID property identify each Landsat type
    spacecraft_id = ee.String(input_img.get('SPACECRAFT_ID'))
    bitshift = ee.Dictionary({
        'LANDSAT_4': 0, 'LANDSAT_5': 0, 'LANDSAT_7': 0, 'LANDSAT_8': 1, 'LANDSAT_9': 1,
    })
    return (
        input_img.select(['QA_RADSAT'], ['mask'])
        .rightShift(ee.Number(bitshift.get(spacecraft_id)))
        .bitwiseAnd(7).gt(0)
        # This will mask if saturated in "all" RGB bands instead of "any" RGB band
        # .bitwiseAnd(7).gte(7)
    )

    # # Mask if saturated in any band
    # return input_img.select(['QA_RADSAT']).gt(0)


def c02_l2_sr_cloud_qa_mask(input_img, adjacent_flag=True, shadow_flag=True, snow_flag=True):
    """Landsat Collection 2 Level 2 SR_CLOUD_QA band cloud mask (Landsat 4/5/7 only)

    Parameters
    ----------
    input_img : ee.Image
        Image from a Landsat Collection 2 SR image collection
        with the SR_CLOUD_QA band and the SPACECRAFT_ID property
        (e.g. LANDSAT/LC08/C02/T1_L2).
    adjacent_flag : bool
        If true, mask adjacent to cloud pixels (the default is True).
    shadow_flag : bool
        If true, mask shadow pixels (the default is True).
    snow_flag : bool
        If true, mask snow pixels (the default is True).

    Returns
    -------
    ee.Image

    """

    # TODO: Try developing an implementation that doesn't require an "If"
    # TODO: Maybe rename "adjacent" to "dilate" to match QA_PIXEL function

    def sr_cloud_qa_l57(sr_cloud_qa_img):
        # The SR_CLOUD_QA band is only in Landsat 4/5/7
        # Bit 0: Dark Dense Vegetation (DDV)
        # Bit 1: Cloud, Bit 2: Cloud Shadow, Bit 3: Adjacent to Cloud
        # Bit 4: Snow, Bit 5: Water
        mask_img = sr_cloud_qa_img.rightShift(1).bitwiseAnd(1).neq(0)
        if shadow_flag:
            mask_img = mask_img.Or(sr_cloud_qa_img.rightShift(2).bitwiseAnd(1).neq(0))
        if adjacent_flag:
            mask_img = mask_img.Or(sr_cloud_qa_img.rightShift(3).bitwiseAnd(1).neq(0))
        if snow_flag:
            mask_img = mask_img.Or(sr_cloud_qa_img.rightShift(4).bitwiseAnd(1).neq(0))

        return mask_img

    def sr_cloud_qa_l89(sr_cloud_qa_img):
        # There is no SR_CLOUD_QA band in the Landsat 8/9 images
        #   so return an all zero image for the mask
        return sr_cloud_qa_img.multiply(0)

    spacecraft_id = ee.String(input_img.get('SPACECRAFT_ID'))
    return ee.Image(
        ee.Algorithms.If(
            ee.List(['LANDSAT_8', 'LANDSAT_9']).contains(spacecraft_id),
            sr_cloud_qa_l89(input_img.select('QA_PIXEL')),
            sr_cloud_qa_l57(input_img.select('SR_CLOUD_QA'))
        )
    ).rename(['mask'])


def c02_matched_toa_coll(
        input_img,
        image_property='LANDSAT_SCENE_ID',
        match_property='LANDSAT_SCENE_ID',
):
    """Return the Landsat Collection 2 TOA collection matching an image property

    Parameters
    ----------
    input_img : ee.Image
        Image with the "image_property" metadata property.
    image_property : str
        The metadata property name in input_img to use as a match criteria
        (the default is "LANDSAT_SCENE_ID").
    match_property : str
        The metadata property name in the Landsat Collection 2 TOA collections
        to use as a match criteria (the default is "LANDSAT_SCENE_ID").

    Returns
    -------
    ee.ImageCollection

    Todo
    ----
    Try using LinkCollection instead

    """

    # Filter TOA collections to the target image UTC day
    # This filter range could be a lot tighter but keeping it to the day makes it easier to test
    #   and will hopefully not impact the performance too much
    start_date = ee.Date(input_img.get('system:time_start')).update(hour=0, minute=0, second=0)
    end_date = start_date.advance(1, 'day')

    l5_coll = ee.ImageCollection('LANDSAT/LT05/C02/T1_TOA').filterDate(start_date, end_date)
    l7_coll = ee.ImageCollection('LANDSAT/LE07/C02/T1_TOA').filterDate(start_date, end_date)
    l8_coll = ee.ImageCollection('LANDSAT/LC08/C02/T1_TOA').filterDate(start_date, end_date)
    l9_coll = ee.ImageCollection('LANDSAT/LC09/C02/T1_TOA').filterDate(start_date, end_date)

    # The default system:index gets modified when the collections are merged below,
    #   so save the system:index to a new "scene_id" property and use that for matching
    if match_property == 'system:index':
        l5_coll = l5_coll.map(lambda img: img.set('scene_id', img.get('system:index')))
        l7_coll = l7_coll.map(lambda img: img.set('scene_id', img.get('system:index')))
        l8_coll = l8_coll.map(lambda img: img.set('scene_id', img.get('system:index')))
        l9_coll = l9_coll.map(lambda img: img.set('scene_id', img.get('system:index')))
        match_property = 'scene_id'

    return (
        l9_coll.merge(l8_coll).merge(l7_coll).merge(l5_coll)
        .filter(ee.Filter.eq(match_property, ee.String(input_img.get(image_property))))
    )


def c02_matched_l2_coll(
        input_img,
        image_property='LANDSAT_SCENE_ID',
        match_property='LANDSAT_SCENE_ID',
):
    """Return the Landsat Collection 2 Level 2 collection matching an image property

    Parameters
    ----------
    input_img : ee.Image
        Image with the "image_property" metadata property.
    image_property : str
        The metedata property name in input_img to use as a match criteria
        (the default is "LANDSAT_SCENE_ID").
    match_property : str
        The metadata property name in the Landsat Collection 2 Level 2 collections
        to use as a match criteria (the default is "LANDSAT_SCENE_ID").

    Returns
    -------
    ee.ImageCollection

    Todo
    ----
    Try using LinkCollection instead

    """

    # Filter TOA collections to the target to image UTC day
    # This filter range could be a lot tighter but keeping it to the day makes it easier to test
    #   and will hopefully not impact the performance too much
    start_date = ee.Date(input_img.get('system:time_start')).update(hour=0, minute=0, second=0)
    end_date = start_date.advance(1, 'day')

    l5_coll = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2').filterDate(start_date, end_date)
    l7_coll = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2').filterDate(start_date, end_date)
    l8_coll = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2').filterDate(start_date, end_date)
    l9_coll = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2').filterDate(start_date, end_date)

    # The default system:index gets modified when the collections are merged below,
    #   so save the system:index to a new "scene_id" property and use that for matching
    if match_property == 'system:index':
        l5_coll = l5_coll.map(lambda img: img.set('scene_id', img.get('system:index')))
        l7_coll = l7_coll.map(lambda img: img.set('scene_id', img.get('system:index')))
        l8_coll = l8_coll.map(lambda img: img.set('scene_id', img.get('system:index')))
        l9_coll = l9_coll.map(lambda img: img.set('scene_id', img.get('system:index')))
        match_property = 'scene_id'

    return (
        l9_coll.merge(l8_coll).merge(l7_coll).merge(l5_coll)
        .filter(ee.Filter.eq(match_property, ee.String(input_img.get(image_property))))
    )
