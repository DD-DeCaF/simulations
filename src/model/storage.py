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

import requests
from cobra.io.dict import model_from_dict

from model.app import app
from model.exceptions import Forbidden, ModelNotFound


logger = logging.getLogger(__name__)


class ModelWrapper:
    """A wrapper for a cobrapy model with some additional metadata."""

    def __init__(self, model, organism_id, biomass_reaction):
        """
        Parameters
        ----------
        model: cobra.Model
            A cobrapy model instance.
        organism_id: str
            A reference to the organism for which the given model belongs. The identifier is internal to the DD-DeCaF
            platform and references the `id` field in https://api.dd-decaf.eu/warehouse/organisms.
        biomass_reaction: str
            A string referencing the default biomass reaction in the given model.
        """
        self.model = model
        # Use the cplex solver for performance
        self.model.solver = 'cplex'
        self.organism_id = organism_id
        self.biomass_reaction = biomass_reaction


# Keep all loaded models in memory in this dictionary, keyed by our internal
# model storage primary key id.
_MODELS = {}


def get(model_id):
    """Return a ModelWrapper instance for the given model id"""
    # TODO(Ali): Accept token parameter to be used when querying the model storage with JWT.
    if model_id not in _MODELS:
        _load_model(model_id)
    return _MODELS[model_id]


def preload_public_models():
    """Retrieve all public models from storage and instantiate them in memory."""
    logger.info(f"Preloading all public models (this may take some time)")
    response = requests.get(f"{app.config['MODEL_WAREHOUSE_API']}/models")
    response.raise_for_status()
    for model in response.json():
        _load_model(model['id'])
    logger.info(f"Done preloading {len(response.json())} models")


def _load_model(model_id):
    logger.debug(f"Requesting model {model_id} from the model warehouse")
    response = requests.get(f"{app.config['MODEL_WAREHOUSE_API']}/models/{model_id}")

    if response.status_code == 404:
        raise ModelNotFound(f"No model with id {model_id}")
    elif response.status_code in (401, 403):
        raise Forbidden(f"Insufficient permissions to access model {model_id}")
    response.raise_for_status()

    logger.debug(f"Deserializing received model with cobrapy")
    model_data = response.json()
    _MODELS[model_id] = ModelWrapper(
        model_from_dict(model_data['model_serialized']),
        model_data['organism_id'],
        model_data['default_biomass_reaction'],
    )
