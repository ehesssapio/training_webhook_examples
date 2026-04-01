"""
Created: 2025-03-05 00:00
Agent type: Composer
Modified: 2026-03-19 15:30
Agent type: Composer
Modified: 2026-03-19 17:05
Agent type: Composer

Main toolbar: create one Sample with optional Description, or create N Samples and return a table directive.
"""

from __future__ import annotations

from sapiopycommons.callbacks.callback_util import BlankResultHandling
from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.datatype.FieldDefinition import VeloxIntegerFieldDefinition
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookDirective import TableDirective
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from sapiopylib.rest.utils.recordmodel.PyRecordModel import PyRecordModel


class MainToolbarWebhookExample(CommonsWebhookHandler):
    OPT_CREATE_ONE: str = "Create one Sample and commit"
    OPT_EXTENDED: str = "Extended: create N Samples + table directive"

    MENU_OPTIONS: tuple[str, ...] = (OPT_CREATE_ONE, OPT_EXTENDED)

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.can_send_client_callback():
            return SapioWebhookResult(
                False,
                display_text="Main toolbar example requires client callback.",
            )
        try:
            choice: str = self.callback.option_dialog(
                "Main Toolbar Examples",
                "Select demonstration:",
                list(self.MENU_OPTIONS),
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return SapioWebhookResult(True)

        if choice == self.OPT_CREATE_ONE:
            return self._run_create_one_sample()
        if choice == self.OPT_EXTENDED:
            return self._run_extended()
        return SapioWebhookResult(False, display_text="Unknown option.")

    def _run_create_one_sample(self) -> SapioWebhookResult:
        if self.dt_man.get_data_type_definition("Sample") is None:
            self.callback.display_warning(
                "The 'Sample' data type is not defined in this system. Cannot create a record."
            )
            return SapioWebhookResult(True)
        sample: PyRecordModel = self.inst_man.add_new_record("Sample")
        try:
            sample.set_field_value("Description", "Created by Main Toolbar Example")
        except Exception:
            pass
        self.rec_man.store_and_commit()
        self.callback.display_info(
            f"Created a new Sample record (RecordId: {sample.record_id}) and committed.\n\n"
            "Main toolbar webhooks can perform persisted actions from anywhere in the application."
        )
        return SapioWebhookResult(True)

    def _run_extended(self) -> SapioWebhookResult:
        try:
            num_raw: object = self.callback.input_dialog(
                "Create Samples",
                "Enter the number of samples to register",
                VeloxIntegerFieldDefinition("NumSamples", "NumSamples", "Number of Samples"),
                require_input=True,
                blank_result_handling=BlankResultHandling.REPEAT,
                repeat_message="Please provide a non-blank numerical value to continue.",
                cancel_message="User cancelled dialog.",
            )
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        num_samples: int = int(num_raw) if not isinstance(num_raw, int) else num_raw
        sample_models: list[PyRecordModel] = self.inst_man.add_new_records("Sample", num_samples)
        self.rec_man.store_and_commit()
        return SapioWebhookResult(
            True,
            directive=TableDirective([x.get_data_record() for x in sample_models]),
        )
