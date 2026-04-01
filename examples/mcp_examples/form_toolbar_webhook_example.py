"""
Created: 2026-03-19 15:05
Agent type: Composer
Modified: 2026-03-19 17:05
Agent type: Composer

Python counterpart to Java FormToolbarPluginExample.java (`sapio://examples/java/invocations/form-toolbar`).

`WebhookEndpointType.FORMTOOLBAR` with `context.data_record`. Loads the form record as `PyRecordModel` for extension.
"""

from __future__ import annotations

from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.DataRecord import DataRecord
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from sapiopylib.rest.utils.recordmodel.PyRecordModel import PyRecordModel


class FormToolbarWebhookExample(CommonsWebhookHandler):
    SAMPLE_TYPE: str = "Sample"

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        rec: DataRecord | None = context.data_record
        if rec is None:
            return SapioWebhookResult(True, display_text="Form toolbar: no data_record on context.")
        if rec.data_type_name != self.SAMPLE_TYPE:
            return SapioWebhookResult(
                True,
                display_text=f"This example uses {self.SAMPLE_TYPE}; context has {rec.data_type_name}.",
            )
        if not self.can_send_client_callback():
            return SapioWebhookResult(
                True,
                display_text=f"Form toolbar: Sample RecordId={rec.record_id}. Interactive demo needs client callback.",
            )
        return self._run_demo(rec)

    def _run_demo(self, rec: DataRecord) -> SapioWebhookResult:
        try:
            ok: bool = self.callback.yes_no_dialog(
                "Form toolbar demo",
                f"Load Sample RecordId={rec.record_id} as PyRecordModel?",
                False,
            )
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        if not ok:
            return SapioWebhookResult(True, display_text="Cancelled.")
        model: PyRecordModel = self.inst_man.add_existing_records([rec])[0]
        note: str = f"Loaded PyRecordModel RecordId={model.record_id}."
        self.callback.display_info(note)
        return SapioWebhookResult(True, display_text=note)
