"""
Created: 2025-03-05 00:00
Agent type: Composer
Modified: 2026-03-19 15:30
Agent type: Composer
Modified: 2026-03-19 17:05
Agent type: Composer

ELN rule webhook: `ElnRuleHandler`, `ExperimentHandler`, `store_and_commit`, and `update_experiment` to Completed.
"""

from __future__ import annotations

from sapiopycommons.general.time_util import TimeUtil
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.eln.SapioELNEnums import ElnExperimentStatus
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from sapiopylib.rest.utils.recordmodel.PyRecordModel import PyRecordModel


class ExperimentWebhookExample(CommonsWebhookHandler):
    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        return self._run_mutations()

    def _run_mutations(self) -> SapioWebhookResult:
        if self.rule_handler is None or self.exp_handler is None:
            return SapioWebhookResult(
                True,
                display_text="Requires ELN rule context (rule_handler) and ExperimentHandler.",
            )
        sample_models: list[PyRecordModel] = self.rule_handler.get_models("Sample")
        for sample_model in sample_models:
            sample_model.set_field_value("C_Completed", True)
        datum_models: list[PyRecordModel] = self.exp_handler.get_step_models("Instrument Results")
        for datum_model in datum_models:
            datum_model.set_field_value("C_DateCompleted", TimeUtil.now_in_millis())
        self.rec_man.store_and_commit()
        self.exp_handler.update_experiment(experiment_status=ElnExperimentStatus.Completed)
        return SapioWebhookResult(True)
