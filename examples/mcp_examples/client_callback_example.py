"""
Created: 2026-03-18 12:00
Agent type: Composer
Modified: 2026-03-19 18:30
Agent type: Composer
Modified: 2026-03-20 12:00
Agent type: Composer

Python counterpart to the Java feature example ClientCallbackExample.java
(`sapio://examples/java/features/client-callback`).

Demonstrates `CallbackUtil` (`self.callback` on `CommonsWebhookHandler`) for messages, dialogs, files,
forms/tables, record selection, and e-sign. Category layout follows the Java ClientCallbackExample where applicable.

Primary API: `sapiopycommons.callbacks.callback_util.CallbackUtil`.
"""

from __future__ import annotations

import traceback
from datetime import datetime, timezone

from sapiopycommons.callbacks.field_builder import AnyFieldInfo, FieldBuilder
from sapiopycommons.general.custom_report_util import CustomReportUtil
from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.CustomReport import CustomReportCriteria, RawReportTerm, RawTermOperation, ReportColumn
from sapiopylib.rest.pojo.DataRecordPaging import DataRecordPojoPageCriteria
from sapiopylib.rest.pojo.datatype.FieldDefinition import (
    FieldType,
    VeloxBooleanFieldDefinition,
    VeloxDoubleFieldDefinition,
    VeloxEnumFieldDefinition,
    VeloxIntegerFieldDefinition,
    VeloxStringFieldDefinition,
)
from sapiopylib.rest.pojo.webhook.ClientCallbackRequest import PopupType
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult

# Temporary data type name for synthetic form/table field defs (CallbackUtil temp type contract).
_TEMP_DT: str = "TempClientCallbackDemo"


class ClientCallbackFeatureExample(CommonsWebhookHandler):
    """
    Menu-driven ClientCallback / CallbackUtil demo aligned with Java ClientCallbackExample.
    """

    CAT_MESSAGES: str = "Messages & Popups"
    CAT_SIMPLE_DIALOGS: str = "Simple Dialogs"
    CAT_LIST_SELECTION: str = "List Selection"
    CAT_FILE_OPS: str = "File Operations"
    CAT_FORM_TABLE: str = "Form & Table Entry"
    CAT_RECORD_SELECT: str = "Record Selection"
    CAT_ADVANCED: str = "E-Signature"

    MENU_OPTIONS: tuple[str, ...] = (
        CAT_MESSAGES,
        CAT_SIMPLE_DIALOGS,
        CAT_LIST_SELECTION,
        CAT_FILE_OPS,
        CAT_FORM_TABLE,
        CAT_RECORD_SELECT,
        CAT_ADVANCED,
    )

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.can_send_client_callback():
            return SapioWebhookResult(
                False,
                display_text="This handler needs an interactive WebhookEndpointType (client callback required).",
            )
        try:
            category: str = self.callback.option_dialog(
                "ClientCallback Examples",
                "Select a callback category to explore:",
                list(self.MENU_OPTIONS),
                0,
                user_can_cancel=True,
            )
            if category == self.CAT_MESSAGES:
                self._run_messages_demo()
            elif category == self.CAT_SIMPLE_DIALOGS:
                self._run_simple_dialogs_demo()
            elif category == self.CAT_LIST_SELECTION:
                self._run_list_selection_demo()
            elif category == self.CAT_FILE_OPS:
                self._run_file_operations_demo()
            elif category == self.CAT_FORM_TABLE:
                self._run_form_table_demo()
            elif category == self.CAT_RECORD_SELECT:
                self._run_record_selection_demo()
            elif category == self.CAT_ADVANCED:
                self._run_advanced_demo()
            else:
                self.callback.display_error(f"Unknown category: {category}")
                return SapioWebhookResult(False)
            return SapioWebhookResult(True)
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        except Exception as ex:
            tb: str = traceback.format_exc()
            self.callback.display_error(f"Error:\n{ex}\n\n{tb}")
            return SapioWebhookResult(False)

    def _run_messages_demo(self) -> None:
        """Java `runMessagesDemo` — same demo labels and branching."""
        demos: list[str] = [
            "displayMessage - Basic message",
            "displayInfo - Info (Display Info)",
            "displayWarning - Warning toast",
            "displayError - Error dialog",
            "displayPopup (Success)",
            "displayPopup (Warning)",
            "displayPopup (Error)",
            "displayPopup (Info)",
        ]
        try:
            selected: list[str] = self.callback.list_dialog(
                "Select Message Demos",
                demos,
                multi_select=True,
                shortcut_single_option=False,
            )
        except SapioUserCancelledException:
            return
        if not selected:
            return
        for demo in selected:
            if "displayMessage" in demo:
                self.callback.display_info("This is a basic message.")
            elif "displayInfo" in demo and "Display Info" in demo:
                self.callback.display_info("This is an informational message.")
            elif "displayWarning" in demo:
                self.callback.display_warning("This is a warning message.")
            elif "displayError" in demo and "dialog" in demo:
                self.callback.display_error("This is an error message.")
            elif "Success" in demo:
                self.callback.toaster_popup(
                    "Operation completed successfully!",
                    title="Success",
                    popup_type=PopupType.Success,
                )
            elif "Warning" in demo and "displayPopup" in demo:
                self.callback.toaster_popup(
                    "Please review before continuing.",
                    title="Warning",
                    popup_type=PopupType.Warning,
                )
            elif "Error" in demo and "displayPopup" in demo:
                self.callback.toaster_popup(
                    "An error occurred during processing.",
                    title="Error",
                    popup_type=PopupType.Error,
                )
            elif "Info" in demo and "displayPopup" in demo:
                self.callback.toaster_popup(
                    "Here is some helpful information.",
                    title="Information",
                    popup_type=PopupType.Info,
                )

    def _run_simple_dialogs_demo(self) -> None:
        """Java `runSimpleDialogsDemo` — same four submenu labels."""
        demos: list[str] = [
            "showInputDialog - Text input",
            "showOptionDialog - Option selection",
            "showYesNoDialog - Yes/No question",
            "showOkCancelDialog - OK/Cancel confirmation",
        ]
        try:
            choice: str = self.callback.option_dialog(
                "Select Simple Dialog Demo",
                "Choose a dialog type:",
                demos,
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return
        result_text: str = ""
        if choice == demos[0]:
            try:
                text_val: object = self.callback.input_dialog(
                    "Text Input",
                    "Enter a value:",
                    VeloxStringFieldDefinition(_TEMP_DT, "TextIn", "Value", max_length=200, editable=True),
                )
                result_text = f"You entered: {text_val}" if text_val is not None else "Input cancelled"
            except SapioUserCancelledException:
                result_text = "Input cancelled"
        elif choice == demos[1]:
            try:
                opts: list[str] = ["Option A", "Option B", "Option C"]
                opt: str = self.callback.option_dialog(
                    "Option Selection",
                    "Select an option:",
                    opts,
                    0,
                    user_can_cancel=True,
                )
                result_text = f"You selected: {opt}"
            except SapioUserCancelledException:
                result_text = "Selection cancelled"
        elif choice == demos[2]:
            yes: bool = self.callback.yes_no_dialog(
                "Confirmation",
                "Do you want to proceed?",
                default_yes=True,
            )
            result_text = "You clicked: Yes" if yes else "You clicked: No"
        elif choice == demos[3]:
            ok: bool = self.callback.ok_cancel_dialog(
                "Confirm Action",
                "Are you sure you want to continue?",
                default_ok=True,
            )
            result_text = "You clicked: OK" if ok else "You clicked: Cancel"
        self.callback.toaster_popup(result_text, title="Result", popup_type=PopupType.Success)

    def _run_list_selection_demo(self) -> None:
        """Java `runListSelectionDemo`."""
        modes: list[str] = ["Single selection list", "Multi-selection list"]
        try:
            mode: str = self.callback.option_dialog(
                "List Selection Demo",
                "Choose list type:",
                modes,
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return
        items: list[str] = ["Item 1", "Item 2", "Item 3", "Item 4", "Item 5"]
        multi: bool = mode == modes[1]
        title: str = "Select Items (Multi)" if multi else "Select Item (Single)"
        try:
            picked: list[str] = self.callback.list_dialog(
                title,
                items,
                multi_select=multi,
                shortcut_single_option=False,
            )
        except SapioUserCancelledException:
            return
        summary: str = f"Selected: {picked}" if picked else "Selection cancelled"
        self.callback.toaster_popup(summary, title="Result", popup_type=PopupType.Success)

    def _run_file_operations_demo(self) -> None:
        """Java `runFileOperationsDemo`."""
        ops: list[str] = [
            "showFileDialog - Single file upload",
            "showMultiFileDialog - Multiple file upload",
            "writeBytes - Download CSV file",
            "writeBytes - Download text file",
        ]
        try:
            op: str = self.callback.option_dialog(
                "File Operation Demo",
                "Choose operation:",
                ops,
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return
        if op == ops[0]:
            try:
                name: str
                _data: bytes
                name, _data = self.callback.request_file("Select a File", enforce_file_extensions=False)
                self.callback.display_info(f"Selected: {name}")
            except SapioUserCancelledException:
                self.callback.display_info("File selection cancelled")
        elif op == ops[1]:
            try:
                files: dict[str, bytes] = self.callback.request_files("Select Files", enforce_file_extensions=False)
                if files:
                    self.callback.display_info(f"Selected {len(files)} files")
                else:
                    self.callback.display_info("File selection cancelled")
            except SapioUserCancelledException:
                self.callback.display_info("File selection cancelled")
        elif op == ops[2]:
            csv_text: str = "ID,Name,Value\n1,Sample A,100\n2,Sample B,200\n3,Sample C,300"
            self.callback.write_file("export.csv", csv_text.encode("utf-8"))
            self.callback.display_info("CSV download initiated")
        elif op == ops[3]:
            text: str = (
                f"Sample Report\n\nGenerated: {datetime.now(timezone.utc).isoformat()}\n\nThis is sample content."
            )
            self.callback.write_file("report.txt", text.encode("utf-8"))
            self.callback.display_info("Text download initiated")

    def _run_form_table_demo(self) -> None:
        """Java `runFormTableDemo` / form / custom table / table from existing data type layout."""
        demos: list[str] = [
            "showFieldEntryDialog - Form input (custom fields)",
            "showTableEntryDialog - Table input (custom fields)",
            "showTableEntryDialog - Table using existing data type layout",
        ]
        try:
            d: str = self.callback.option_dialog(
                "Form/Table Demo",
                "Choose demo:",
                demos,
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return
        if d == demos[0]:
            self._run_form_entry_demo()
        elif d == demos[1]:
            self._run_table_entry_demo()
        else:
            self._run_table_entry_from_data_type_demo()

    def _run_form_entry_demo(self) -> None:
        """Java `runFormEntryDemo` — FormBuilder fields mirrored with Velox* definitions."""
        fields = [
            VeloxStringFieldDefinition(_TEMP_DT, "Name", "Name", max_length=100, required=True, editable=True),
            VeloxIntegerFieldDefinition(_TEMP_DT, "Age", "Age", min_value=0, max_value=150, editable=True),
            VeloxDoubleFieldDefinition(_TEMP_DT, "Score", "Score", default_value=0.0, editable=True),
            VeloxBooleanFieldDefinition(_TEMP_DT, "Active", "Active", default_value=True, editable=True),
            VeloxEnumFieldDefinition(
                _TEMP_DT,
                "Status",
                "Status",
                default_value=0,
                values=["Pending", "Active", "Complete"],
                required=True,
                editable=True,
            ),
        ]
        try:
            result: dict[str, object] = self.callback.form_dialog(
                "Form Entry Demo",
                "Enter the following information:",
                fields,
            )
        except SapioUserCancelledException:
            self.callback.display_info("Form cancelled")
            return
        if result is not None:
            lines: list[str] = [f"  {k}: {v}" for k, v in result.items()]
            self.callback.toaster_popup(
                "Form submitted:\n" + "\n".join(lines),
                title="Result",
                popup_type=PopupType.Success,
            )
        else:
            self.callback.display_info("Form cancelled")

    def _run_table_entry_demo(self) -> None:
        """Java `runTableEntryDemo` — same initial rows and columns."""
        cols = [
            VeloxStringFieldDefinition(_TEMP_DT, "SampleId", "Sample ID", required=True, editable=True),
            VeloxDoubleFieldDefinition(_TEMP_DT, "Volume", "Volume (µL)", default_value=0.0, editable=True),
            VeloxEnumFieldDefinition(
                _TEMP_DT,
                "Status",
                "Status",
                default_value=0,
                values=["Pending", "Active", "Complete"],
                required=True,
                editable=True,
            ),
        ]
        rows: list[dict[str, object]] = [
            {"SampleId": "SAMPLE-001", "Volume": 100.0, "Status": 1},
            {"SampleId": "SAMPLE-002", "Volume": 150.0, "Status": 0},
            {},
            {},
        ]
        try:
            out_rows: list[dict[str, object]] = self.callback.table_dialog(
                "Table Entry Demo",
                "Edit the data:",
                cols,
                rows,
            )
            self.callback.display_info(f"Table submitted with {len(out_rows)} rows")
        except SapioUserCancelledException:
            self.callback.display_info("Table entry cancelled")

    def _run_table_entry_from_data_type_demo(self) -> None:
        """Java `runTableEntryFromDataTypeDemo` — pick type, optional layout, empty rows on temp type."""
        names_sorted: list[str] = []
        for dt_name in self.dt_man.get_data_type_name_list():
            dt_def = self.dt_man.get_data_type_definition(dt_name)
            if dt_def is None:
                continue
            if dt_def.is_pseudo:
                continue
            names_sorted.append(dt_name)
        names_sorted.sort()
        if not names_sorted:
            self.callback.display_warning("No data types available")
            return
        try:
            chosen_types: list[str] = self.callback.list_dialog(
                "Select Data Type",
                names_sorted,
                multi_select=False,
                shortcut_single_option=False,
            )
        except SapioUserCancelledException:
            return
        if not chosen_types:
            return
        data_type_name: str = chosen_types[0]
        dt_def = self.dt_man.get_data_type_definition(data_type_name)
        if dt_def is None:
            self.callback.display_warning("Data type not found")
            return
        layouts = self.dt_man.get_data_type_layout_list(data_type_name) or []
        layout_name: str | None = None
        if len(layouts) == 1:
            layout_name = layouts[0].layout_name
        elif len(layouts) > 1:
            layout_names: list[str] = [x.layout_name for x in layouts]
            try:
                picked_layout: list[str] = self.callback.list_dialog(
                    "Select Layout",
                    layout_names,
                    multi_select=False,
                    shortcut_single_option=False,
                )
            except SapioUserCancelledException:
                return
            if picked_layout:
                layout_name = picked_layout[0]
        temp_type = self.dt_man.get_temporary_data_type(data_type_name, layout_name)
        if temp_type is None:
            self.callback.display_warning("Could not build temporary data type for selection")
            return
        field_list: list = temp_type.get_field_def_list()
        try:
            out_rows: list[dict[str, object]] = self.callback.table_dialog(
                f"Table Entry: {dt_def.display_name}",
                f"Enter data using the {data_type_name} data type fields:",
                field_list,
                5,
                data_type=data_type_name,
                display_name=dt_def.display_name,
                plural_display_name=dt_def.plural_display_name,
            )
            self.callback.display_info(f"Table submitted with {len(out_rows)} rows")
        except SapioUserCancelledException:
            self.callback.display_info("Table entry cancelled")

    def _run_record_selection_demo(self) -> None:
        """Java `runRecordSelectionDemo` — custom report + grid maps, then input selection."""
        demos: list[str] = [
            "showDataRecordSelectionDialog - Grid selection",
            "showInputSelectionDialog - Search selection",
        ]
        try:
            pick: str = self.callback.option_dialog(
                "Record Selection Demo",
                "Choose demo:",
                demos,
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return
        if pick == demos[0]:
            if self.dt_man.get_data_type_definition("Sample") is None:
                self.callback.display_warning("Sample data type not found")
                return
            criteria: CustomReportCriteria = CustomReportCriteria(
                column_list=[
                    ReportColumn("Sample", "RecordId", FieldType.LONG),
                    ReportColumn("Sample", "SampleId", FieldType.STRING),
                    ReportColumn("Sample", "ExemplarSampleType", FieldType.STRING),
                ],
                root_term=RawReportTerm(
                    "Sample",
                    "RecordId",
                    RawTermOperation.GREATER_THAN_OPERATOR,
                    "0",
                ),
                root_data_type="Sample",
                page_size=50,
                page_number=0,
            )
            try:
                rows: list[dict[str, object]] = CustomReportUtil.run_custom_report(
                    self.user,
                    criteria,
                    page_limit=1,
                    page_size=50,
                    page_number=0,
                )
            except Exception as ex:
                self.callback.display_warning(
                    f"Custom report (Sample.RecordId > 0) failed: {ex!s}. "
                    "Falling back to first page of query_all_records_of_type."
                )
                page = self.dr_man.query_all_records_of_type(
                    "Sample",
                    DataRecordPojoPageCriteria(page_number=0, page_size=50),
                )
                recs = list(page.records) if page.records else []
                if not recs:
                    self.callback.display_info("No Sample records found")
                    return
                try:
                    chosen_recs: list = self.callback.record_selection_dialog(
                        "Select samples:",
                        ["RecordId", "SampleId", "ExemplarSampleType"],
                        recs,
                        multi_select=True,
                        shortcut_single_option=False,
                    )
                except SapioUserCancelledException:
                    self.callback.display_info("Selection cancelled")
                    return
                if chosen_recs:
                    self.callback.display_info(f"Selected {len(chosen_recs)} records")
                else:
                    self.callback.display_info("Selection cancelled")
                return
            if not rows:
                self.callback.display_info("No Sample records found")
                return
            field_maps: list[dict[str, object]] = self._sample_report_rows_to_field_maps(rows)
            ro: AnyFieldInfo = AnyFieldInfo(editable=False, required=False, visible=True)
            fb: FieldBuilder = FieldBuilder("Sample")
            field_defs = [
                fb.long_field("RecordId", abstract_info=ro, display_name="Record ID"),
                fb.string_field("SampleId", abstract_info=ro, display_name="Sample ID"),
                fb.string_field("ExemplarSampleType", abstract_info=ro, display_name="Sample Type"),
            ]
            try:
                selected_maps: list[dict[str, object]] = self.callback.selection_dialog(
                    "Select samples:",
                    field_defs,
                    field_maps,
                    multi_select=True,
                    shortcut_single_option=False,
                )
            except SapioUserCancelledException:
                self.callback.display_info("Selection cancelled")
                return
            if selected_maps:
                self.callback.display_info(f"Selected {len(selected_maps)} records")
            else:
                self.callback.display_info("Selection cancelled")
        else:
            self.callback.input_selection_dialog(
                "Sample",
                "Search and select samples:",
                multi_select=False,
            )
            self.callback.display_info("Input selection dialog shown")

    @staticmethod
    def _sample_report_rows_to_field_maps(rows: list[dict[str, object]]) -> list[dict[str, object]]:
        """Normalize custom-report dict keys to field maps for `selection_dialog`."""
        out: list[dict[str, object]] = []
        for row in rows:
            rid: object = row.get("RecordId")
            if rid is None:
                rid = row.get("Sample.RecordId")
            sid: object = row.get("SampleId")
            if sid is None:
                sid = row.get("Sample.SampleId")
            st: object = row.get("ExemplarSampleType")
            if st is None:
                st = row.get("Sample.ExemplarSampleType")
            out.append(
                {
                    "RecordId": int(rid) if rid is not None else None,
                    "SampleId": sid,
                    "ExemplarSampleType": st,
                }
            )
        return out

    def _run_advanced_demo(self) -> None:
        """E-signature via `CallbackUtil.esign_dialog` (Java `showESignDialog`)."""
        resp = self.callback.esign_dialog(
            "Electronic Signature",
            "Please authenticate to confirm this action.",
            show_comment=True,
        )
        if resp.authenticated and resp.user_info is not None:
            uname: str | None = getattr(resp.user_info, "username", None)
            self.callback.display_info(f"Authenticated: {uname!s}")
        else:
            self.callback.display_info("Signature cancelled or failed")
