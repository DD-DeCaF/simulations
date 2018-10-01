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

"""Expose the main Flask-RESTPlus application."""

import logging
import logging.config

from flask import Flask
from flask_cors import CORS
from raven.contrib.flask import Sentry
from werkzeug.contrib.fixers import ProxyFix

from model.settings import Settings


app = Flask(__name__)
app.config.from_object(Settings())
app.wsgi_app = ProxyFix(app.wsgi_app)


def init_app(application, interface):
    """Initialize the main app with config information and routes."""
    # Configure logging
    logging.config.dictConfig(application.config['LOGGING'])

    # Configure middleware
    from model import middleware
    middleware.init_app(application)

    # Configure Sentry
    if application.config['SENTRY_DSN']:
        sentry = Sentry(dsn=application.config['SENTRY_DSN'], logging=True,
                        level=logging.WARNING)
        sentry.init_app(application)

    # Add routes and resources.
    # TODO: use flask-restplus
    from model import resources
    app.add_url_rule('/models/<model_id>', view_func=resources.model_get_modified, methods=['POST'])
    app.add_url_rule('/models/<model_id>/modify', view_func=resources.model_modify, methods=['POST'])
    app.add_url_rule('/simulate', view_func=resources.model_simulate, methods=['POST'])
    app.add_url_rule('/metrics', view_func=resources.metrics)
    app.add_url_rule('/healthz', view_func=resources.healthz)

    # Add CORS information for all resources.
    CORS(application)

    # Preload all models in production/staging environments
    from model import storage
    if app.config['ENVIRONMENT'] in ('production', 'staging'):
        storage.preload_public_models()
