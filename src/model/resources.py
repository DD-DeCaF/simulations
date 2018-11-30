# Copyright 2018 Novo Nordisk Foundation Center for Biosustainability, DTU.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

from cobra.io.dict import model_from_dict, model_to_dict
from flask import Response, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest
from prometheus_client.multiprocess import MultiProcessCollector

from model import deltas, storage
from model.adapter import adapt_from_genotype, adapt_from_measurements, adapt_from_medium
from model.exceptions import Forbidden, ModelNotFound, Unauthorized
from model.operations import apply_operations
from model.simulations import simulate


logger = logging.getLogger(__name__)


def model_get_modified(model_id):
    if not request.is_json:
        return "Non-JSON request content is not supported", 415

    try:
        model_wrapper = storage.get(model_id)
    except Unauthorized as error:
        return error.message, 401
    except Forbidden as error:
        return error.message, 403
    except ModelNotFound as error:
        return error.message, 404

    # Make a copy of the shared model instance for this request. It is not sufficient to use the cobra model context
    # manager here, as long as we're using async gunicorn workers and app state can be shared between requests.
    # This is an expensive operation, it can take a few seconds for large models.
    model = model_wrapper.model.copy()

    try:
        apply_operations(model, request.json['operations'])
    except KeyError:
        return "Missing field 'operations'", 400

    return jsonify(model_to_dict(model))


def model_modify(model_id):
    if not request.is_json:
        return "Non-JSON request content is not supported", 415

    try:
        model_wrapper = storage.get(model_id)
    except Unauthorized as error:
        return error.message, 401
    except Forbidden as error:
        return error.message, 403
    except ModelNotFound as error:
        return error.message, 404

    # Make a copy of the shared model instance for this request. It is not sufficient to use the cobra model context
    # manager here, as long as we're using async gunicorn workers and app state can be shared between requests.
    # This is an expensive operation, it can take a few seconds for large models.
    model = model_wrapper.model.copy()

    try:
        conditions = request.json['conditions']
    except KeyError:
        return "Missing field 'conditions'", 400

    # Build list of operations to perform on the model
    operations = []
    errors = []
    if 'medium' in conditions:
        operations_medium, errors_medium = adapt_from_medium(model, conditions['medium'])
        operations.extend(operations_medium)
        errors.extend(errors_medium)

    if 'genotype' in conditions:
        operations_genotype, errors_genotype = adapt_from_genotype(model, conditions['genotype'])
        operations.extend(operations_genotype)
        errors.extend(errors_genotype)

    if 'measurements' in conditions:
        operations_measurements, errors_measurements = adapt_from_measurements(model, model_wrapper.biomass_reaction,
                                                                               conditions['measurements'])
        operations.extend(operations_measurements)
        errors.extend(errors_measurements)

    if errors:
        # If any errors occured during modifications, discard generated operations and return the error messages to the
        # client for follow-up
        return jsonify({'errors': errors})
    else:
        delta_id = deltas.save(model.id, conditions, operations)
        return jsonify({'id': delta_id, 'operations': operations})


def model_simulate():
    if not request.is_json:
        return "Non-JSON request content is not supported", 415

    if 'model_id' in request.json:
        # Client provided an identifier to some model in the model storage service, retrieve it
        logger.debug(f"Simulating model by id {request.json['model_id']}")

        try:
            model_wrapper = storage.get(request.json['model_id'])
            biomass_reaction = model_wrapper.biomass_reaction
        except Unauthorized as error:
            return error.message, 401
        except Forbidden as error:
            return error.message, 403
        except ModelNotFound as error:
            return error.message, 404

        # Make a copy of the shared model instance for this request. It is not sufficient to use the cobra model context
        # manager here, as long as we're using async gunicorn workers and app state can be shared between requests.
        # This is an expensive operation, it can take a few seconds for large models.
        model = model_wrapper.model.copy()
    elif 'model' in request.json:
        # Client provided a full custom model and biomass reaction
        logger.debug("Simulating ad-hoc model provided by client")

        try:
            model_dict = request.json['model']
            model = model_from_dict(model_dict)
        except Exception as error:
            logger.warning(f"Cobrapy could not deserialize provided model: {str(error)}", exc_info=True)
            logger.debug(f"Full serialized model: {model_dict}")
            return f"The provided model is not deserializable by cobrapy", 400
        try:
            biomass_reaction = request.json['biomass_reaction']
        except KeyError:
            return f"Missing field 'biomass_reaction'", 400
        else:
            if not model.reactions.has_id(biomass_reaction):
                return f"There is no biomass reaction with id '{biomass_reaction}' in the model", 400
    else:
        return f"Missing field 'model' or 'model_id'", 400

    operations = []

    if 'delta_id' in request.json:
        delta_id = request.json['delta_id']
        try:
            operations.extend(deltas.load_from_key(delta_id))
        except KeyError:
            return f"Cannot find delta id '{delta_id}'", 404

    if 'operations' in request.json:
        operations.extend(request.json['operations'])

    apply_operations(model, operations)

    # Parse solver request args and set defaults
    method = request.json.get('method', 'fba')
    objective_id = request.json.get('objective')
    objective_direction = request.json.get('objective_direction')

    flux_distribution, growth_rate = simulate(model, biomass_reaction, method, objective_id, objective_direction)
    return jsonify({'flux_distribution': flux_distribution, 'growth_rate': growth_rate})


def metrics():
    return Response(generate_latest(MultiProcessCollector(CollectorRegistry())), mimetype=CONTENT_TYPE_LATEST)


def healthz():
    """
    HTTP endpoint for readiness probes.

    Return an empty response. This response will not be ready until the application has finished initializing, e.g.,
    preloading models, which takes a few minutes.
    """
    return ""