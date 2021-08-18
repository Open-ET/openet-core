import ee


def median_absolute_deviation(images, crop_mask, made_scale=2):
    """Median absolute deviation

    Parameters
    ----------
    images : list
    crop_mask : ee.Image
    made_scale : float, optional

    Returns
    -------
    ee.Image

    """
    # TODO: This should eventually change based on the image list size
    model_count = 6

    # CGM - For now assume SIMS has already been masked to crop areas
    # Compute a SIMS image for just crop pixels (mask out non agg for sims)
    # sims_crop = sims.updateMask(crop_mask)

    # Compute the Ensemble for all models and for SIMS only in crop pixels
    # ensemble_sims_crop = ee.Image([disalexi, eemetric, geesebal, ptjpl, sims_crop, ssebop])

    ensemble_sims_crop = ee.Image(images)

    # Compute simple mean, median, and MADe
    # ens_mean = ensemble_sims_crop.reduce(ee.Reducer.mean())\
    #     .rename(["mean"])
    ens_median = ensemble_sims_crop.reduce(ee.Reducer.median())\
        .rename(["median"])
    MADe = ensemble_sims_crop.subtract(ens_median).abs()\
        .reduce(ee.Reducer.median())\
        .multiply(1.4826).rename(["MADe"])

    # Calulate upper and lower bounds for outlier, based on median
    upper = ens_median.add(MADe.multiply(made_scale)).rename(["upper"])
    lower = ens_median.subtract(MADe.multiply(made_scale)).rename(["lower"])

    # Drop Counts
    count_sims = ensemble_sims_crop.lt(lower).add(ensemble_sims_crop.gt(upper))\
        .reduce(ee.Reducer.sum()).add(crop_mask.Not()).rename(["count"])
    count_img = ee.Image(model_count).subtract(count_sims).clamp(4, model_count)

    ens = ensemble_sims_crop.unmask(-9999).toArray()
    diff = ens.subtract(ens_median)
    # TODO: Is the first .toArray needed?  Isn't ens already an array?
    ens_sort = ens.toArray().arraySort(diff.abs().toArray())

    array_null = ee.Image.constant([-9999] * model_count)\
        .toArray()

    sort_img = ens_sort.arraySlice(0, 0, count_img).arrayCat(array_null, 0)\
        .arraySlice(0, 0, model_count)\
        .arrayFlatten([[f'B{b+1}' for b in range(model_count)]])

    model_drop_mean = sort_img.mask(sort_img.neq(-9999))\
        .reduce(ee.Reducer.mean())

    return model_drop_mean.rename(["ensemble"])

    # # CGM - Commented out returning model indices for now
    # index_array = ee.Image.constant([1, 2, 3, 4, 5, 6])\
    #     .rename(ensemble_sims_crop.bandNames()).toArray()
    # index_sort = index_array.arraySort(diff.abs().toArray())
    # index_img = index_sort.arraySlice(0, 0, count_img).arrayCat(array_null, 0)\
    #     .arraySlice(0, 0, 6).arrayFlatten([['B1', 'B2', 'B3', 'B4', 'B5', 'B6']])
    # index_img = index_img.mask(sort_img.neq(-9999))

    # # Add mean, ens_meidan, made, upper and lower to ensamble for map display
    # ensemble = ensemble_sims_crop.addBands(ens_mean).addBands(ens_median)
    #     .addBands(MADe).addBands(upper).addBands(lower)
    #     .addBands(model_drop_mean)


# CGM - Mean ensemble placeholder function
def mean(images, crop_mask=None):
    """

    Parameters
    ----------
    images
    crop_mask

    Returns
    -------
    ee.Image

    """
    ensemble_img = ee.Image(images)
    return ensemble_img.reduce(ee.Reducer.mean()).rename(['ensemble'])
