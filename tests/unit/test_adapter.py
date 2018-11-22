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

from model.adapter import adapt_from_genotype, adapt_from_measurements, adapt_from_medium
from model.ice_client import ICE


def test_medium_adapter(iJO1366):
    iJO1366, biomass_reaction = iJO1366
    medium = [
        {'id': 'chebi:63041'},
        {'id': 'chebi:91249'},
        {'id': 'chebi:86244'},
        {'id': 'chebi:131387'},
    ]
    operations, errors = adapt_from_medium(iJO1366, medium)
    assert len(errors) == 5
    assert set(iJO1366.medium) == {'EX_fe3_e', 'EX_h2o_e', 'EX_mobd_e', 'EX_nh4_e', 'EX_so4_e', 'EX_ni2_e', 'EX_mn2_e', 'EX_cl_e'}  # noqa
    assert all(iJO1366.reactions.get_by_id(r).lower_bound == -1000 for r in iJO1366.medium)


def test_genotype_adapter(monkeypatch, iJO1366):
    iJO1366, biomass_reaction = iJO1366

    # Disable GPR queries for efficiency
    monkeypatch.setattr(ICE, 'get_reaction_equations', lambda self, genotype: {})

    genotype_changes = ['+Aac', '-pta']
    operations, errors = adapt_from_genotype(iJO1366, genotype_changes)
    assert len(operations) == 1
    assert len(errors) == 0


def test_measurements_adapter(iJO1366):
    iJO1366, biomass_reaction = iJO1366
    measurements = [
        {'type': 'compound', 'id': 'chebi:42758', 'unit': 'mmol', 'name': 'aldehydo-D-glucose', 'measurements': [-9.0]},
        {'type': 'compound', 'id': 'chebi:16236', 'unit': 'mmol', 'name': 'ethanol', 'measurements': [5.0, 4.8, 5.2, 4.9]},  # noqa
        {'type': 'reaction', 'id': 'PFK', 'measurements': [5, 4.8, 7]},
        {'type': 'reaction', 'id': 'PGK', 'measurements': [5, 5]},
    ]
    operations, errors = adapt_from_measurements(iJO1366, biomass_reaction, measurements)
    assert len(operations) == 4
    assert len(errors) == 0
