"""Explicit test-only configuration for the project suite."""

import os

os.environ["FIVEBR_INSECURE_TEST_BYPASS"] = "1"

from web.app import app as project_app

project_app.testing = True
project_app.config["INSECURE_TEST_BYPASS"] = True
