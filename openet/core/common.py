import ee

from . import landsat


def landsat_c2_sr_cloud_mask(
        input_img,
        cirrus_flag=False,
        dilate_flag=False,
        shadow_flag=True,
        snow_flag=False,
        water_flag=False,
        cloud_score_flag=False,
        cloud_score_pct=100,
        filter_flag=False,
        saturated_flag=False,
        sr_cloud_qa_flag=False,
):
    """Compute cloud mask for a Landsat Coll. 2 Level 2 (SR) image using multiple approaches

    Parameters
    ----------
    input_img : ee.Image
        Image from a Landsat Collection 2 SR image collection
        with QA_PIXEL and QA_RADSAT bands and the SPACECRAFT_ID property
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
    cloud_score_flag : bool
        If true, mask pixels that have a TOA simple cloud score >= cloud_score_pct
        (the default is False).
    cloud_score_pct : bool
        Pixels with a cloud score >= this value will be masked (the default is 100).
    filter_flag : bool
        Filter QA_PIXEL cloud mask with a single pixel erode/dilate (the default is True).
    saturated_flag : bool
        If true, mask pixels that are saturated in the RGB bands (the default is False).
    sr_cloud_qa_flag : bool
        If true, mask pixels using the SR_CLOUD_QA band (the default is False).
        This approach will only be applied for Landsat 4/5/7 images
        and is equivalent to the LEDAPS masking in Collection 1.

    Returns
    -------
    ee.Image

    Notes
    -----
    Output image is structured to be applied directly with updateMask()
        i.e. 0 is cloud/masked, 1 is clear/unmasked

    """
    # Use the QA_PIXEL band to build the initial/default cloud mask
    mask_img = landsat.c02_qa_pixel_mask(
        input_img,
        cirrus_flag=cirrus_flag,
        dilate_flag=dilate_flag,
        shadow_flag=shadow_flag,
        snow_flag=snow_flag,
        water_flag=water_flag,
    )

    # Erode/dilate 1 cell to remove standalone pixels
    # This seems to mostly happen in the QA_PIXEL mask above,
    #   but it could be applied to the final mask before return
    # Not sure if the extra pixel dilate is needed, but leaving for now
    # Does this call need the reproject?  If applied in a map call it might be needed
    if filter_flag:
        mask_img = (
            mask_img
            .reduceNeighborhood(ee.Reducer.min(), ee.Kernel.circle(radius=1, units='pixels'))
            .reduceNeighborhood(ee.Reducer.max(), ee.Kernel.circle(radius=2, units='pixels'))
            # .reduceNeighborhood(ee.Reducer.max(), ee.Kernel.circle(radius=1, units='pixels'))
            # .reproject(input_img.projection())
        )

    # Apply other cloud masks
    if cloud_score_flag:
        mask_img = mask_img.Or(landsat.c02_cloud_score_mask(input_img, cloud_score_pct))
    if saturated_flag:
        mask_img = mask_img.Or(landsat.c02_qa_radsat_mask(input_img))
    if sr_cloud_qa_flag:
        mask_img = mask_img.Or(landsat.c02_sr_cloud_qa_mask(input_img))
        # # Should the QA_PIXEL flags be passed through to the function also?
        # sr_cloud_qa_mask = landsat.c02_l2_sr_cloud_qa_mask(
        #     input_img, adjacent_flag=dilate_flag, shadow_flag=shadow_flag, snow_flag=snow_flag
        # )
        # mask_img = mask_img.Or(sr_cloud_qa_mask)

    # Flip to set cloudy pixels to 0 and clear to 1 for an updateMask() call
    return mask_img.Not().rename(['cloud_mask'])


def sentinel2_toa_cloud_mask(input_img):
    """Extract cloud mask from the Sentinel 2 TOA QA60 band

    Parameters
    ----------
    input_img : ee.Image
        Image from the COPERNICUS/S2 collection with a QA60 band.

    Returns
    -------
    ee.Image

    Notes
    -----
    Output image is structured to be applied directly with updateMask()
        i.e. 0 is cloud, 1 is cloud free

    Bits
        10: Opaque clouds present
        11: Cirrus clouds present

    The Sentinel 2 TOA and SR cloud masks functions are currently identical

    References
    ----------
    https://sentinel.esa.int/documents/247904/685211/Sentinel-2_User_Handbook
    https://sentinel.esa.int/web/sentinel/technical-guides/sentinel-2-msi/level-1c/cloud-masks

    """
    qa_img = input_img.select(['QA60'])
    cloud_mask = qa_img.rightShift(10).bitwiseAnd(1).neq(0)\
        .Or(qa_img.rightShift(11).bitwiseAnd(1).neq(0))

    # Set cloudy pixels to 0 and clear to 1
    return cloud_mask.Not().rename(['cloud_mask'])


def sentinel2_sr_cloud_mask(input_img):
    """Extract cloud mask from the Sentinel 2 SR QA60 band

    Parameters
    ----------
    input_img : ee.Image
        Image from the COPERNICUS/S2_SR collection with a QA60 band.

    Returns
    -------
    ee.Image

    Notes
    -----
    Output image is structured to be applied directly with updateMask()
        i.e. 0 is cloud, 1 is cloud free

    Bits
        10: Opaque clouds present
        11: Cirrus clouds present

    The Sentinel 2 TOA and SR cloud masks functions are currently identical

    References
    ----------
    https://sentinel.esa.int/documents/247904/685211/Sentinel-2_User_Handbook
    https://sentinel.esa.int/web/sentinel/technical-guides/sentinel-2-msi/level-1c/cloud-masks

    """
    qa_img = input_img.select(['QA60'])
    cloud_mask = qa_img.rightShift(10).bitwiseAnd(1).neq(0)\
        .Or(qa_img.rightShift(11).bitwiseAnd(1).neq(0))

    # Set cloudy pixels to 0 and clear to 1
    return cloud_mask.Not().rename(['cloud_mask'])


def landsat_c2_sr_lst_correct(input_img, ndvi=None):
    """Apply correction to Collection 2 LST using adjusted ASTER emissivity

    Parameters
    ----------
    input_img : ee.Image
        Image from a Landsat Collection 2 SR image collection
        with the SPACECRAFT_ID and LANDSAT_PRODUCT_ID metadata properties
        (e.g. LANDSAT/LC08/C02/T1_L2).  The image itself is not read in this
        function but is instead used to select from the Level 2 and TOA collections.
    ndvi : ee.Image
        This parameter is deprecated and NDVI will be computed internally in the function,
        but leaving to support backwards compatibility.

    Returns
    -------
    lst : ee.Image

    Authors
    -------
    Peter ReVelle, Richard Allen, Ayse Kilic

    References
    ----------
    Malakar, N., Hulley, G., Hook, S., Laraby, K., Cook, M. and Schott, J., 2018.
    An operational land surface temperature product for Landsat thermal data:
    Methodology and validation.
    IEEE Transactions on Geoscience and Remote Sensing, 56(10), pp.5717-5735.

    Allen, R and Kilic, A. 2022.

    Hulley, G. 2023.

    """
    spacecraft_id = ee.String(input_img.get('SPACECRAFT_ID'))

    # Landsat image geometry for clipping ASTER GED
    image_geom = input_img.geometry()
    image_extent = image_geom.bounds(1, 'EPSG:4326')

    # Server side approach for getting image extent snapped to the ASTER GED grid
    buffer_cells = 1
    cellsize = 0.1
    image_xy = ee.Array(image_extent.coordinates().get(0)).transpose().toList()
    xmin = ee.Number(ee.List(image_xy.get(0)).reduce(ee.Reducer.min()))
    ymin = ee.Number(ee.List(image_xy.get(1)).reduce(ee.Reducer.min()))
    xmax = ee.Number(ee.List(image_xy.get(0)).reduce(ee.Reducer.max()))
    ymax = ee.Number(ee.List(image_xy.get(1)).reduce(ee.Reducer.max()))
    xmin = xmin.divide(cellsize * buffer_cells).floor().multiply(cellsize * buffer_cells)
    ymin = ymin.divide(cellsize * buffer_cells).floor().multiply(cellsize * buffer_cells)
    xmax = xmax.divide(cellsize * buffer_cells).ceil().multiply(cellsize * buffer_cells)
    ymax = ymax.divide(cellsize * buffer_cells).ceil().multiply(cellsize * buffer_cells)
    clip_extent = ee.Geometry.Rectangle([xmin, ymin, xmax, ymax], 'EPSG:4326', False)

    # Aster Global Emissivity Dataset
    ged = ee.Image('NASA/ASTER_GED/AG100_003').clip(clip_extent)

    veg_emis = 0.99
    soil_emiss_fill = 0.97

    # Set K1, K2 values
    k1 = ee.Dictionary({
        'LANDSAT_4': 607.76, 'LANDSAT_5': 607.76, 'LANDSAT_7': 666.09,
        'LANDSAT_8': 774.8853, 'LANDSAT_9': 799.0284,
    })
    k2 = ee.Dictionary({
        'LANDSAT_4': 1260.56, 'LANDSAT_5': 1260.56, 'LANDSAT_7': 1282.71,
        'LANDSAT_8': 1321.0789, 'LANDSAT_9': 1329.0284,
    })

    # Set c13, c14, and c regression coefficients from Malakar et al. (2018)
    # Landsat 9 coefficients are copied from L8
    c13 = ee.Dictionary({
        'LANDSAT_4': 0.3222, 'LANDSAT_5': -0.0723, 'LANDSAT_7': 0.2147,
        'LANDSAT_8': 0.6820, 'LANDSAT_9': 0.7689,
    })
    c14 = ee.Dictionary({
        'LANDSAT_4': 0.6498, 'LANDSAT_5': 1.0521, 'LANDSAT_7': 0.7789,
        'LANDSAT_8': 0.2578, 'LANDSAT_9': 0.1843,
    })
    c = ee.Dictionary({
        'LANDSAT_4': 0.0272, 'LANDSAT_5': 0.0195, 'LANDSAT_7': 0.0058,
        'LANDSAT_8': 0.0584, 'LANDSAT_9': 0.0457,
    })

    def get_matched_c2_t1_l2_image(input_img):
        # Find matching Landsat Collection 2 Tier 1 Level 2 image
        #   based on the "LANDSAT_PRODUCT_ID" property
        # Build the system:index format scene ID from the LANDSAT_PRODUCT_ID
        scene_id = ee.List(ee.String(input_img.get('LANDSAT_PRODUCT_ID')).split('_'))
        scene_id = (
            ee.String(scene_id.get(0)).cat('_').cat(ee.String(scene_id.get(2)))
            .cat('_').cat(ee.String(scene_id.get(3)))
        )

        # Testing if it is any faster to filter each collection separately
        # TODO: Test if adding an extra .filterDate() call helps
        return ee.Image(
            ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
            .filter(ee.Filter.eq('system:index', scene_id))
            .merge(ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
                   .filter(ee.Filter.eq('system:index', scene_id)))
            .merge(ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
                   .filter(ee.Filter.eq('system:index', scene_id)))
            .merge(ee.ImageCollection('LANDSAT/LT05/C02/T1_L2')
                   .filter(ee.Filter.eq('system:index', scene_id)))
            .merge(ee.ImageCollection('LANDSAT/LT04/C02/T1_L2')
                   .filter(ee.Filter.eq('system:index', scene_id)))
            .first()
        )

    def get_matched_c2_t1_radiance_image(input_img):
        # Find matching Landsat Collection 2 Tier 1 radiance image
        #   based on the "LANDSAT_PRODUCT_ID" property
        # Build the system:index format scene ID from the LANDSAT_PRODUCT_ID
        satellite = ee.String(input_img.get('SPACECRAFT_ID'))
        scene_id = ee.List(ee.String(input_img.get('LANDSAT_PRODUCT_ID')).split('_'))
        scene_id = (
            ee.String(scene_id.get(0)).cat('_').cat(ee.String(scene_id.get(2)))
            .cat('_').cat(ee.String(scene_id.get(3)))
        )

        # TODO: Fix error when images that are in the T1_L2 collections but not in the T1,
        #  will fail with a .get() error because matched_img is 'None',
        #  could cause issues if trying to map over a collection

        #  Testing if it is any faster to filter each collection separately
        # TODO: Test if adding an extra .filterDate() call helps
        matched_img = ee.Image(
            ee.ImageCollection('LANDSAT/LC09/C02/T1')
            .filter(ee.Filter.eq('system:index', scene_id))
            .merge(ee.ImageCollection('LANDSAT/LC08/C02/T1_RT')
                   .filter(ee.Filter.eq('system:index', scene_id)))
            .merge(ee.ImageCollection('LANDSAT/LE07/C02/T1')
                   .filter(ee.Filter.eq('system:index', scene_id)))
            .merge(ee.ImageCollection('LANDSAT/LT05/C02/T1')
                   .filter(ee.Filter.eq('system:index', scene_id)))
            .merge(ee.ImageCollection('LANDSAT/LT04/C02/T1')
                   .filter(ee.Filter.eq('system:index', scene_id)))
            .first()
        )

        input_bands = ee.Dictionary({
            'LANDSAT_4': ['B1', 'B2', 'B3', 'B4', 'B5', 'B7', 'B6'],
            'LANDSAT_5': ['B1', 'B2', 'B3', 'B4', 'B5', 'B7', 'B6'],
            'LANDSAT_7': ['B1', 'B2', 'B3', 'B4', 'B5', 'B7', 'B6_VCID_1'],
            'LANDSAT_8': ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B10'],
            'LANDSAT_9': ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B10'],
        })
        output_bands = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'thermal']

        add_thermal_properties = ee.Dictionary({
            'LANDSAT_4': 'RADIANCE_ADD_BAND_6',
            'LANDSAT_5': 'RADIANCE_ADD_BAND_6',
            'LANDSAT_7': 'RADIANCE_ADD_BAND_6_VCID_1',
            'LANDSAT_8': 'RADIANCE_ADD_BAND_10',
            'LANDSAT_9': 'RADIANCE_ADD_BAND_10',
        })
        mul_thermal_properties = ee.Dictionary({
            'LANDSAT_4': 'RADIANCE_MULT_BAND_6',
            'LANDSAT_5': 'RADIANCE_MULT_BAND_6',
            'LANDSAT_7': 'RADIANCE_MULT_BAND_6_VCID_1',
            'LANDSAT_8': 'RADIANCE_MULT_BAND_10',
            'LANDSAT_9': 'RADIANCE_MULT_BAND_10',
        })
        add_thermal_prop = ee.String(add_thermal_properties.get(satellite))
        mul_thermal_prop = ee.String(mul_thermal_properties.get(satellite))

        return (
            matched_img
            .select(ee.List(input_bands.get(satellite)), output_bands)
            .set({
                'RADIANCE_ADD_BAND_thermal': ee.Number(matched_img.get(add_thermal_prop)),
                'RADIANCE_MULT_BAND_thermal': ee.Number(matched_img.get(mul_thermal_prop)),
            })
        )

    # Rebuilding the coll2 image here from the LANDSAT_PRODUCT_ID
    #   since the extra bands needed for the calculation will likely
    #   have been dropped or excluded before getting to this function
    c02_lvl2_img = get_matched_c2_t1_l2_image(input_img)
    c02_rad_img = get_matched_c2_t1_radiance_image(input_img)

    # Compute NDVI from the Level 2 SR image
    # Including the global surface water maximum extent to limit the water mask
    # to only those areas that have been flagged as water at some point in time
    # which should help remove shadows that are misclassified as water
    ndvi = landsat.c02_sr_ndvi(
        sr_img=landsat.c02_l2_sr(c02_lvl2_img),
        water_mask=landsat.c02_qa_water_mask(c02_lvl2_img),
        gsw_extent_flag=True
    )

    # Apply Allen-Kilic Eq. 5 to calc. ASTER emiss. for Landsat
    # This is Eq. 4 of Malakar et al., 2018
    ged_emis = (
        ged.select(['emissivity_band13']).multiply(0.001)
        .multiply(ee.Number(c13.get(spacecraft_id)))
        .add(ged.select(['emissivity_band14']).multiply(0.001)
             .multiply(ee.Number(c14.get(spacecraft_id))))
        .add(ee.Number(c.get(spacecraft_id)))
    )

    # Apply Eq. 4 and 3 of Allen-Kilic to estimate the ASTER emissivity for bare soil
    # (this is Eq. 5 of Malakar et al., 2018) with settings by Allen-Kilic.
    # This uses NDVI of ASTER over the same period as ASTER emissivity.
    fc_aster = ged.select(['ndvi']).multiply(0.01).subtract(0.15).divide(0.65).clamp(0, 1.0)

    # The 0.9798 is average from ASTER spectral response for bands 13/14 for vegetation
    #   derived from Glynn Hulley (2023)
    # CGM - Reordered equation to avoid needing a constant image that would not have a projection
    #   X.multiply(-1).add(1) is equivalent to "1-X" or ee.Image.constant(1).subtract(X)
    em_soil = ged_emis.subtract(fc_aster.multiply(0.9798)).divide(fc_aster.multiply(-1).add(1))

    # Added accounting for instability in (1-fc_ASTER) denominator when fc_ASTER is large
    # by fixing bare component to spectral library emissivity of soil
    em_soil = em_soil.where(fc_aster.gt(0.8), soil_emiss_fill)

    # Fill in soil emissivity gaps using the default value
    # CGM - Not sure if the sameFootprint parameter is needed or does anything
    #   when unmasking with a value,
    # The default of True should be fine when GED is clipped
    em_soil = em_soil.unmask(soil_emiss_fill)

    # Resample soil emissivity using bilinear interpolation
    em_soil = em_soil.resample('bilinear')
    # # CGM - Having the resample without a reproject seemed to cause problems
    # #   when called from other modules/functions, but testing without it
    # em_soil = (
    #     em_soil.resample('bilinear')
    #     .reproject(crs=image_crs, crsTransform=image_geo)
    # )

    # Apply Eq. 4 and 6 of Allen-Kilic to estimate Landsat-based emissivity
    # Using the ASTER-based soil emissivity from above
    # The following estimate for emissivity to use with Landsat may need to be clamped
    #   to some predefined safe limits (for example, 0.5 and 1.0).
    fc_landsat = ndvi.subtract(0.15).divide(0.65).clamp(0, 1.0)

    # calc_smoothed_em_soil
    ls_em = fc_landsat.multiply(-1).add(1).multiply(em_soil).add(fc_landsat.multiply(veg_emis))

    # Apply Eq. 8 to get thermal surface radiance, Rc, from C2 Real time band 10
    # (Eq. 7 of Malakar et al. but without the emissivity to produce actual radiance)
    rc = (
        c02_rad_img.select(['thermal'])
        .multiply(ee.Number(c02_rad_img.get('RADIANCE_MULT_BAND_thermal')))
        .add(ee.Number(c02_rad_img.get('RADIANCE_ADD_BAND_thermal')))
        .subtract(c02_lvl2_img.select(['ST_URAD']).multiply(0.001))
        .divide(c02_lvl2_img.select(['ST_ATRAN']).multiply(0.0001))
        .subtract(ls_em.multiply(-1).add(1).multiply(c02_lvl2_img.select(['ST_DRAD']).multiply(0.001)))
    )

    # Apply Eq. 7 to convert Rs to LST (similar to Malakar et al., but with emissivity)
    return (
        ls_em.multiply(ee.Number(k1.get(spacecraft_id)))
        .divide(rc).add(1.0).log().pow(-1)
        .multiply(ee.Number(k2.get(spacecraft_id)))
        .rename('lst')
    )
