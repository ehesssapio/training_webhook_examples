"""
Created: 2026-03-19 15:05
Agent type: Composer
Modified: 2026-03-19 17:05
Agent type: Composer
Modified: 2026-03-26 09:30
Agent type: gpt-5.3-codex-low

ELN entry validation: for `Sample` entry submissions, attach parent `Request` records
to the `Associated Requests for Samples` experiment entry.
"""

from __future__ import annotations

from sapiopycommons.eln.experiment_step_factory import ExperimentStepFactory
from sapiopycommons.general.exceptions import SapioException
from sapiopycommons.rules.eln_rule_handler import ElnRuleHandler
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.utils.recordmodel.PyRecordModel import PyRecordModel
from sapiopylib.rest.utils.recordmodel.properties import Parents
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult


class ExpEntryValidationWebhookExample(CommonsWebhookHandler):
    SAMPLE: str = "Sample"
    REQUEST: str = "Request"
    REQUEST_ENTRY_NAME: str = "Associated Requests for Samples"

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        return self._run_sample_request_gate(context)

    def _run_sample_request_gate(self, context: SapioWebhookContext) -> SapioWebhookResult:
        try:
            rule_handler: ElnRuleHandler = ElnRuleHandler(context)
        except SapioException:
            return SapioWebhookResult(
                True,
                display_text="ELN validation webhook: no velox_eln_rule_result_map (not an ELN rule call).",
            )
        exp_entry = context.experiment_entry
        dt: str | None = exp_entry.data_type_name if exp_entry is not None else None
        if dt != self.SAMPLE:
            return SapioWebhookResult(
                True,
                display_text=f"ELN validation: entry data type {dt!r} is not {self.SAMPLE!r}.",
            )

        sample_models: list[PyRecordModel] = list(rule_handler.get_models(self.SAMPLE))
        # Some ELN entry validation invocations do not populate the rule result map.
        # First fall back to current step models from ExperimentHandler.
        if not sample_models and self.exp_handler is not None and exp_entry is not None:
            try:
                sample_models = list(self.exp_handler.get_step_models(exp_entry.entry_name) or [])
            except Exception:
                sample_models = []
        # Then fall back to loading records from ELN manager for the current entry.
        if not sample_models and self.eln_man is not None and exp_entry is not None and context.eln_experiment is not None:
            try:
                sample_models = list(
                    self.eln_man.get_data_records_for_entry(
                        context.eln_experiment.notebook_experiment_id,
                        exp_entry.entry_id,
                    )
                    or []
                )
            except Exception:
                sample_models = []
        if not sample_models:
            return SapioWebhookResult(
                True,
                display_text="ELN validation: no Sample records available in rule context or entry records.",
            )

        if self.rel_man is None:
            return SapioWebhookResult(
                True,
                display_text="ELN validation: relationship manager unavailable.",
            )
        try:
            self.rel_man.load_parents(sample_models, self.REQUEST)
        except SapioException as exc:
            return SapioWebhookResult(
                True,
                display_text=f"ELN validation: failed loading parent Request relationships ({exc}).",
            )

        request_by_id: dict[int, PyRecordModel] = {}
        for sample in sample_models:
            parents: list[PyRecordModel] = sample.get(Parents.of_type_name(self.REQUEST)) or []
            for parent in parents:
                request_by_id[parent.record_id] = parent
        request_models: list[PyRecordModel] = list(request_by_id.values())
        if not request_models:
            return SapioWebhookResult(
                True,
                display_text=f"Found {len(sample_models)} Sample record(s) but no parent Request records.",
            )

        if self.exp_handler is None:
            return SapioWebhookResult(
                True,
                display_text="ELN validation: experiment handler unavailable for entry updates.",
            )

        request_step = self.exp_handler.get_step(self.REQUEST_ENTRY_NAME, exception_on_none=False)
        reused_entry: bool = request_step is not None
        if request_step is None:
            step_factory: ExperimentStepFactory = ExperimentStepFactory(self.exp_handler)
            request_step = step_factory.create_table_step(self.REQUEST_ENTRY_NAME, self.REQUEST)

        try:
            self.exp_handler.set_step_records(request_step, request_models)
        except SapioException as exc:
            return SapioWebhookResult(
                True,
                display_text=f"ELN validation: failed writing Request entry records ({exc}).",
            )
        return SapioWebhookResult(
            True,
            display_text=(
                f"Found {len(sample_models)} Sample record(s); attached {len(request_models)} unique parent Request "
                f"record(s) to entry {self.REQUEST_ENTRY_NAME!r} ({'reused' if reused_entry else 'created'})."
            ),
        )
