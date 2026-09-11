# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

from fastapi import FastAPI
from fastapi_healthchecks.api.router import HealthcheckRouter, Probe

app = FastAPI()
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
