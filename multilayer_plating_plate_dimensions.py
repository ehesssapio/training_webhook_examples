"""
3D plating — experiment entry toolbar: set Plate rows/columns from a short form.

Sapio setup (App Setup → Manage Rules & Webhooks → Webhooks):
  * Invocation: **Experiment Entry Toolbar**
  * Webhook URL: ``{webhook-server-base}/change-plate-dimensions``
  * Restrict the webhook to the **3D plating** workflow template / target entry so the
    button only appears where intended.

The current ELN entry step option ``MultiLayerPlating_Plate_RecordIdList`` must contain
exactly one plate record ID (no comma-separated list). The handler updates that Plate's
``PlateRows`` and ``PlateColumns`` after the user submits rows/columns (1–2 characters each).
"""
from __future__ import annotations

from typing import Any

from sapiopycommons.general.exceptions import SapioUserErrorException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.ClientCallbackService import ClientCallback
from sapiopylib.rest.DataMgmtService import DataMgmtServer
from sapiopylib.rest.pojo.datatype.FieldDefinition import VeloxStringFieldDefinition
from sapiopylib.rest.pojo.webhook.ClientCallbackRequest import FormEntryDialogRequest
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from sapiopylib.rest.utils.FormBuilder import FormBuilder
from sapiopylib.rest.utils.Protocols import ElnEntryStep

from utilities.data_type_models import PlateModel

# Step option on the current experiment entry (workflow configuration).
STEP_OPTION_PLATE_RECORD_ID_LIST: str = "MultiLayerPlating_Plate_RecordIdList"

# Temporary form data type and field API names (must match default_values / dialog response keys).
_TEMP_DATA_TYPE_NAME: str = "MultiLayerPlatingPlateDims"
_FIELD_ROWS: str = "RowsInput"
_FIELD_COLS: str = "ColsInput"

_CANCEL_MESSAGE: str = "No changes were made."
_SUCCESS_TEMPLATE: str = "Updated plate {plate_id} to {rows} row(s) × {cols} column(s)."


def _split_csv_ids(raw: str) -> list[str]:
    parts = [p.strip() for p in raw.split(",")]
    return [p for p in parts if p]


def _parse_single_plate_record_id(raw: str | None) -> int:
    if raw is None or not str(raw).strip():
        raise SapioUserErrorException(
            f"Step option {STEP_OPTION_PLATE_RECORD_ID_LIST!r} is missing or empty."
        )
    tokens = _split_csv_ids(str(raw))
    if len(tokens) == 0:
        raise SapioUserErrorException(
            f"Step option {STEP_OPTION_PLATE_RECORD_ID_LIST!r} is missing or empty."
        )
    if len(tokens) > 1:
        raise SapioUserErrorException(
            "Multiple plate IDs are set for this step; exactly one plate ID is required."
        )
    try:
        return int(tokens[0])
    except ValueError as e:
        raise SapioUserErrorException(
            f"Step option {STEP_OPTION_PLATE_RECORD_ID_LIST!r} must be a numeric record ID."
        ) from e


def _parse_dimension(value: Any, label: str) -> int:
    if value is None:
        raise SapioUserErrorException(f"{label} is required.")
    s = str(value).strip()
    if not s:
        raise SapioUserErrorException(f"{label} is required.")
    if len(s) > 2:
        raise SapioUserErrorException(f"{label} must be at most 2 characters.")
    if not s.isdigit():
        raise SapioUserErrorException(f"{label} must be a positive number.")
    n = int(s)
    if n <= 0:
        raise SapioUserErrorException(f"{label} must be greater than zero.")
    return n


class MultiLayerPlatingPlateDimensions(CommonsWebhookHandler):
    """Prompt for plate rows/columns, then update the plate from the step option list."""

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.is_eln_entry_toolbar():
            raise SapioUserErrorException(
                "This action must be run from an experiment entry toolbar button."
            )
        if context.eln_experiment is None:
            raise SapioUserErrorException("No notebook experiment in context.")
        step = context.active_step
        if not isinstance(step, ElnEntryStep):
            raise SapioUserErrorException("No active experiment entry step in context.")

        callback: ClientCallback = DataMgmtServer.get_client_callback(context.user)
        form_builder = FormBuilder()
        form_builder.add_field(
            VeloxStringFieldDefinition(
                _TEMP_DATA_TYPE_NAME,
                _FIELD_ROWS,
                "Rows",
                max_length=2,
                editable=True,
            ),
            0,
            2,
        )
        form_builder.add_field(
            VeloxStringFieldDefinition(
                _TEMP_DATA_TYPE_NAME,
                _FIELD_COLS,
                "Columns",
                max_length=2,
                editable=True,
            ),
            2,
            2,
        )
        temp_type_def = form_builder.get_temporary_data_type()
        default_values: dict[str, Any] = {_FIELD_ROWS: "", _FIELD_COLS: ""}
        request = FormEntryDialogRequest(
            "Plate dimensions",
            "Enter row and column counts for the plate (1–2 digits each).",
            temp_type_def,
            default_values,
        )
        response: dict[str, Any] | None = callback.show_form_entry_dialog(request)
        if response is None:
            return SapioWebhookResult(True, _CANCEL_MESSAGE)

        rows = _parse_dimension(response.get(_FIELD_ROWS), "Rows")
        cols = _parse_dimension(response.get(_FIELD_COLS), "Columns")

        options = step.get_options()
        plate_id = _parse_single_plate_record_id(options.get(STEP_OPTION_PLATE_RECORD_ID_LIST))

        dr = context.data_record_manager.query_system_for_record(PlateModel.DATA_TYPE_NAME, plate_id)
        if dr is None:
            raise SapioUserErrorException(f"Plate record {plate_id} was not found.")

        plate: PlateModel = self.inst_man.add_existing_records_of_type([dr], PlateModel)[0]
        plate.set_PlateRows_field(rows)
        plate.set_PlateColumns_field(cols)
        self.rec_man.store_and_commit()

        refresh_entries = [context.experiment_entry] if context.experiment_entry is not None else None
        return SapioWebhookResult(
            True,
            display_text=_SUCCESS_TEMPLATE.format(plate_id=plate_id, rows=rows, cols=cols),
            refresh_notebook_experiment=True,
            eln_entry_refresh_list=refresh_entries,
        )
