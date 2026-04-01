"""
Created: 2026-03-19 15:05
Agent type: Composer
Modified: 2026-03-19 17:05
Agent type: Composer

ELN entry-init webhook: emits a client callback and log for any initialized entry.
"""

from __future__ import annotations

from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.Message import VeloxLogLevel, VeloxLogMessage
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult


class ExperimentEntryInitWebhookExample(CommonsWebhookHandler):
    INIT_MESSAGE: str = "Entry initialized"

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        return self._run_gate()

    def _run_gate(self) -> SapioWebhookResult:
        entry = self.context.experiment_entry
        entry_type_name: str = str(getattr(entry, "entry_type", "Unknown"))
        msg: str = f"Entry init: {self.INIT_MESSAGE} ({entry_type_name})."
        self.messenger.log_message(
            VeloxLogMessage(msg, log_level=VeloxLogLevel.INFO, originating_class=self.__class__.__name__)
        )
        if self.can_send_client_callback():
            self.callback.display_info(self.INIT_MESSAGE)
        return SapioWebhookResult(True, display_text=msg)
