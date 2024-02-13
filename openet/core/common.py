import ee

from . import landsat


def landsat_c2_sr_cloud_mask(
        input_img,
        cirrus_flag=False,
        dilate_flag=False,
        shadow_flag=True,
        snow_flag=False,
        cloud_score_flag=False,
        cloud_score_pct=100,
        filter_flag=False,
        saturated_flag=False,
        sr_cloud_qa_flag=False,
        # cloud_confidence=3,
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
        input_img, cirrus_flag, dilate_flag, shadow_flag, snow_flag
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


def landsat_c2_sr_lst_correct(sr_image, ndvi):
    """Apply correction to Collection 2 LST by using ASTER emissivity and recalculating LST following the
    procedure in the white paper by R. Allen and A. Kilic (2022) that is based on
    Malakar, N.K., Hulley, G.C., Hook, S.J., Laraby, K., Cook, M. and Schott, J.R., 2018.
    An operational land surface temperature product for Landsat thermal data: Methodology and validation.
    IEEE Transactions on Geoscience and Remote Sensing, 56(10), pp.5717-5735.

    Parameters
    ----------
    sr_image : ee.Image
        Image from a Landsat Collection 2 SR image collection
        with the SPACECRAFT_ID and LANDSAT_SCENE_ID metadata properties
        (e.g. LANDSAT/LC08/C02/T1_L2).
    ndvi : ee.Image
        Normalized difference vegetation index (NDVI)

    Returns
    -------
    L8_LST_smooth: LST recalculated from smoothed emissivity [ee.Image]

    :authors: Peter ReVelle, Richard Allen, Ayse Kilic
    """
    spacecraft_id = ee.String(sr_image.get('SPACECRAFT_ID'))

    veg_emis = 0.99
    soil_emiss_fill = 0.97

    # Aster Global Emissivity Dataset
    ged = ee.Image('NASA/ASTER_GED/AG100_003')

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

    def get_matched_c2_t1_rt_image(input_image):
        # Find Coll 2 T1 raw and RT image matching the Collection image
        #   based on the LANDSAT_SCENE_ID property
        scene_id = input_image.get('LANDSAT_SCENE_ID')
        landsat_bands = ['blue', 'green', 'red', 'nir', 'swir1', 'thermal', 'swir2']

        l4 = ee.ImageCollection('LANDSAT/LT04/C01/T1')
        l5 = ee.ImageCollection('LANDSAT/LT05/C02/T1')
        l7 = ee.ImageCollection('LANDSAT/LE07/C02/T1_RT')
        l8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_RT')
        l9 = ee.ImageCollection('LANDSAT/LC09/C02/T1')
        coll2 = l4.merge(l5).merge(l7).merge(l8).merge(l9)

        image_raw = coll2.filter(ee.Filter.eq('LANDSAT_SCENE_ID', scene_id)).first()

        l4_spacecraft_id = 'LANDSAT_4'
        l5_spacecraft_id = 'LANDSAT_5'
        l7_spacecraft_id = 'LANDSAT_7'
        l8_spacecraft_id = 'LANDSAT_8'
        l9_spacecraft_id = 'LANDSAT_9'

        ADD_THERMAL = {
            l4_spacecraft_id: image_raw.get('RADIANCE_ADD_BAND_6'),
            l5_spacecraft_id: image_raw.get('RADIANCE_ADD_BAND_6'),
            l7_spacecraft_id: image_raw.get('RADIANCE_ADD_BAND_6_VCID_1'),
            l8_spacecraft_id: image_raw.get('RADIANCE_ADD_BAND_10'),
            l9_spacecraft_id: image_raw.get('RADIANCE_ADD_BAND_10'),

        }
        MUL_THERMAL = {
            l4_spacecraft_id: image_raw.get('RADIANCE_MULT_BAND_6'),
            l5_spacecraft_id: image_raw.get('RADIANCE_MULT_BAND_6'),
            l7_spacecraft_id: image_raw.get('RADIANCE_MULT_BAND_6_VCID_1'),
            l8_spacecraft_id: image_raw.get('RADIANCE_MULT_BAND_10'),
            l9_spacecraft_id: image_raw.get('RADIANCE_MULT_BAND_10'),
        }

        def props(landsat):
            return {
                'RADIANCE_ADD_BAND_thermal': ADD_THERMAL[landsat],
                'RADIANCE_MULT_BAND_thermal': MUL_THERMAL[landsat],
            }

        rename_band = ee.Dictionary({
            l4_spacecraft_id: ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7'],
            l5_spacecraft_id: ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7'],
            l7_spacecraft_id: ['B1', 'B2', 'B3', 'B4', 'B5', 'B6_VCID_1', 'B7'],
            l8_spacecraft_id: ['B2', 'B3', 'B4', 'B5', 'B6', 'B10', 'B7'],
            l9_spacecraft_id: ['B2', 'B3', 'B4', 'B5', 'B6', 'B10', 'B7'],
        })
        set_prop = ee.Dictionary({
            l4_spacecraft_id: props(l4_spacecraft_id),
            l5_spacecraft_id: props(l5_spacecraft_id),
            l7_spacecraft_id: props(l7_spacecraft_id),
            l8_spacecraft_id: props(l8_spacecraft_id),
            l9_spacecraft_id: props(l9_spacecraft_id),
        })
        # TODO: Fix error when images that are in the T1_L2 collections but not in the T1,
        #  will fail with a .get() error because image_raw is 'None',
        #  could cause issues if trying to map over a collection
        satellite = image_raw.get('SPACECRAFT_ID')

        matched_image = image_raw.select(rename_band.get(satellite), landsat_bands)\
            .set(set_prop.get(satellite))

        return ee.Image(matched_image)

    def get_matched_c2_t1_image(input_image):
        # Find collection 2 tier 1 level 2 image matching the Collection image
        #   based on the LANDSAT_SCENE_ID property

        scene_id = input_image.get('LANDSAT_SCENE_ID')

        l4 = ee.ImageCollection('LANDSAT/LT04/C02/T1_L2')
        l5 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2')
        l7 = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
        l8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
        l9 = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
        coll2 = l4.merge(l5).merge(l7).merge(l8).merge(l9)

        matched_image = coll2.filter(ee.Filter.eq('LANDSAT_SCENE_ID', scene_id)).first()

        return ee.Image(matched_image)

    # Rebuilding the coll2 image here since the extra bands needed for the calculation
    #   will likely have been dropped or excluded before getting to this function
    coll2 = get_matched_c2_t1_image(sr_image)
    coll2RT = get_matched_c2_t1_rt_image(sr_image)

    # Apply Allen-Kilic Eq. 5 to calc. ASTER emiss. for Landsat
    # This is Eq. 4 of Malakar et al., 2018
    def ged_emis(ged_col):
        eb13 = ged_col.select('emissivity_band13').multiply(0.001)
        eb14 = ged_col.select('emissivity_band14').multiply(0.001)
        emAsLs = (
            eb13.multiply(ee.Number(c13.get(spacecraft_id)))
            .add(eb14.multiply(ee.Number(c14.get(spacecraft_id))))
            .add(ee.Number(c.get(spacecraft_id)))
            .rename('EmisAsL8')
        )
        return emAsLs

    l8_As_Em = ged_emis(ged)

    # Apply Eq. 4 and 3 of Allen-Kilic to estimate the ASTER emissivity for bare soil
    # (this is Eq. 5 of Malakar et al., 2018) with settings by Allen-Kilic.
    # This uses NDVI of ASTER over the same period as ASTER emissivity.
    fc_ASTER = ged.select(['ndvi']).multiply(0.01).subtract(0.15).divide(0.65).clamp(0, 1.0)

    # The 0.9798 is average from ASTER spectral response for bands 13/14 for vegetation
    # derived from Glynn Hulley (2023)
    # CGM - Reordered equation to avoid needing a constant image that would not have a projection
    #   X.multiply(-1).add(1) is equivalent to "1-X" or ee.Image.constant(1).subtract(X)
    em_soil = l8_As_Em.subtract(fc_ASTER.multiply(0.9798)).divide(fc_ASTER.multiply(-1).add(1))

    # Added accounting for instability in (1-fc_ASTER) denominator when fc_ASTER is large by fixing bare
    # component to spectral library emissivity of soil
    em_soil = em_soil.where(fc_ASTER.gt(0.8), soil_emiss_fill)

    # Fill in soil emissivity gaps using the footprint of the landsat NDVI image
    # Need to set flag for footprint to False since the footprint of the ASTER emissivity data is undefined
    fill_img = ndvi.multiply(0).add(soil_emiss_fill)
    em_soil = em_soil.unmask(fill_img, False)

    # Resample soil emissivity using bilinear interpolation
    em_soil = em_soil.resample('bilinear')

    # Apply Eq. 4 and 6 of Allen-Kilic to estimate Landsat-based emissivity
    # Using the ASTER-based soil emissivity from above
    # The following estimate for emissivity to use with Landsat may need to be clamped
    # to some predefined safe limits (for example, 0.5 and 1.0).
    fc_Landsat = ndvi.multiply(1.0).subtract(0.15).divide(0.65).clamp(0, 1.0)

    # calc_smoothed_em_soil
    em_soil_clipped = em_soil.clip(fc_Landsat.geometry())
    LS_EM = (
        fc_Landsat.multiply(-1).add(1).multiply(em_soil_clipped)
        .add(fc_Landsat.multiply(veg_emis))
    )
    # LS_EM = image.multiply(veg_emis)
    #     .add(ee.Image.constant(1).subtract(image).multiply(em_soil_smooth_clipped))

    # Apply Eq. 8 to get thermal surface radiance, Rc, from C2 Real time band 10
    # (Eq. 7 of Malakar et al. but without the emissivity to produce actual radiance)
    # def calc_Rc_smooth(LS_EM):
    Rc = (
        coll2RT.select(['thermal'])
        .multiply(ee.Number(coll2RT.get('RADIANCE_MULT_BAND_thermal')))
        .add(ee.Number(coll2RT.get('RADIANCE_ADD_BAND_thermal')))
        .subtract(coll2.select(['ST_URAD']).multiply(0.001))
        .divide(coll2.select(['ST_ATRAN']).multiply(0.0001))
        .subtract(LS_EM.multiply(-1).add(1).multiply(coll2.select(['ST_DRAD']).multiply(0.001)))
    )

    # Apply Eq. 7 to convert Rs to LST (similar to Malakar et al., but with emissivity)
    # def calc_LST_smooth(image):
    L8_LST = (
        LS_EM.multiply(ee.Number(k1.get(spacecraft_id)))
        .divide(Rc).add(1.0).log().pow(-1)
        .multiply(ee.Number(k2.get(spacecraft_id)))
    )
    # L8_LST = ee.Image.constant(ee.Number(k2.get(spacecraft_id))) \
    #     .divide(LS_EM.multiply(ee.Number(k1.get(spacecraft_id)))
    #             .divide(Rc_smooth).add(ee.Number(1.0)).log())

    return L8_LST.rename('surface_temperature')
    #     .set('system:time_start', image.get('system:time_start'))
