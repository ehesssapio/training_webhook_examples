"""
Created: 2026-03-19 15:20
Agent type: Composer
Modified: 2026-03-19 22:30
Agent type: Composer
Modified: 2026-03-20 12:00
Agent type: Composer

Python counterpart to Java PlateAliquotExample.java
(`sapio://examples/java/features/plate-aliquot`).

Inspects a plate-designer step via PlateDesignerEntry when run from an ELN experiment webhook (exp_handler).
"""

from __future__ import annotations

import traceback

from sapiopycommons.callbacks.callback_util import BlankResultHandling
from sapiopycommons.eln.plate_designer import PlateDesignerEntry
from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.datatype.FieldDefinition import VeloxStringFieldDefinition
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult


class PlateAliquotFeatureExample(CommonsWebhookHandler):
    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.can_send_client_callback():
            return SapioWebhookResult(False, display_text="Requires client callback.")
        try:
            self._run_view_plate_layout()
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        except Exception as ex:
            self.callback.display_error(f"{ex!s}\n{traceback.format_exc()}")
            return SapioWebhookResult(False)
        return SapioWebhookResult(True)

    def _run_view_plate_layout(self) -> None:
        if self.exp_handler is None:
            self.callback.display_warning(
                "Run this webhook from an ELN experiment context so exp_handler is available."
            )
            return
        step_raw: object = self.callback.input_dialog(
            "Plate designer",
            "Plate designer step name in this experiment:",
            VeloxStringFieldDefinition("TempPlate", "StepName", "Step name", max_length=200, editable=True),
            blank_result_handling=BlankResultHandling.REPEAT,
        )
        step_name: str = str(step_raw).strip() if step_raw is not None else ""
        step = self.exp_handler.get_step(step_name)
        pd: PlateDesignerEntry = PlateDesignerEntry(step, self.exp_handler)
        plates = pd.get_plates()
        lines: list[str] = [
            f"PlateDesignerEntry {step_name!r}\n\n",
            f"Plate record count: {len(plates)}\n\n",
        ]
        self.callback.display_info("".join(lines))
