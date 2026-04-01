"""
Created: 2026-03-19 15:20
Agent type: Composer
Modified: 2026-03-20 14:30
Agent type: Composer
Modified: 2026-03-20 16:45
Agent type: Composer

Python counterpart to Java AliquotHelperExample.java
(`sapio://examples/java/features/aliquot-helper`).

Numeric next-ID and multiple-ID demos use create_aliquot_for_samples so the server assigns child SampleId per site rules.
"""

from __future__ import annotations

import traceback

from sapiopycommons.callbacks.callback_util import BlankResultHandling
from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.samples.aliquot import create_aliquot_for_samples
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.DataRecordManagerService import DataRecord
from sapiopylib.rest.pojo.DataRecordPaging import DataRecordPojoPageCriteria
from sapiopylib.rest.pojo.datatype.FieldDefinition import VeloxStringFieldDefinition
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from sapiopylib.rest.utils.recordmodel.PyRecordModel import PyRecordModel


class AliquotHelperFeatureExample(CommonsWebhookHandler):
    OPT_NEXT_ID: str = "Generate Next Sample ID (Numeric)"
    OPT_MULTIPLE: str = "Generate Multiple IDs at Once"

    MENU_OPTIONS: tuple[str, ...] = (
        OPT_NEXT_ID,
        OPT_MULTIPLE,
    )

    def _load_samples(self, limit: int = 50) -> list:
        page = self.dr_man.query_all_records_of_type(
            "Sample", DataRecordPojoPageCriteria(page_size=limit)
        )
        return page.result_list or []

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.can_send_client_callback():
            return SapioWebhookResult(False, display_text="Requires client callback.")
        try:
            choice: str = self.callback.option_dialog(
                "AliquotHelper Demo",
                "Select a demonstration:",
                list(self.MENU_OPTIONS),
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        try:
            if choice == self.OPT_NEXT_ID:
                self._run_next_id_demo()
            elif choice == self.OPT_MULTIPLE:
                self._run_multiple_ids_demo()
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        except Exception as ex:
            self.callback.display_error(f"Error:\n{ex!s}\n\n{traceback.format_exc()}")
            return SapioWebhookResult(False)
        return SapioWebhookResult(True)

    def _run_next_id_demo(self) -> None:
        raw: object = self.callback.input_dialog(
            "Base Sample ID",
            "Enter the parent Sample's SampleId (e.g., SAMPLE-001). One new aliquot child will be created.",
            VeloxStringFieldDefinition("AliqDemo", "BaseId", "Base ID", max_length=200, editable=True),
            blank_result_handling=BlankResultHandling.CANCEL,
        )
        base: str = str(raw).strip() if raw is not None else ""
        if not base:
            return
        page = self.dr_man.query_data_records("Sample", "SampleId", [base])
        matches: list[DataRecord] = page.result_list or []
        if not matches:
            self.callback.display_warning(
                f"No Sample found with SampleId {base!r}. Create the parent first or check the ID."
            )
            return
        if len(matches) > 1:
            if not self.callback.yes_no_dialog(
                "Multiple Samples",
                f"Found {len(matches)} Samples with SampleId {base!r}. Use the first match as parent?",
                False,
            ):
                return
        parent: PyRecordModel = self.inst_man.add_existing_records(matches[:1])[0]
        if not self.callback.yes_no_dialog(
            "Create aliquot",
            f"Create 1 aliquot Sample under parent {base!r}? (demo write)",
            False,
        ):
            return
        result = create_aliquot_for_samples({parent: 1}, self.user)
        new_ids: list[int] = list(result.get(parent))
        id_lines: list[str] = []
        if new_ids:
            by_id_page = self.dr_man.query_data_records_by_id("Sample", new_ids)
            aliquots: list[DataRecord] = by_id_page.result_list or []
            for rec in aliquots:
                sid: object = rec.get_fields().get("SampleId")
                id_lines.append(f"  record_id={rec.record_id}, SampleId={sid!r}")
        self.callback.display_info(
            f"Parent SampleId: {base!r}\n"
            f"New aliquot record id(s): {new_ids}\n"
            + ("New aliquot row(s):\n" + "\n".join(id_lines) if id_lines else "")
        )

    def _run_multiple_ids_demo(self) -> None:
        samples = self._load_samples(30)
        if not samples:
            self.callback.display_warning("No Sample records found (first page).")
            return
        if not self.callback.yes_no_dialog(
            "Create aliquots",
            "Create 1 aliquot Sample for the first Sample on the first page? (demo write)",
            False,
        ):
            return
        parent: PyRecordModel = self.inst_man.add_existing_records(samples[:1])[0]
        result = create_aliquot_for_samples({parent: 1}, self.user)
        new_ids: list[int] = list(result.get(parent))
        self.callback.display_info(f"New aliquot record id(s): {new_ids}")
