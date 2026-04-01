"""
Created: 2025-03-05 00:00
Agent type: Composer
Modified: 2026-03-19 15:30
Agent type: Composer
Modified: 2026-03-19 17:05
Agent type: Composer

Experiment main toolbar: finds the first form/table entry for `Sample`, averages its `Volume`,
and sets `C_AverageVolume` on the experiment record.
"""

from __future__ import annotations

from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from sapiopylib.rest.utils.recordmodel.PyRecordModel import PyRecordModel


class ExperimentToolbarWebhookExample(CommonsWebhookHandler):
    SOURCE_DATA_TYPE: str = "Sample"

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if self.can_send_client_callback():
            try:
                if not self.callback.yes_no_dialog(
                    "Experiment toolbar",
                    "Average Volume from selected rows and set C_AverageVolume on the experiment?",
                    False,
                ):
                    return SapioWebhookResult(True)
            except SapioUserCancelledException:
                return SapioWebhookResult(True)
        return self._run_demo(context)

    def _run_demo(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if self.exp_handler is None:
            return SapioWebhookResult(
                True,
                display_text="Experiment toolbar demo needs ExperimentHandler (ELN experiment webhook).",
            )
        source_step = None
        selected_step_name: str | None = None
        for step in self.exp_handler.get_all_steps():
            entry = getattr(step, "eln_entry", None)
            if entry is None:
                continue
            dt_name = (getattr(entry, "data_type_name", None) or "").strip()
            entry_type = getattr(entry, "entry_type", None)
            entry_type_name = str(entry_type).lower()
            is_table_or_form = "table" in entry_type_name or "form" in entry_type_name
            if dt_name == self.SOURCE_DATA_TYPE and is_table_or_form:
                if source_step is None:
                    source_step = step
                    selected_step_name = getattr(step, "get_name", lambda: None)()
        if source_step is None:
            return SapioWebhookResult(
                True,
                display_text=f"No form/table entry found for data type {self.SOURCE_DATA_TYPE!r}.",
            )
        source_recs = self.exp_handler.get_step_records(source_step)
        exp_details: list[PyRecordModel] = self.inst_man.add_existing_records(source_recs or [])
        volumes: list[float] = []
        for x in exp_details:
            v: object | None = x.get_field_value("Volume")
            if v is not None:
                try:
                    volumes.append(float(v))
                except (TypeError, ValueError):
                    pass
        experiment_record_direct = None
        try:
            experiment_record_direct = self.exp_handler.get_experiment_record()
        except Exception:
            experiment_record_direct = None
        if not volumes:
            return SapioWebhookResult(
                True,
                display_text=f"No numeric Volume in first {self.SOURCE_DATA_TYPE!r} form/table entry.",
            )
        if experiment_record_direct is None:
            return SapioWebhookResult(True, display_text="Could not resolve experiment record from ExperimentHandler.")

        avg_volume: float = sum(volumes) / len(volumes)
        experiment_record: PyRecordModel = self.inst_man.add_existing_record(experiment_record_direct)
        experiment_record.set_field_value("C_AverageVolume", avg_volume)
        self.rec_man.store_and_commit()
        return SapioWebhookResult(
            True,
            display_text=(
                f"Set C_AverageVolume={avg_volume} from {len(volumes)} row(s) in "
                f"{self.SOURCE_DATA_TYPE!r} entry {selected_step_name!r}."
            ),
        )
