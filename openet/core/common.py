import re
import warnings

import ee


def landsat_c1_toa_cloud_mask(
        input_img,
        snow_flag=False,
        cirrus_flag=False,
        cloud_confidence=2,
        shadow_confidence=3,
        snow_confidence=3,
        cirrus_confidence=3,
        ):
    """Extract cloud mask from the Landsat Collection 1 TOA BQA band

    Parameters
    ----------
    input_img : ee.Image
        Image from a Landsat Collection 1 TOA collection with a BQA band
        (e.g. LANDSAT/LE07/C01/T1_TOA).
    snow_flag : bool
        If true, mask snow pixels (the default is False).
    cirrus_flag : bool
        If true, mask cirrus pixels (the default is False).
        Note, cirrus bits are only set for Landsat 8 (OLI) images.
    cloud_confidence : int
        Minimum cloud confidence value (the default is 2).
    shadow_confidence : int
        Minimum cloud confidence value (the default is 3).
    snow_confidence : int
        Minimum snow confidence value (the default is 3).  Only used if
        snow_flag is True.
    cirrus_confidence : int
        Minimum cirrus confidence value (the default is 3).  Only used if
        cirrus_flag is True.

    Returns
    -------
    ee.Image

    Notes
    -----
    Output image is structured to be applied directly with updateMask()
        i.e. 0 is cloud/masked, 1 is clear/unmasked

    Assuming Cloud must be set to check Cloud Confidence

    Bits
        0:     Designated Fill
        1:     Terrain Occlusion (OLI) / Dropped Pixel (TM, ETM+)
        2-3:   Radiometric Saturation
        4:     Cloud
        5-6:   Cloud Confidence
        7-8:   Cloud Shadow Confidence
        9-10:  Snow/Ice Confidence
        11-12: Cirrus Confidence (Landsat 8 only)

    Confidence values
        00: "Not Determined", algorithm did not determine the status of this
            condition
        01: "No", algorithm has low to no confidence that this condition exists
            (0-33 percent confidence)
        10: "Maybe", algorithm has medium confidence that this condition exists
            (34-66 percent confidence)
        11: "Yes", algorithm has high confidence that this condition exists
            (67-100 percent confidence)

    References
    ----------


    """
    qa_img = input_img.select(['BQA'])
    cloud_mask = qa_img.rightShift(4).bitwiseAnd(1).neq(0)\
        .And(qa_img.rightShift(5).bitwiseAnd(3).gte(cloud_confidence))\
        .Or(qa_img.rightShift(7).bitwiseAnd(3).gte(shadow_confidence))
    if snow_flag:
        cloud_mask = cloud_mask.Or(
            qa_img.rightShift(9).bitwiseAnd(3).gte(snow_confidence))
    if cirrus_flag:
        cloud_mask = cloud_mask.Or(
            qa_img.rightShift(11).bitwiseAnd(3).gte(cirrus_confidence))

    # Set cloudy pixels to 0 and clear to 1
    return cloud_mask.Not()


def landsat_c1_sr_cloud_mask(
        input_img,
        cloud_confidence=3,
        shadow_flag=True,
        snow_flag=False,
        ):
    """Extract cloud mask from the Landsat Collection 1 SR pixel_qa band

    Parameters
    ----------
    input_img : ee.Image
        Image from a Landsat Collection 1 SR image collection with a pixel_qa
        band (e.g. LANDSAT/LE07/C01/T1_SR).
    cloud_confidence : int
        Minimum cloud confidence value (the default is 3).
    shadow_flag : bool
        If true, mask shadow pixels (the default is True).
    snow_flag : bool
        If true, mask snow pixels (the default is False).

    Returns
    -------
    ee.Image

    Notes
    -----
    Output image is structured to be applied directly with updateMask()
        i.e. 0 is cloud/masked, 1 is clear/unmasked

    Assuming Cloud must be set to check Cloud Confidence

    Bits
        0: Fill
        1: Clear
        2: Water
        3: Cloud Shadow
        4: Snow
        5: Cloud
        6-7: Cloud Confidence

    Confidence values
        00: "None"
        01: "Low"
        10: "Medium"
        11: "High"

    References
    ----------

    """
    qa_img = input_img.select(['pixel_qa'])
    cloud_mask = qa_img.rightShift(5).bitwiseAnd(1).neq(0)\
        .And(qa_img.rightShift(6).bitwiseAnd(3).gte(cloud_confidence))
    if shadow_flag:
        cloud_mask = cloud_mask.Or(qa_img.rightShift(3).bitwiseAnd(1).neq(0))
    if snow_flag:
        cloud_mask = cloud_mask.Or(qa_img.rightShift(4).bitwiseAnd(1).neq(0))

    # Set cloudy pixels to 0 and clear to 1
    return cloud_mask.Not()


def landsat_c2_sr_cloud_mask(
        input_img,
        cirrus_flag=False,
        dilate_flag=False,
        shadow_flag=True,
        snow_flag=False,
        saturated_flag=False,
        # cloud_confidence=3,
        ):
    """Extract cloud mask from the Landsat Collection 2 SR QA_PIXEL band

    Parameters
    ----------
    input_img : ee.Image
        Image from a Landsat Collection 2 SR image collection
        with QA_PIXEL and QA_RADSAT bands (e.g. LANDSAT/LC08/C02/T1_L2).
    cirrus_flag : bool
        If true, mask cirrus pixels (the default is False).
        Note, cirrus bits are only set for Landsat 8 (OLI) images.
    dilate_flag : bool
        If true, mask dilated cloud pixels (the default is False).
    shadow_flag : bool
        If true, mask shadow pixels (the default is True).
    snow_flag : bool
        If true, mask snow pixels (the default is False).
    saturated_flag : bool
        If true, mask pixels that are saturated in any band
        (the default is False).

    Returns
    -------
    ee.Image

    Notes
    -----
    Output image is structured to be applied directly with updateMask()
        i.e. 0 is cloud/masked, 1 is clear/unmasked

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
    cloud_mask = qa_img.rightShift(3).bitwiseAnd(1).neq(0)
    #     .Or(qa_img.rightShift(8).bitwiseAnd(3).gte(cloud_confidence))
    if cirrus_flag:
        cloud_mask = cloud_mask.Or(qa_img.rightShift(2).bitwiseAnd(1).neq(0))
    if dilate_flag:
        cloud_mask = cloud_mask.Or(qa_img.rightShift(1).bitwiseAnd(1).neq(0))
    if shadow_flag:
        cloud_mask = cloud_mask.Or(qa_img.rightShift(4).bitwiseAnd(1).neq(0))
    if snow_flag:
        cloud_mask = cloud_mask.Or(qa_img.rightShift(5).bitwiseAnd(1).neq(0))

    if saturated_flag:
        # Masking if saturated in any band
        sat_mask = input_img.select(['QA_RADSAT']).gt(0)
        cloud_mask = cloud_mask.Or(sat_mask)

    # Flip to set cloudy pixels to 0 and clear to 1
    return cloud_mask.Not().rename(['cloud_mask'])


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
    return cloud_mask.Not()


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
    return cloud_mask.Not()


# def sentinel2_toa_cloud_mask(input_img):
#     # This function will be removed as of version 0.1
#     warnings.warn(
#         "common.sentinel2_toa_cloud_mask() is deprecated, "
#         "use common.sentinel2_cloud_mask() instead",
#         DeprecationWarning
#     )
#     return sentinel2_cloud_mask(input_img)


def landsat_c2_sr_lst_correct(sr_image, ndvi):
    """ Apply correction to Collection 2 LST by using ASTER emissivity and recalculating LST following the
    procedure in the white paper by R.Allen and A.Kilic (2022) that is based on
    Malakar, N.K., Hulley, G.C., Hook, S.J., Laraby, K., Cook, M. and Schott, J.R., 2018.
    An operational land surface temperature product for Landsat thermal data: Methodology and validation.
    IEEE Transactions on Geoscience and Remote Sensing, 56(10), pp.5717-5735.

    :param sr_image: Surface reflectance image [ee.Image]
    :param ndvi: NDVI image [ee.Image]
    :return: L8_LST_smooth: LST recalculated from smoothed emissivity [ee.Image]

    :authors: Peter ReVelle, Richard Allen, Ayse Kilic
    """
    spacecraft_id = ee.String(sr_image.get('SPACECRAFT_ID'))

    veg_emis = 0.99
    soil_emiss_fill = 0.97

    # Aster Global Emissivity Dataset
    ged = ee.Image("NASA/ASTER_GED/AG100_003")

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
    sr_image = sr_image \
        .set({
            'K1': ee.Number(k1.get(spacecraft_id)),
            'K2': ee.Number(k2.get(spacecraft_id)),
            'c13': ee.Number(c13.get(spacecraft_id)),
            'c14': ee.Number(c14.get(spacecraft_id)),
            'c': ee.Number(c.get(spacecraft_id))
        })

    def get_matched_c2_t1_rt_image(input_image):
        # Find Coll 2 T1 raw and RT image matching the Collection image
        #   based on the LANDSAT_SCENE_ID property
        scene_id = input_image.get('LANDSAT_SCENE_ID')
        landsat_bands = ['blue', 'green', 'red', 'nir', 'swir1', 'thermal', 'swir2']

        l4 = ee.ImageCollection('LANDSAT/LT04/C01/T1')
        l5 = ee.ImageCollection('LANDSAT/LT05/C02/T1')
        l7 = ee.ImageCollection('LANDSAT/LE07/C02/T1_RT')
        l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_RT")
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
            l9_spacecraft_id: image_raw.get('RADIANCE_ADD_BAND_10')

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
            l9_spacecraft_id: ['B2', 'B3', 'B4', 'B5', 'B6', 'B10', 'B7']})
        set_prop = ee.Dictionary({
            l4_spacecraft_id: props(l4_spacecraft_id),
            l5_spacecraft_id: props(l5_spacecraft_id),
            l7_spacecraft_id: props(l7_spacecraft_id),
            l8_spacecraft_id: props(l8_spacecraft_id),
            l9_spacecraft_id: props(l9_spacecraft_id)
        })
        # TODO: Fix error when images that are in the T1_L2 collections but not in the T1,
        #  will fail with a .get() error because image_raw is 'None',
        #  could cause issues if trying to map over a collection
        satellite = image_raw.get('SPACECRAFT_ID')

        matched_image = image_raw.select(rename_band.get(satellite), landsat_bands)\
            .set(set_prop.get(satellite))

        return ee.Image(matched_image)

    def get_matched_c2_t1_image(input_image):
        # Find Coll 2 T1 RT image matching the Collection image
        #   based on the LANDSAT_SCENE_ID property

        scene_id = input_image.get('LANDSAT_SCENE_ID')

        l4 = ee.ImageCollection('LANDSAT/LT04/C02/T1_L2')
        l5 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2')
        l7 = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
        l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
        coll2 = l4.merge(l5).merge(l7).merge(l8).merge(l9)

        matched_image = coll2.filter(ee.Filter.eq('LANDSAT_SCENE_ID', scene_id)).first()

        return ee.Image(matched_image)

    coll2RT = get_matched_c2_t1_rt_image(sr_image)
    coll2 = get_matched_c2_t1_image(sr_image)

    # Apply Allen-Kilic Eq. 5 to calc. ASTER emiss. for Landsat
    # This is Eq. 4 of Malakar et al., 2018
    def ged_emis(ged_col):
        eb13 = ged_col.select('emissivity_band13').multiply(0.001)
        eb14 = ged_col.select('emissivity_band14').multiply(0.001)
        emAsLs = (
            eb13.multiply(ee.Number(sr_image.get('c13')))
            .add(eb14.multiply(ee.Number(sr_image.get('c14'))))
            .add(ee.Number(sr_image.get('c')))
            .rename('EmisAsL8')
        )
        return emAsLs

    l8_As_Em = ged_emis(ged)

    # Apply Eq. 4 and 3 of Allen-Kilic to estimate the ASTER emissivity for bare soil
    # (this is Eq. 5 of Malakar et al., 2018)
    # with settings by Allen-Kilic. This uses NDVI of ASTER over the same period as ASTER emissivity.
    fc_ASTER = ged.select(['ndvi']).multiply(0.01).subtract(0.15).divide(0.65).clamp(0, 1.0)

    denom = fc_ASTER.multiply(-1).add(1)
    # denom = ee.Image.constant(1).subtract(fc_ASTER)
    # The 0.9798 is average from ASTER spectral response for bands 13/14 for vegetation derived
    # from Glynn Hulley (2023)
    em_soil = l8_As_Em.subtract(fc_ASTER.multiply(0.9798)).divide(denom)

    # Added accounting for instability in (1-fc_ASTER) denominator when fc_ASTER is large by fixing bare
    # component to spectral library emissivity of soil
    em_soil = em_soil.where(fc_ASTER.gt(0.8), soil_emiss_fill)

    # Fill in soil emissivity gaps using the footprint of the landsat NDVI image
    # Need to set flag for footprint to False since the footprint of the ASTER emissivity data is undefined
    fill_img = ndvi.multiply(0).add(soil_emiss_fill)
    em_soil = em_soil.unmask(fill_img, False)

    # Resample soil emissivity using bilinear interpolation
    em_soil = em_soil.resample("bilinear")

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
        LS_EM.multiply(ee.Number(sr_image.get('K1')))
        .divide(Rc).add(1.0).log().pow(-1)
        .multiply(ee.Number(sr_image.get('K2')))
    )
    # L8_LST = ee.Image.constant(sr_image.get('K2')) \
    #     .divide(LS_EM.multiply(ee.Number(sr_image.get('K1')))
    #             .divide(Rc_smooth).add(ee.Number(1.0)).log())

    return L8_LST.rename('surface_temperature')
    #     .set('system:time_start', image.get('system:time_start'))
