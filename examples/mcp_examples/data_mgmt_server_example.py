"""
Created: 2026-03-19 15:20
Agent type: Composer
Modified: 2026-03-19 19:20
Agent type: Composer
Modified: 2026-03-20 12:00
Agent type: Composer

Python counterpart to Java DataMgmtServerExample.java
(`sapio://examples/java/features/data-mgmt-server`).

List available managers, create a Sample, or update the first Sample (description + commit).
"""

from __future__ import annotations

import traceback

from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.DataRecordPaging import DataRecordPojoPageCriteria
from sapiopylib.rest.pojo.datatype.FieldDefinition import VeloxStringFieldDefinition
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult

_TEMP_DT: str = "TempDataMgmtDemo"


class DataMgmtServerFeatureExample(CommonsWebhookHandler):
    OPT_LIST: str = "List Available Managers"
    OPT_CREATE: str = "Create a Sample record"
    OPT_UPDATE: str = "Update first Sample (set description)"
    MENU_OPTIONS: tuple[str, ...] = (OPT_LIST, OPT_CREATE, OPT_UPDATE)

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.can_send_client_callback():
            return SapioWebhookResult(False, display_text="Requires client callback.")
        try:
            choice: str = self.callback.option_dialog(
                "DataMgmtServer Examples",
                "Select which demonstration to run:",
                list(self.MENU_OPTIONS),
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        try:
            if choice == self.OPT_LIST:
                self._run_list_managers_demo()
            elif choice == self.OPT_CREATE:
                self._run_create_sample_demo()
            elif choice == self.OPT_UPDATE:
                self._run_update_first_sample_demo()
            else:
                self.callback.display_error("Unknown option selected.")
                return SapioWebhookResult(False)
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        except Exception as ex:
            self.callback.display_error(
                f"DataMgmtServer Example Error:\n{ex}\n\n{traceback.format_exc()}"
            )
            return SapioWebhookResult(False)
        return SapioWebhookResult(True)

    def _run_list_managers_demo(self) -> None:
        """Java runListManagersDemo — same sectioned list of managers."""
        output: str = (
            "Available Managers\n\n"
            "=== AVAILABLE MANAGERS ===\n\n"
            "DATA MANAGEMENT:\n"
            "• DataRecordManager - CRUD operations on records\n"
            "• DataTypeManager - Data type definitions\n"
            "• DataFieldDefManager - Field definitions\n\n"
            "USER & SESSION:\n"
            "• VeloxUserManager - User management\n"
            "• UserGroupManager - User groups\n"
            "• SessionManager - Session management\n\n"
            "ELN:\n"
            "• NotebookExperimentManager - ELN experiments\n\n"
            "REPORTING:\n"
            "• CustomReportManager - Ad-hoc queries\n"
            "• DashboardManager - Dashboards\n\n"
            "SYSTEM:\n"
            "• WorkflowManager - Workflows\n"
            "• AccessionManager - Auto-numbering\n"
            "• PickListManager - Pick lists\n"
        )
        self.callback.display_info(output)

    def _run_create_sample_demo(self) -> None:
        """Java runCreateSampleDemo — confirm, addDataRecord, optional description, storeAndCommit."""
        try:
            confirm: str = self.callback.option_dialog(
                "Create Sample",
                "This will create a new Sample record and commit it to the system. Proceed?",
                ["Proceed", "Cancel"],
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return
        if confirm != "Proceed":
            return
        try:
            record = self.dr_man.add_data_record("Sample")
            try:
                desc_raw: object = self.callback.input_dialog(
                    "Optional description",
                    "Optional: Enter a description for the new sample (or leave blank):",
                    VeloxStringFieldDefinition(_TEMP_DT, "Description", "Description", max_length=2000, editable=True),
                )
                if desc_raw is not None and str(desc_raw).strip():
                    record.set_field_value("Description", str(desc_raw).strip())
            except SapioUserCancelledException:
                pass
            except Exception:
                pass  # Description field may not exist on all Sample types
            self.dr_man.commit_data_records([record])
            rec_id: int = record.record_id
            self.callback.display_info(
                f"Created Sample record (RecordId: {rec_id}) and committed."
            )
        except Exception as ex:
            raise ex

    def _run_update_first_sample_demo(self) -> None:
        """Java runUpdateFirstSampleDemo — getAllRecordsOfType, confirm, input description, setDataField, storeAndCommit."""
        page = self.dr_man.query_all_records_of_type(
            "Sample",
            DataRecordPojoPageCriteria(page_size=1, page_number=0),
        )
        records = list(page.records) if page.records else []
        if not records:
            self.callback.display_warning("No Sample records found. Create a sample first.")
            return
        first = records[0]
        rec_id: int = first.record_id
        try:
            confirm: str = self.callback.option_dialog(
                "Update first Sample",
                f"This will set the Description on the first Sample (RecordId: {rec_id}) and commit. Proceed?",
                ["Proceed", "Cancel"],
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return
        if confirm != "Proceed":
            return
        try:
            desc_raw: object = self.callback.input_dialog(
                "Description",
                "Enter description for the sample:",
                VeloxStringFieldDefinition(_TEMP_DT, "Description", "Description", max_length=2000, editable=True),
            )
            if desc_raw is None:
                return
            try:
                first.set_field_value("Description", str(desc_raw))
            except Exception as ex:
                self.callback.display_error(
                    f"This Sample type may not have a Description field: {ex}"
                )
                return
            self.dr_man.commit_data_records([first])
            self.callback.display_info(f"Updated Sample (RecordId: {rec_id}) and committed.")
        except Exception as ex:
            raise ex
