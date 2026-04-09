#! /usr/bin/env python
import os
import sys

from sapiopycommons.general.time_util import TimeUtil
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.WebhookService import WebhookConfiguration, WebhookServerFactory
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from waitress import serve

from exercises.training_event.B_webhooks_fundamentals_examples import TrainingEventExerciseSolution, \
    TrainingEventExerciseBroken, TrainingEventContextCounter
from exercises.training_event.C_export_predefined_search import ExportPredefinedSearch
from exercises.training_event.D_record_models_comparison import DataRecordTimingExample, RecordModelTimingExample
from approve_shipment import ApproveShipment
from multilayer_plating_plate_dimensions import MultiLayerPlatingPlateDimensions
from receive_shipment import ReceiveShipment
from bulk_samples_from_study import BulkSamplesFromStudy


def _env_flag_true(name: str) -> bool:
    """True if the environment variable is set to a common affirmative value (case-insensitive)."""
    raw = os.environ.get(name)
    if raw is None:
        return False
    return raw.strip().lower() in ("true", "1", "yes")


def _listen_port() -> int:
    """Port for the local webhook server (SapioWebhooksPort, then PORT, default 8091)."""
    for key in ("SapioWebhooksPort", "PORT"):
        raw = os.environ.get(key)
        if raw is not None and raw.strip():
            return int(raw.strip())
    return 8092


# TimeUtil is a utility provided by sapiopycommons for handling timezone conversions.
# This call sets up a default timezone that all calls to TimeUtil will use unless otherwise
# specified by the input parameters. This would typically be the timezone that matches the
# customer's location.
TimeUtil.set_default_timezone("UTC")

# This training project often targets Sapio over HTTPS with self-signed certs, so verification is off by default.
# For production or any host with a publicly trusted CA, set SapioWebhooksVerifySsl=true (see Dockerfile).
# debug should be false by default, as having a deployed server in debug mode can be unsafe.
# client_timeout_seconds is the default amount of time that the webhook server will wait for a response from the
# Sapio server when making requests. This can be changed here to affect all registered endpoints, or changed on a
# per-endpoint basis by changing the webhook handler's client_timeout_seconds class variable.
config: WebhookConfiguration = WebhookConfiguration(verify_sapio_cert=False, debug=False, client_timeout_seconds=600)

if _env_flag_true("SapioWebhooksVerifySsl"):
    config.verify_sapio_cert = True
# Explicit opt-out (same effect as default here); useful if you temporarily set VerifySsl in the environment.
elif _env_flag_true("SapioWebhooksInsecure") or _env_flag_true("SapioWebhooksAllowSelfSigned"):
    config.verify_sapio_cert = False


class Ping(CommonsWebhookHandler):
    """
    A simple webhook that returns the time as a toaster popup when invoked from the system.
    Intended to be placed on the main toolbar to verify that the webhook server is running and
    is able to be access by the system.
    """
    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        now: str = TimeUtil.now_in_format("%H:%M:%S")
        return SapioWebhookResult(True, f"The webhook server is active.\nServer time: {now}.")


# Ping to see if the webhook server is running.
config.register('/ping', Ping)

# Register new endpoints here:
config.register('/export-search', ExportPredefinedSearch)

config.register('/context-counter', TrainingEventContextCounter)
config.register('/working-example', TrainingEventExerciseSolution)
config.register('/broken-example', TrainingEventExerciseBroken)

config.register('/data-record-timing-example', DataRecordTimingExample)
config.register('/record-model-timing-example', RecordModelTimingExample)

# Shipment approval (e-sign): register the same path on two Sapio webhooks — Form Toolbar + Table Toolbar, Shipment only.
config.register('/approve-shipment', ApproveShipment)

# Receive shipment (table dialog + batch commit): Form Toolbar + Table Toolbar, Shipment only.
config.register('/receive-shipment', ReceiveShipment)

# 3D plating: experiment entry toolbar — set plate rows/columns from step option plate ID list.
config.register('/change-plate-dimensions', MultiLayerPlatingPlateDimensions)

# Bulk samples under a study (main toolbar): study → count → accessioned IDs → layout table → process or Logged.
config.register('/bulk-samples-from-study', BulkSamplesFromStudy)

app = WebhookServerFactory.configure_flask_app(app=None, config=config)


# Health check route. This is required for deployments to services which use
# a specific GET endpoint to check the health of the webhook server.
@app.route("/ping")
def health_check():
    return "Alive!"


# Run this to run a local server. The app you are using will need a way to access this
# port on your local host in order to interact with the webhook server. This can be achieved
# by using a service such as ngrok, or using your device's IP on an internal network as the webhook URL.
# A Docker image built using the provided Dockerfile will instead use Gunicorn as the entry point,
# meaning that changes to the below code will not affect a deployed webhook server.
if __name__ == '__main__':
    host = "0.0.0.0"
    port = _listen_port()
    # Set SapioWebhooksDebug to true, 1, or yes on your local machine to use Flask's dev server with debug enabled.
    try:
        print(f"Starting webhook server on http://{host}:{port}/")
        if _env_flag_true("SapioWebhooksDebug"):
            app.run(host=host, port=port, debug=True)
        else:
            serve(app, host=host, port=port)
    except OSError as e:
        # Typical: errno.EADDRINUSE / WinError 10048. On some Windows setups a conflicting bind raises WinError 10013.
        print(
            f"Could not listen on {host}:{port}: {e}\n"
            f"Another process may be using the port, or the OS may block it. "
            f"Stop the other listener, or set SapioWebhooksPort (or PORT) to a free port.",
            file=sys.stderr,
        )
        sys.exit(1)
