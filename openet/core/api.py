# import sys

import ee

# import openet.interp as interp


# class API():
#     """"""
#     def __init__(self):
#         """"""
#         pass


# TODO: Make this a class eventually
def collection(
        et_model,
        variable,
        collections,
        start_date,
        end_date,
        t_interval,
        geometry,
        **kwargs
        ):
    """Generic OpenET Collection

    Parameters
    ----------
    self :
    et_model : {'ndvi', 'ssebop'}
        ET model.
    variable : str

    collections : list
        GEE satellite image collection IDs.
    start_date : str
        ISO format inclusive start date (i.e. YYYY-MM-DD).
    end_date : str
        ISO format exclusive end date (i.e. YYYY-MM-DD).
    t_interval : {'daily', 'monthly', 'annual', 'overpass'}
        Time interval over which to interpolate and aggregate values.
        Selecting 'overpass' will return values only for the overpass dates.
    geometry : ee.Geometry
        The geometry object will be used to filter the input collections.
    kwargs :

    Returns
    -------
    ee.ImageCollection

    Notes
    -----
    The following is just a basic framework for what needs to happen to
        go from input parameters to an output image collection.
    A lot of this might make more sense in the init function above.

    """

    # Load the ET model
    if et_model.lower() == 'ndvi':

        # # DEADBEEF - Manually adding OpenET Model to system path
        # # This will eventually be handled by import openet modules
        # import os
        # model_path = os.path.dirname(os.path.dirname(os.path.dirname(
        #     os.path.abspath(os.path.realpath(__file__)))))
        # print(model_path)
        # sys.path.insert(0, os.path.join(model_path, 'openet-ndvi-test'))
        # print(sys.path)

        try:
            import openet.ndvi as model
        except ModuleNotFoundError:
            print(
                '\nThe ET model {} could not be imported'.format(et_model) +
                '\nPlease ensure that the model has been installed')
            return False
        except Exception as e:
            print('Unhandled Exception: {}'.format(e))
            raise

    elif et_model.lower() == 'ssebop':

        # # DEADBEEF - Manually adding OpenET Models to system path
        # # This will eventually be handled by import openet modules
        # import os
        # model_path = os.path.dirname(os.path.dirname(os.path.dirname(
        #     os.path.abspath(os.path.realpath(__file__)))))
        # print(model_path)
        # sys.path.insert(0, os.path.join(model_path, 'openet-ssebop-test'))

        try:
            import openet.ssebop as model
        except ModuleNotFoundError:
            print(
                '\nThe ET model {} could not be imported'.format(et_model) +
                '\nPlease ensure that the model has been installed')
            return False
        except Exception as e:
            print('Unhandled Exception: {}'.format(e))
            raise

    else:
        # CGM - This could just be a value error exception
        raise ValueError('unsupported et_model type')

    variable_coll = model.collection(
        variable,
        collections,
        start_date,
        end_date,
        t_interval,
        geometry,
        **kwargs
    )
    return variable_coll
