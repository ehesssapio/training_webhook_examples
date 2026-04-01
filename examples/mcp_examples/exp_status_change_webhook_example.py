"""
Created: 2026-03-19 15:05
Agent type: Composer
Modified: 2026-03-19 17:05
Agent type: Composer

When `context.eln_experiment` status is Completed, sets `C_Completed` on the Samples step.
"""

from __future__ import annotations

from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.eln.SapioELNEnums import ElnExperimentStatus
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from sapiopylib.rest.utils.recordmodel.PyRecordModel import PyRecordModel


class ExpStatusChangeWebhookExample(CommonsWebhookHandler):
    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if self.can_send_client_callback():
            try:
                if not self.callback.yes_no_dialog(
                    "Experiment status change",
                    "When experiment status is Completed, set C_Completed on Samples step?",
                    False,
                ):
                    return SapioWebhookResult(True)
            except SapioUserCancelledException:
                return SapioWebhookResult(True)
        return self._run_mutate(context)

    def _run_mutate(self, context: SapioWebhookContext) -> SapioWebhookResult:
        exp = context.eln_experiment
        if exp is None or exp.notebook_experiment_status != ElnExperimentStatus.Completed:
            return SapioWebhookResult(
                True,
                display_text="Experiment not present or status is not Completed; no update.",
            )
        if self.exp_handler is None:
            return SapioWebhookResult(
                True,
                display_text="No ExperimentHandler (invoke from ELN-related webhook).",
            )
        samples: list[PyRecordModel] = list(self.exp_handler.get_step_models("Samples"))
        for sample in samples:
            sample.set_field_value("C_Completed", True)
        self.rec_man.store_and_commit()
        return SapioWebhookResult(True, display_text="Set C_Completed=True on Samples step.")
