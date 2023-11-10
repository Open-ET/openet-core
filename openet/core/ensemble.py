import ee

# from . import utils
# # import openet.core.utils as utils

model_index = {
    'disalexi': 1,
    'eemetric': 2,
    'geesebal': 3,
    'ptjpl': 4,
    'sims': 5,
    'ssebop': 6,
}


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
    # TODO:

    # TODO: Add checks on model count and minimum model count
    # TODO: Compute model_count dynamically
    # TODO: Change the model_count and range() based lists to server side calls
    model_names = ensemble_img.bandNames()
    model_count = model_names.size()
    min_model_count = model_count.min(4)

    # Map the model index to a generic "BX" band name for the output images
    output_bands = ee.List.sequence(1, model_count)\
        .map(lambda x: ee.String('B').cat(ee.Number(x).format('%d')))

    ens_median = ensemble_img.reduce(ee.Reducer.median()).rename(["median"])
    MADe = ensemble_img.subtract(ens_median).abs()\
        .reduce(ee.Reducer.median()).multiply(1.4826)

    # Calculate upper and lower bounds for outlier, based on median
    upper = ens_median.add(MADe.multiply(made_scale)).rename(["upper"])
    lower = ens_median.subtract(MADe.multiply(made_scale)).rename(["lower"])

    # Count of ensemble values after applying MAD filtering
    # Note, this is not the final count of models used in the ensemble
    mad_count = (
        ensemble_img.gte(lower).And(ensemble_img.lte(upper))
        .reduce(ee.Reducer.sum())
        .clamp(min_model_count, model_count)
        .rename(["count"])
    )

    ens_array = ensemble_img.unmask(-9999).toArray()
    diff_array = ens_array.subtract(ens_median)

    mad_img = (
        ens_array.arraySort(diff_array.abs())
        .arraySlice(0, 0, mad_count)
        .arrayCat(ee.Array(-9999).repeat(0, model_count), 0)
        .arraySlice(0, 0, model_count)
        .arrayFlatten([output_bands])
    )
    mad_img = mad_img.mask(mad_img.neq(-9999))

    # TODO: Add a flag or parameter for returning additional bands
    # TODO: Move the model bit image
    output_img = (
        mad_img
        .reduce(ee.Reducer.mean()
                .combine(ee.Reducer.min(), sharedInputs=True)
                .combine(ee.Reducer.max(), sharedInputs=True)
                .combine(ee.Reducer.count(), sharedInputs=True))\
        .rename(["ensemble_mad", "ensemble_mad_min", "ensemble_mad_max",
                 "ensemble_mad_count"])
    )

    # Map the band names to the model index
    # The extra combine is to try and account for the ensemble images having
    #   band names that don't map to one of the model names/indexes
    # band_dict = ee.Dictionary(model_index)
    band_dict = ee.Dictionary(model_index).combine(ee.Dictionary.fromLists(
        output_bands, ee.List.sequence(9, model_count.add(9).subtract(1))))
    band_index = model_names.map(lambda x: band_dict.get(x))
    # band_index = ee.List.sequence(1, model_count)

    # Bit encode the models using the model index values
    # Build the index array from the ensemble images so that the index
    #   is masked the same
    index_array = (
        ensemble_img.multiply(0).add(ee.Image.constant(band_index))
        .unmask(-9999).toArray()
    )
    index_img = (
        index_array.arraySort(diff_array.abs())
        .arraySlice(0, 0, mad_count)
        .arrayCat(ee.Array(-9999).repeat(0, model_count), 0)
        .arraySlice(0, 0, model_count)
        .arrayFlatten([output_bands])
    )
    index_img = index_img.mask(index_img.neq(-9999))
    index_img = index_img.multiply(0).add(2).pow(index_img.subtract(1))\
        .reduce(ee.Reducer.sum()).int().rename(['ensemble_mad_index'])
    output_img = output_img.addBands(index_img)

    return output_img

    # DEADBEEF
    # print(utils.point_image_value(ee.Image(images), [-120, 39], scale=1))
    # print(utils.point_image_value(ens_median, [-120, 39], scale=1))
    # print(utils.point_image_value(MADe, [-120, 39], scale=1))
    # print(utils.point_image_value(upper, [-120, 39], scale=1))
    # print(utils.point_image_value(lower, [-120, 39], scale=1))
    # print(utils.point_image_value(count_img, [-120, 39], scale=1))
    # print(utils.point_image_value(sort_img, [-120, 39], scale=1))
    # print(utils.point_image_value(model_drop_mean, [-120, 39], scale=1))

    # # Add mean, ens_median, made, upper and lower to ensemble for map display
    # ens_mean = ensemble_img.reduce(ee.Reducer.mean()).rename(["mean"])
    # ensemble = ensemble_sims_crop.addBands(ens_mean).addBands(ens_median)
    #     .addBands(MADe).addBands(upper).addBands(lower)
    #     .addBands(model_drop_mean)


def mean(ensemble_img):
    """Simple arithmetic mean placeholder function

    Parameters
    ----------
    ensemble_img : ee.Image

    Returns
    -------
    ee.Image

    """
    return ensemble_img.reduce(ee.Reducer.mean()).rename(['ensemble_sam'])
