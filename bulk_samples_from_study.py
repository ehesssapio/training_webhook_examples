"""
Bulk samples from study — Main Toolbar webhook.

Sapio setup (App Setup → Manage Rules & Webhooks → Webhooks):
  Invocation: Main Toolbar — URL: ``{webhook-server-base}/bulk-samples-from-study``
  (must match ``config.register`` in ``server.py``).

Tenant / training checklist:
  * **Study → Sample** relationship: Sample records are attached as **children of the selected Study**
    (``study_model.add_children(sample_models)``). If your model links Study and Sample differently,
    change ``_link_samples_to_study`` below.
  * Accession configuration for **Sample.SampleId** (Exemplar / accession service) so
    ``AccessionService.accession_with_config`` succeeds.
  * **Sample.ExemplarSampleStatus** includes picklist value **Logged** when the user declines process assignment.
  * **Process assignment** uses ``ProcessTracking.assign_to_process`` (AssignedProcess-style experiment
    processes, not ProcessQueueItem queues). Process choices are loaded from **Process** records
    (``ProcessName``, skipping rows with ``IsActive`` false). Optional env **BULK_SAMPLES_PROCESS_NAMES**
    (comma-separated) is merged in if no suitable Process records exist, for constrained environments.
"""
from __future__ import annotations

import os
from typing import Any

from sapiopycommons.callbacks.callback_util import CallbackUtil, FieldModifier
from sapiopycommons.general.accession_service import AccessionService
from sapiopycommons.general.exceptions import SapioUserErrorException
from sapiopycommons.processtracking.endpoints import ProcessTracking
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.User import SapioUser
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from sapiopylib.rest.utils.autopaging import QueryAllRecordsOfTypeAutoPager
from sapiopylib.rest.utils.recordmodel.RecordModelManager import RecordModelInstanceManager

from utilities.data_type_models import ProcessModel, SampleModel, StudyModel

STUDY_DATA_TYPE_NAME: str = "Study"
SAMPLE_DATA_TYPE_NAME: str = "Sample"
SAMPLE_ID_FIELD: str = "SampleId"
SAMPLE_STATUS_LOGGED: str = "Logged"

# Upper bound for integer dialog and accession batch size.
MAX_SAMPLES_PER_RUN: int = 500

# Fields never copied from the table dialog back onto the model (accession / system).
SKIP_APPLY_FIELDS: frozenset[str] = frozenset({SAMPLE_ID_FIELD, "RecordId"})


def _process_name_options_from_env() -> list[str]:
    raw = os.environ.get("BULK_SAMPLES_PROCESS_NAMES", "").strip()
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def _assignable_process_names(user: SapioUser, inst_man: RecordModelInstanceManager) -> list[str]:
    """
    Names accepted by assign-to-process: active Process records' ProcessName, else env override list.
    """
    names: set[str] = set()
    process_records = QueryAllRecordsOfTypeAutoPager(ProcessModel.DATA_TYPE_NAME, user).get_all_at_once()
    if process_records:
        process_models: list[ProcessModel] = inst_man.add_existing_records_of_type(
            process_records, ProcessModel
        )
        for proc in process_models:
            if proc.get_IsActive_field() is False:
                continue
            pn = proc.get_ProcessName_field()
            if pn and str(pn).strip():
                names.add(str(pn).strip())
    if names:
        return sorted(names)
    return _process_name_options_from_env()


def _link_samples_to_study(study: StudyModel, samples: list[SampleModel]) -> None:
    """Attach new samples to the study (default: parent Study, child Sample)."""
    study.add_children(samples)


def _apply_field_maps_to_samples(
    samples: list[SampleModel],
    field_maps: list[dict[str, Any]],
) -> None:
    if len(field_maps) != len(samples):
        raise SapioUserErrorException(
            f"Table dialog returned {len(field_maps)} row(s) for {len(samples)} sample(s); cannot apply edits."
        )
    for model, fm in zip(samples, field_maps):
        for fn, value in fm.items():
            if fn in SKIP_APPLY_FIELDS:
                continue
            model.set_field_value(fn, value)


class BulkSamplesFromStudy(CommonsWebhookHandler):
    """Main toolbar: pick Study → sample count → accession IDs → layout table → commit → process or Logged."""

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.is_main_toolbar():
            raise SapioUserErrorException(
                "Bulk Samples from Study must be invoked from the main toolbar."
            )
        if not self.can_send_client_callback():
            raise SapioUserErrorException(
                "Bulk Samples from Study requires a client callback for dialogs."
            )

        callback = CallbackUtil(context)

        study_records = QueryAllRecordsOfTypeAutoPager(STUDY_DATA_TYPE_NAME, context.user).get_all_at_once()
        if not study_records:
            raise SapioUserErrorException("No Study records were found to select from.")

        study_models: list[StudyModel] = self.inst_man.add_existing_records_of_type(
            study_records, StudyModel
        )
        selected: list[StudyModel] = callback.record_selection_dialog(
            "<p>Select the study to create samples under.</p>",
            records=study_models,
            multi_select=False,
            fields=None,
        )
        if not selected:
            return SapioWebhookResult(True, "No study was selected.")
        study: StudyModel = selected[0]

        count = callback.integer_input_dialog(
            title="Number of samples",
            msg="<p>How many samples should be created?</p>",
            field_name="Sample count",
            default_value=1,
            min_value=1,
            max_value=MAX_SAMPLES_PER_RUN,
            require_input=True,
        )
        if count < 1 or count > MAX_SAMPLES_PER_RUN:
            raise SapioUserErrorException(
                f"Sample count must be between 1 and {MAX_SAMPLES_PER_RUN}."
            )

        sample_ids = AccessionService(context.user).accession_with_config(
            SAMPLE_DATA_TYPE_NAME, SAMPLE_ID_FIELD, count
        )
        if len(sample_ids) != count:
            raise SapioUserErrorException(
                f"Accession service returned {len(sample_ids)} id(s) for count {count}."
            )

        sample_models: list[SampleModel] = self.inst_man.add_new_records_of_type(count, SampleModel)
        for sample, sid in zip(sample_models, sample_ids):
            sample.set_SampleId_field(sid)

        _link_samples_to_study(study, sample_models)

        field_maps = callback.record_table_dialog(
            "New samples",
            "<p>Review accessioned Sample IDs and edit fields, then confirm to create records.</p>",
            fields=None,
            records=sample_models,
            default_modifier=FieldModifier(visible=True, key_field=False, editable=True),
            field_modifiers={SAMPLE_ID_FIELD: FieldModifier(editable=False)},
        )
        _apply_field_maps_to_samples(sample_models, field_maps)

        assign_process = callback.yes_no_dialog(
            "Assign to process",
            "<p>Assign the new samples to an experiment process?</p>",
            default_yes=False,
        )

        process_name: str | None = None
        if assign_process:
            options = _assignable_process_names(context.user, self.inst_man)
            if not options:
                raise SapioUserErrorException(
                    "Process assignment was requested but no process names were found. "
                    "Ensure active Process records exist with ProcessName set, or set "
                    "BULK_SAMPLES_PROCESS_NAMES to a comma-separated list."
                )
            chosen = callback.list_dialog(
                "Select process",
                options,
                multi_select=False,
            )
            if not chosen:
                raise SapioUserErrorException("No process was selected.")
            process_name = chosen[0]
        else:
            for s in sample_models:
                s.set_ExemplarSampleStatus_field(SAMPLE_STATUS_LOGGED)

        self.rec_man.store_and_commit()

        if assign_process and process_name:
            ProcessTracking.assign_to_process(
                context,
                SampleModel,
                sample_models,
                process_name,
            )

        return SapioWebhookResult(
            True,
            f"Created {count} sample(s) under the selected study.",
        )
