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

from model.modeling.salts import MEDIUM_SALTS


def test_medium_salts():
    assert len(MEDIUM_SALTS) > 2000
    assert len(MEDIUM_SALTS['75832']) == 2
    assert len(MEDIUM_SALTS['30808']) == 2
    assert len(MEDIUM_SALTS['86254']) == 4
