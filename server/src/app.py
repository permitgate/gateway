# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

from fastapi import FastAPI
from fastapi_healthchecks.api.router import HealthcheckRouter, Probe

from api.approval_flows import router as approval_flows_router

app = FastAPI(
    title="PermitGate Gateway API",
    description="API for managing approval flows and workflow automation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)
app.include_router(
    HealthcheckRouter(
        Probe(
            name="readiness",
            checks=[
                # TODO:
            ],
        ),
        Probe(
            name="liveness",
            checks=[
                # TODO:
            ],
        ),
    ),
    prefix="/health",
)
app.include_router(approval_flows_router)
