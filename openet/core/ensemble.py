import ee

from . import utils
# import openet.core.utils as utils


def mad(ensemble_img, made_scale=2):
    """Median absolute deviation

    Parameters
    ----------
    ensemble_img : ee.Image
    made_scale : float, optional

    Returns
    -------
    ee.Image

    """
    # TODO: Add checks on model count and minimum model count
    # TODO: Compute model_count dynamically
    model_count = 6
    # model_count = image.bandNames().size()
    min_model_count = 4

    ens_median = ensemble_img.reduce(ee.Reducer.median()).rename(["median"])
    MADe = ensemble_img.subtract(ens_median).abs()\
        .reduce(ee.Reducer.median()).multiply(1.4826)

    # Calulate upper and lower bounds for outlier, based on median
    upper = ens_median.add(MADe.multiply(made_scale)).rename(["upper"])
    lower = ens_median.subtract(MADe.multiply(made_scale)).rename(["lower"])

    # Count of ensemble values after applying MAD filtering
    # Note, this is not the final count of models used in the ensemble
    mad_count = ensemble_img.gte(lower).And(ensemble_img.lte(upper))\
        .reduce(ee.Reducer.sum())\
        .clamp(min_model_count, model_count)\
        .rename(["count"])

    ens_array = ensemble_img.unmask(-9999).toArray()
    diff_array = ens_array.subtract(ens_median)
    ens_sort = ens_array.arraySort(diff_array.abs())

    array_null = ee.Image.constant([-9999] * model_count).toArray()
    sort_img = ens_sort.arraySlice(0, 0, mad_count)\
        .arrayCat(array_null, 0).arraySlice(0, 0, model_count)\
        .arrayFlatten([[f'B{b+1}' for b in range(model_count)]])

    model_drop_mean = sort_img.mask(sort_img.neq(-9999))\
        .reduce(ee.Reducer.mean()).rename(["ensemble"])

    # DEADBEEF
    # print(utils.point_image_value(ee.Image(images), [-120, 39], scale=1))
    # print(utils.point_image_value(ens_median, [-120, 39], scale=1))
    # print(utils.point_image_value(MADe, [-120, 39], scale=1))
    # print(utils.point_image_value(upper, [-120, 39], scale=1))
    # print(utils.point_image_value(lower, [-120, 39], scale=1))
    # print(utils.point_image_value(count_img, [-120, 39], scale=1))
    # print(utils.point_image_value(sort_img, [-120, 39], scale=1))
    # print(utils.point_image_value(model_drop_mean, [-120, 39], scale=1))

    return model_drop_mean

    # # CGM - Commented out returning model indices for now
    # index_array = ee.Image.constant([1, 2, 3, 4, 5, 6])\
    #     .rename(ensemble_sims_crop.bandNames()).toArray()
    # index_sort = index_array.arraySort(diff.abs().toArray())
    # index_img = index_sort.arraySlice(0, 0, count_img).arrayCat(array_null, 0)\
    #     .arraySlice(0, 0, 6).arrayFlatten([['B1', 'B2', 'B3', 'B4', 'B5', 'B6']])
    # index_img = index_img.mask(sort_img.neq(-9999))

    # # Add mean, ens_meidan, made, upper and lower to ensamble for map display
    # ens_mean = ensemble_img.reduce(ee.Reducer.mean()).rename(["mean"])
    # ensemble = ensemble_sims_crop.addBands(ens_mean).addBands(ens_median)
    #     .addBands(MADe).addBands(upper).addBands(lower)
    #     .addBands(model_drop_mean)


# CGM - Mean ensemble placeholder function
def mean(images):
    """

    Parameters
    ----------
    images : list

    Returns
    -------
    ee.Image

    """
    ensemble_img = ee.Image(images)
    return ensemble_img.reduce(ee.Reducer.mean()).rename(['ensemble'])
