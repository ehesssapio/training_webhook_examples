"""
Created: 2025-03-05 00:00
Agent type: Composer
Modified: 2026-03-19 15:30
Agent type: Composer
Modified: 2026-03-19 17:05
Agent type: Composer

Experiment entry toolbar: averages `Volume` from `context.data_record_list` and sets `C_AverageVolume` on the experiment.
"""

from __future__ import annotations

from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from sapiopylib.rest.utils.recordmodel.PyRecordModel import PyRecordModel


class ExperimentEntryToolbarWebhookExample(CommonsWebhookHandler):
    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if self.can_send_client_callback():
            try:
                if not self.callback.yes_no_dialog(
                    "Entry toolbar",
                    "Average Volume from selected rows and set C_AverageVolume on the experiment?",
                    False,
                ):
                    return SapioWebhookResult(True)
            except SapioUserCancelledException:
                return SapioWebhookResult(True)
        return self._run_demo(context)

    def _run_demo(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if self.exp_handler is None:
            return SapioWebhookResult(True, display_text="Entry toolbar demo needs ExperimentHandler.")
        dr_list = context.data_record_list
        if not dr_list:
            return SapioWebhookResult(True, display_text="No data_record_list on context.")
        exp_details: list[PyRecordModel] = self.inst_man.add_existing_records(dr_list)
        volumes: list[float] = []
        for x in exp_details:
            v: object | None = x.get_field_value("Volume")
            if v is not None:
                try:
                    volumes.append(float(v))
                except (TypeError, ValueError):
                    pass
        if not volumes:
            return SapioWebhookResult(True, display_text="No numeric Volume in context rows.")
        avg_volume: float = sum(volumes) / len(volumes)
        experiment_record: PyRecordModel = self.inst_man.add_existing_record(self.exp_handler.get_experiment_record())
        experiment_record.set_field_value("C_AverageVolume", avg_volume)
        self.rec_man.store_and_commit()
        return SapioWebhookResult(True, display_text=f"Set C_AverageVolume={avg_volume} from {len(volumes)} row(s).")
