"""
Created: 2026-03-19 15:20
Agent type: Composer
Modified: 2026-03-19 22:30
Agent type: Composer

Python counterpart to Java ExperimentEntryExample.java
(`sapio://examples/java/features/experiment-entry-manager`).

Lists experiment steps and entry metadata from ExperimentHandler (read-only).
"""

from __future__ import annotations

import traceback

from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult


class ExperimentEntryManagerFeatureExample(CommonsWebhookHandler):
    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.can_send_client_callback():
            return SapioWebhookResult(False, display_text="Requires client callback.")
        if self.exp_handler is None:
            return SapioWebhookResult(
                True,
                display_text="Invoke from an ELN experiment webhook so exp_handler is populated.",
            )
        try:
            steps = self.exp_handler.get_all_steps()
            lines: list[str] = [
                "=== Experiment steps ===\n\n",
                f"Count: {len(steps)}\n\n",
            ]
            for s in steps[:40]:
                lines.append(
                    f" • {s.get_name()!r}  type={s.eln_entry.data_type_name!r}  "
                    f"order={s.eln_entry.order}  status={s.eln_entry.entry_status!r}\n"
                )
            if len(steps) > 40:
                lines.append(f"\n... and {len(steps) - 40} more\n")
            self.callback.display_info("".join(lines))
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        except Exception as ex:
            self.callback.display_error(
                f"Experiment Entry Example Error:\n{ex!s}\n\n{traceback.format_exc()}"
            )
            return SapioWebhookResult(False)
        return SapioWebhookResult(True)
