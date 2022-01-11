import warnings

import ee


def landsat_c1_toa_cloud_mask(input_img, snow_flag=False, cirrus_flag=False,
                              cloud_confidence=2, shadow_confidence=3,
                              snow_confidence=3, cirrus_confidence=3):
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


def landsat_c1_sr_cloud_mask(input_img, cloud_confidence=3,
                             shadow_flag=True, snow_flag=False):
    """Extract cloud mask from the Landsat Collection 1 SR pixel_qa band

    Parameters
    ----------
    img : ee.Image
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


def landsat_c2_sr_cloud_mask(input_img, cirrus_flag=False, dilate_flag=False,
                             shadow_flag=True, snow_flag=False,
                             ):
    """Extract cloud mask from the Landsat Collection 2 SR QA_PIXEL band

    Parameters
    ----------
    img : ee.Image
        Image from a Landsat Collection 2 SR image collection with a QA_PIXEL
        band (e.g. LANDSAT/LC08/C02/T1_L2).
    cirrus_flag : bool
        If true, mask cirrus pixels (the default is False).
        Note, cirrus bits are only set for Landsat 8 (OLI) images.
    dilate_flag : bool
        If true, mask dilated cloud pixels (the default is False).
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
    #     .And(qa_img.rightShift(8).bitwiseAnd(3).gte(cloud_confidence))
    if cirrus_flag:
        cloud_mask = cloud_mask.Or(qa_img.rightShift(2).bitwiseAnd(1).neq(0))
    if dilate_flag:
        cloud_mask = cloud_mask.Or(qa_img.rightShift(1).bitwiseAnd(1).neq(0))
    if shadow_flag:
        cloud_mask = cloud_mask.Or(qa_img.rightShift(4).bitwiseAnd(1).neq(0))
    if snow_flag:
        cloud_mask = cloud_mask.Or(qa_img.rightShift(5).bitwiseAnd(1).neq(0))

    # Flip to set cloudy pixels to 0 and clear to 1
    return cloud_mask.Not()


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
