"""
Created: 2026-03-19 15:20
Agent type: Composer
Modified: 2026-03-19 19:15
Agent type: Composer
Modified: 2026-03-20 12:00
Agent type: Composer

Python counterpart to Java CustomReportManagerExample.java
(`sapio://examples/java/features/custom-report-manager`).

Run a system report by name (table view) or an ad-hoc Sample report; results are shown in a table dialog.
"""

from __future__ import annotations

import traceback
from typing import Any

from sapiopycommons.general.custom_report_util import CustomReportUtil
from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.CustomReport import CustomReportCriteria, RawReportTerm, RawTermOperation, ReportColumn
from sapiopylib.rest.pojo.datatype.FieldDefinition import FieldType
from sapiopylib.rest.pojo.datatype.FieldDefinition import VeloxStringFieldDefinition
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult

_TEMP_DT: str = "TempReportResults"


class CustomReportManagerFeatureExample(CommonsWebhookHandler):
    OPT_SYSTEM: str = "Run System Report (Table View)"
    OPT_ADHOC: str = "Run Ad-Hoc Report (Table View)"
    MENU_OPTIONS: tuple[str, ...] = (OPT_SYSTEM, OPT_ADHOC)

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.can_send_client_callback():
            return SapioWebhookResult(False, display_text="Interactive demos require client callback.")
        try:
            choice: str = self.callback.option_dialog(
                "CustomReportManager Examples",
                "Select which demonstration to run:",
                list(self.MENU_OPTIONS),
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        try:
            if choice == self.OPT_SYSTEM:
                self._run_system_report_demo()
            elif choice == self.OPT_ADHOC:
                self._run_adhoc_report_demo()
            else:
                self.callback.display_error("Unknown option selected.")
                return SapioWebhookResult(False)
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        except Exception as ex:
            self.callback.display_error(
                f"CustomReportManager Example Error:\n{ex}\n\n{traceback.format_exc()}"
            )
            return SapioWebhookResult(False)
        return SapioWebhookResult(True)

    def _run_system_report_demo(self) -> None:
        """Java runSystemReportDemo — user picks report, run with page 100, display in table dialog."""
        try:
            report_name_raw: object = self.callback.input_dialog(
                "System report name",
                "Enter a predefined search / system report name (must exist in Data Designer):",
                VeloxStringFieldDefinition(_TEMP_DT, "ReportName", "Report name", max_length=500, editable=True),
            )
        except SapioUserCancelledException:
            return
        if report_name_raw is None or not str(report_name_raw).strip():
            return
        report_name = str(report_name_raw).strip()
        try:
            criteria = CustomReportUtil.get_system_report_criteria(self.user, report_name)
        except Exception as ex:
            self.callback.display_warning(f"No system report named {report_name!r}: {ex}")
            return
        if criteria is None:
            self.callback.display_warning(
                f"No system report named {report_name!r}.\n\n"
                "Predefined searches must exist in Data Designer. "
                "User-saved searches are not available for this API call."
            )
            return
        criteria.page_size = 100
        criteria.page_number = 0
        result = self.report_man.run_custom_report(criteria)
        row_count: int = len(result.result_table) if result.result_table else 0
        if row_count == 0:
            self.callback.display_info(
                f"Report Results\n\nReport {report_name!r} returned no results."
            )
            return
        self._display_report_results_in_table(report_name, result, row_count)

    def _run_adhoc_report_demo(self) -> None:
        """Java runAdHocReportDemo — ad-hoc Sample report with same columns and term, table dialog."""
        if self.dt_man.get_data_type_definition("Sample") is None:
            self.callback.display_warning(
                "Data Type Not Found\n\nThe 'Sample' data type does not exist. This demo requires the Sample data type."
            )
            return
        criteria: CustomReportCriteria = CustomReportCriteria(
            column_list=[
                ReportColumn("Sample", "RecordId", FieldType.LONG),
                ReportColumn("Sample", "SampleId", FieldType.STRING),
                ReportColumn("Sample", "OtherSampleId", FieldType.STRING),
                ReportColumn("Sample", "ExemplarSampleType", FieldType.STRING),
                ReportColumn("Sample", "ExemplarSampleStatus", FieldType.STRING),
                ReportColumn("Sample", "DateCreated", FieldType.DATE),
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
        result = self.report_man.run_custom_report(criteria)
        row_count = len(result.result_table) if result.result_table else 0
        if row_count == 0:
            self.callback.display_info(
                "Report Results\n\nAd-hoc Sample report returned no results."
            )
            return
        self._display_report_results_in_table("Ad-Hoc Sample Report", result, row_count)

    def _display_report_results_in_table(
        self,
        report_name: str,
        report: Any,
        row_count: int,
    ) -> None:
        """Mirror Java displayReportResultsInTable — build string columns from report columns, stringify rows, table_dialog."""
        columns = report.column_list
        rows_raw = report.result_table or []
        row_dicts: list[dict[str, Any]] = CustomReportUtil._process_results(
            rows_raw, columns, None
        )
        display_data: list[dict[str, object]] = []
        for row in row_dicts:
            display_data.append(
                {k: (str(v) if v is not None else "") for k, v in row.items()}
            )
        fields: list[VeloxStringFieldDefinition] = []
        for col in columns:
            display_name: str = getattr(col, "data_field_name", col.data_field_name)
            fields.append(
                VeloxStringFieldDefinition(
                    _TEMP_DT,
                    col.data_field_name,
                    display_name,
                    required=False,
                    editable=False,
                )
            )
        msg: str = (
            f"Report: {report_name}\nTotal rows: {row_count}"
            + (" (more pages available)" if getattr(report, "has_next_page", False) else " (all results shown)")
        )
        try:
            self.callback.table_dialog(
                "Report Results",
                msg,
                fields,
                display_data,
                data_type=_TEMP_DT,
            )
        except SapioUserCancelledException:
            return
