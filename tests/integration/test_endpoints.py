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

"""Test local HTTP endpoints"""

from collections import namedtuple

import pytest
import requests

from simulations.ice_client import ICE


MEASUREMENTS = [
    {
        "id": "CHEBI:42758",
        "namespace": "chebi",
        "measurements": [-9.0],
        "type": "compound",
    },
    {
        "id": "CHEBI:16236",
        "namespace": "chebi",
        "measurements": [5.0, 4.8, 5.2, 4.9],
        "type": "compound",
    },
    {
        "id": "PFK",
        "namespace": "bigg.reaction",
        "measurements": [5, 5],
        "type": "reaction",
    },
]


def test_simulate_wrong_id(monkeypatch, client):
    # Mock `requests` to skip the external API request
    Response = namedtuple("Response", ["status_code"])
    monkeypatch.setattr(
        requests, "get", lambda *args, **kwargs: Response(status_code=404)
    )
    response = client.post("/simulate", json={"model_id": 404, "message": {}})
    assert response.status_code == 404


def test_simulate_unauthorized(client, models):
    response = client.post(
        "/simulate", json={"model_id": models["e_coli_core_proprietary"]}
    )
    assert response.status_code == 403


def test_simulate_no_operations(client, models):
    response = client.post("/simulate", json={"model_id": models["iJO1366"]})
    assert response.status_code == 200
    assert response.json["status"] == "optimal"


def test_simulate_infeasible(client, models):
    measurements = [
        {
            "id": "BIOMASS_Ec_iJO1366_core_53p95M",
            "namespace": "bigg.reaction",
            # Force an impossible growth to ensure infeasability
            "measurements": [1000],
            "type": "reaction",
        }
    ]
    response = client.post(
        f"/models/{models['iJO1366']}/modify", json={"measurements": measurements}
    )
    assert response.status_code == 200

    operations = response.json["operations"]
    response = client.post(
        "/simulate", json={"model_id": models["iJO1366"], "operations": operations}
    )
    assert response.status_code == 200
    assert response.json["status"] == "infeasible"


def test_simulate_fluxomics(monkeypatch, client, models):
    response = client.post(
        f"/models/{models['iJO1366']}/modify", json={"measurements": MEASUREMENTS}
    )
    assert response.status_code == 200

    operations = response.json["operations"]
    response = client.post(
        "/simulate", json={"model_id": models["iJO1366"], "operations": operations}
    )
    assert response.status_code == 200
    assert response.json["status"] == "optimal"
    assert response.json["flux_distribution"]["EX_glc__D_e"] == -9.0
    assert (
        abs(response.json["flux_distribution"]["EX_etoh_e"] - 4.64) < 0.001
    )  # lower bound
    assert response.json["flux_distribution"]["PFK"] == pytest.approx(5)


def test_simulate_modify(monkeypatch, client, models):
    # Disable GPR queries for efficiency
    monkeypatch.setattr(ICE, "get_reaction_equations", lambda self, genotype: {})

    conditions = {"measurements": MEASUREMENTS, "genotype": ["+Aac", "-pta"]}
    response = client.post(f"/models/{models['iJO1366']}/modify", json=conditions)
    assert response.status_code == 200

    operations = response.json["operations"]
    assert any(
        [
            op["operation"] == "knockout"
            and op["type"] == "gene"
            and op["id"] == "b2297"
            for op in operations
        ]
    )
    assert any(
        [
            op["operation"] == "modify"
            and op["type"] == "reaction"
            and op["id"] == "EX_etoh_e"
            for op in operations
        ]
    )
    assert any(
        [
            op["operation"] == "modify"
            and op["type"] == "reaction"
            and op["id"] == "PFK"
            for op in operations
        ]
    )

    response = client.post(
        "/simulate",
        json={
            "model_id": models["iJO1366"],
            "method": "pfba",
            "operations": operations,
        },
    )
    assert response.status_code == 200
    assert response.json["status"] == "optimal"
    fluxes = response.json["flux_distribution"]

    assert fluxes["EX_glc__D_e"] == -9.0
    assert abs(fluxes["EX_etoh_e"] - 4.64) < 0.001  # lower bound
    assert fluxes["PFK"] == pytest.approx(5)


def test_simulate_different_objective(client, models):
    response = client.post(
        "/simulate", json={"model_id": models["iJO1366"], "objective_id": "EX_etoh_e"}
    )
    assert response.status_code == 200
    result = response.json
    assert result["status"] == "optimal"
    assert abs(result["flux_distribution"]["EX_etoh_e"]) == pytest.approx(20)

    response = client.post("/simulate", json={"model_id": models["iJO1366"]})
    assert response.status_code == 200
    result = response.json
    assert result["status"] == "optimal"
    assert abs(result["flux_distribution"]["EX_etoh_e"]) == pytest.approx(0)


def test_modify(monkeypatch, client, models):
    # Disable GPR queries for efficiency
    monkeypatch.setattr(ICE, "get_reaction_equations", lambda self, genotype: {})

    response = client.post(
        f"/models/{models['iJO1366']}/modify",
        json={
            "medium": [
                {"id": "CHEBI:44080", "namespace": "chebi"},
                {"id": "CHEBI:15075", "namespace": "chebi"},
                {"id": "CHEBI:15377", "namespace": "chebi"},
                {"id": "CHEBI:15378", "namespace": "chebi"},
                {"id": "CHEBI:15379", "namespace": "chebi"},
                {"id": "CHEBI:15982", "namespace": "chebi"},
                {"id": "CHEBI:16189", "namespace": "chebi"},
                {"id": "CHEBI:16526", "namespace": "chebi"},
                {"id": "CHEBI:16643", "namespace": "chebi"},
                {"id": "CHEBI:17883", "namespace": "chebi"},
                {"id": "CHEBI:18212", "namespace": "chebi"},
                {"id": "CHEBI:18367", "namespace": "chebi"},
                {"id": "CHEBI:18420", "namespace": "chebi"},
                {"id": "CHEBI:25371", "namespace": "chebi"},
                {"id": "CHEBI:27638", "namespace": "chebi"},
                {"id": "CHEBI:28938", "namespace": "chebi"},
                {"id": "CHEBI:29033", "namespace": "chebi"},
                {"id": "CHEBI:29034", "namespace": "chebi"},
                {"id": "CHEBI:29035", "namespace": "chebi"},
                {"id": "CHEBI:29036", "namespace": "chebi"},
                {"id": "CHEBI:29101", "namespace": "chebi"},
                {"id": "CHEBI:29103", "namespace": "chebi"},
                {"id": "CHEBI:29105", "namespace": "chebi"},
                {"id": "CHEBI:29108", "namespace": "chebi"},
                {"id": "CHEBI:36271", "namespace": "chebi"},
                {"id": "CHEBI:42758", "namespace": "chebi"},
                {"id": "CHEBI:49786", "namespace": "chebi"},
            ],
            "genotype": ["+Aac", "-pta"],
            "measurements": [
                {
                    "type": "compound",
                    "id": "CHEBI:42758",
                    "namespace": "chebi",
                    "measurements": [-9.0],
                },
                {
                    "type": "compound",
                    "id": "CHEBI:16236",
                    "namespace": "chebi",
                    "measurements": [5.0, 4.8, 5.2, 4.9],
                },
                {
                    "type": "reaction",
                    "id": "PFK",
                    "namespace": "bigg.reaction",
                    "measurements": [5, 4.8, 7],
                },
                {
                    "type": "reaction",
                    "id": "PGK",
                    "namespace": "bigg.reaction",
                    "measurements": [5, 5],
                },
            ],
        },
    )
    assert response.status_code == 200
    assert len(response.json["operations"]) == 329


def test_prokaryomics_md120_bw25113(client, models):
    """Test constraining and simulating a model with a real data set"""
    data = {
        "medium": [
            {"id": "CHEBI:131527", "namespace": "chebi"},
            {"id": "CHEBI:3312", "namespace": "chebi"},
            {"id": "CHEBI:16015", "namespace": "chebi"},
            {"id": "CHEBI:26710", "namespace": "chebi"},
            {"id": "CHEBI:30808", "namespace": "chebi"},
            {"id": "CHEBI:32599", "namespace": "chebi"},
            {"id": "CHEBI:34683", "namespace": "chebi"},
            {"id": "CHEBI:35696", "namespace": "chebi"},
            {"id": "CHEBI:42758", "namespace": "chebi"},
            {"id": "CHEBI:49553", "namespace": "chebi"},
            {"id": "CHEBI:49976", "namespace": "chebi"},
            {"id": "CHEBI:62946", "namespace": "chebi"},
            {"id": "CHEBI:63041", "namespace": "chebi"},
            {"id": "CHEBI:63043", "namespace": "chebi"},
            {"id": "CHEBI:75215", "namespace": "chebi"},
        ],
        "measurements": [
            {
                "id": "CS",
                "namespace": "bigg.reaction",
                "measurements": [7.2],
                "type": "reaction",
            },
            {
                "id": "FBA",
                "namespace": "bigg.reaction",
                "measurements": [7.9],
                "type": "reaction",
            },
            {
                "id": "PFK",
                "namespace": "bigg.reaction",
                "measurements": [7.9],
                "type": "reaction",
            },
            {
                "id": "FUM",
                "namespace": "bigg.reaction",
                "measurements": [6.7],
                "type": "reaction",
            },
            {
                "id": "GAPD",
                "namespace": "bigg.reaction",
                "measurements": [16.8],
                "type": "reaction",
            },
            {
                "id": "G6PDH2r",
                "namespace": "bigg.reaction",
                "measurements": [4.6],
                "type": "reaction",
            },
            {
                "id": "PGI",
                "namespace": "bigg.reaction",
                "measurements": [5.3],
                "type": "reaction",
            },
            {
                "id": "GLCptspp",
                "namespace": "bigg.reaction",
                "measurements": [10.0],
                "type": "reaction",
            },
            {
                "id": "ME1",
                "namespace": "bigg.reaction",
                "measurements": [0.3],
                "type": "reaction",
            },
            {
                "id": "ME2",
                "namespace": "bigg.reaction",
                "measurements": [0.3],
                "type": "reaction",
            },
            {
                "id": "MDH",
                "namespace": "bigg.reaction",
                "measurements": [6.5],
                "type": "reaction",
            },
            {
                "id": "PYK",
                "namespace": "bigg.reaction",
                "measurements": [12.0],
                "type": "reaction",
            },
            {
                "id": "PPC",
                "namespace": "bigg.reaction",
                "measurements": [3.0],
                "type": "reaction",
            },
            {
                "id": "PPCK",
                "namespace": "bigg.reaction",
                "measurements": [3.0],
                "type": "reaction",
            },
            {
                "id": "PDH",
                "namespace": "bigg.reaction",
                "measurements": [9.4],
                "type": "reaction",
            },
            {
                "id": "TKT1",
                "namespace": "bigg.reaction",
                "measurements": [1.5],
                "type": "reaction",
            },
            {
                "id": "TALA",
                "namespace": "bigg.reaction",
                "measurements": [1.5],
                "type": "reaction",
            },
            {
                "id": "TKT2",
                "namespace": "bigg.reaction",
                "measurements": [1.1],
                "type": "reaction",
            },
        ],
        "genotype": ["-b3643,-b0062,-b0063,-b0061,-b4350,-b3902,-b3903"],
    }

    response = client.post(f"/models/{models['iJO1366']}/modify", json=data)
    assert response.status_code == 200

    response = client.post(
        "/simulate",
        json={"model_id": models["iJO1366"], "operations": response.json["operations"]},
    )
    assert response.status_code == 200
    assert response.json["status"] == "optimal"
    assert response.json["growth_rate"] == pytest.approx(0.5134445454218568)


def test_growth_rate_measurement(client, models):
    """Constrain the model with a single growth rate measurement."""
    data = {"growth_rate": {"measurements": [0.3]}}

    response = client.post(f"/models/{models['iJO1366']}/modify", json=data)
    assert response.status_code == 200

    response = client.post(
        "/simulate",
        json={"model_id": models["iJO1366"], "operations": response.json["operations"]},
    )
    assert response.status_code == 200
    assert response.json["status"] == "optimal"
    assert response.json["growth_rate"] == pytest.approx(0.285)
