"""
Created: 2025-03-05 00:00
Agent type: Composer
Modified: 2026-03-19 15:30
Agent type: Composer
Modified: 2026-03-19 17:05
Agent type: Composer

On-save rule webhook (`OnSaveRuleHandler`): Sample path syncs `Barcode` from `OtherSampleId`; Subject path uses
`LastSavedValueManager` for date-revision flags. Persists with `rec_man.store_and_commit()`.
"""

from __future__ import annotations

from sapiopycommons.general.exceptions import SapioException, SapioUserCancelledException
from sapiopycommons.rules.on_save_rule_handler import OnSaveRuleHandler
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from sapiopylib.rest.utils.recordmodel.PyRecordModel import PyRecordModel


class OnSaveWebhookExample(CommonsWebhookHandler):
    OPT_SAMPLE: str = "Sample Barcode sync from OtherSampleId"
    OPT_SUBJECT: str = "Subject date demo (LastSavedValueManager)"

    MENU_OPTIONS: tuple[str, ...] = (OPT_SAMPLE, OPT_SUBJECT)

    @staticmethod
    def _to_display(value: object | None) -> str:
        return "" if value is None else str(value)

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.can_send_client_callback():
            return self._run_sample_path(context)
        try:
            choice: str = self.callback.option_dialog(
                "On-Save Webhook Examples",
                "Choose demonstration:",
                list(self.MENU_OPTIONS),
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return SapioWebhookResult(True)

        if choice == self.OPT_SAMPLE:
            return self._run_sample_path(context)
        if choice == self.OPT_SUBJECT:
            return self._run_subject_demo()
        return SapioWebhookResult(False, display_text="Unknown option.")

    def _run_sample_path(self, context: SapioWebhookContext) -> SapioWebhookResult:
        try:
            save_handler: OnSaveRuleHandler = OnSaveRuleHandler(context)
        except SapioException:
            return SapioWebhookResult(
                True,
                display_text="No velox_on_save_result_map on context — register on VELOXONSAVERULEACTION.",
            )
        samples: list[PyRecordModel] = save_handler.get_models("Sample")
        if not samples:
            return SapioWebhookResult(
                True,
                display_text="On-save context has no Sample records.",
            )
        for sample in samples:
            sample.set_field_value("Barcode", self._to_display(sample.get_field_value("OtherSampleId")))
        self.rec_man.store_and_commit()
        return SapioWebhookResult(
            True,
            display_text=f"Updated Barcode from OtherSampleId on {len(samples)} Sample(s).",
        )

    def _run_subject_demo(self) -> SapioWebhookResult:
        if self.rule_handler is None:
            return SapioWebhookResult(
                True,
                display_text="No rule handler on context; mount on an on-save rule with Subject data.",
            )
        subjects: list[PyRecordModel] = self.rule_handler.get_models("Subject")
        self.saved_vals_man.load(subjects)
        for subject in subjects:
            prev = self.saved_vals_man.get_last_saved_value(subject, "C_DateTreated")
            cur = subject.get_field_value("C_DateTreated")
            if prev is not None and cur is not None and prev < cur:
                subject.set_field_value("C_TreatmentDateRevised", True)
        self.rec_man.store_and_commit()
        return SapioWebhookResult(True, display_text="Subject LastSavedValue demo completed.")
