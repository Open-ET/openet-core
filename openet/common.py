import ee


def landsat_bqa_cloud_mask_func(img):
    """Extract Landsat Collection 1 cloud mask from the BQA band

    Parameters
    ----------
    img : ee.Image

    Returns
    -------
    ee.Image

    Notes
    -----
    Output image is structured to be applied directly with updateMask()
      i.e. 0 is cloud, 1 is cloud free

    https://landsat.usgs.gov/collectionqualityband
    https://code.earthengine.google.com/356a3580096cca315785d0859459abbd

    Confidence values
    00 = "Not Determined" = Algorithm did not determine the status of this condition
    01 = "No" = Algorithm has low to no confidence that this condition exists (0-33 percent confidence)
    10 = "Maybe" = Algorithm has medium confidence that this condition exists (34-66 percent confidence)
    11 = "Yes" = Algorithm has high confidence that this condition exists (67-100 percent confidence

    """
    qa_img = ee.Image(img.select(['BQA']))

    # Extracting cloud masks from BQA using rightShift() and  bitwiseAnd()
    # Cloud (med & high confidence), then snow, then shadow, then fill
    # Low confidence clouds tend to be the FMask buffer
    cloud_mask = qa_img.rightShift(4).bitwiseAnd(1).neq(0) \
        .And(qa_img.rightShift(5).bitwiseAnd(3).gte(2)) \
        .Or(qa_img.rightShift(7).bitwiseAnd(3).gte(3)) \
        .Or(qa_img.rightShift(9).bitwiseAnd(3).gte(3)) \
        .Or(qa_img.rightShift(11).bitwiseAnd(3).gte(3))

    return cloud_mask.Not()
