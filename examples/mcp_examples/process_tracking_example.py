"""
Created: 2026-03-19 15:20
Agent type: Composer
Modified: 2026-03-19 22:30
Agent type: Composer
Modified: 2026-03-20 12:00
Agent type: Composer

Python counterpart to Java ProcessTrackingExample.java
(`sapio://examples/java/features/process-tracking`).

Uses sapiopycommons.processtracking.endpoints.ProcessTracking for assign_to_process and read-only status views.
"""

from __future__ import annotations

import traceback

from sapiopycommons.callbacks.callback_util import BlankResultHandling
from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.processtracking.endpoints import ProcessTracking
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.DataRecordPaging import DataRecordPojoPageCriteria
from sapiopylib.rest.pojo.datatype.FieldDefinition import VeloxIntegerFieldDefinition
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult


class ProcessTrackingFeatureExample(CommonsWebhookHandler):
    OPT_SAMPLE_STATUS: str = "View Sample Process Status"
    OPT_PLATE_STATUS: str = "View Plate Process Status"
    OPT_ASSIGN: str = "Assign Sample to Process Step"

    MENU_OPTIONS: tuple[str, ...] = (
        OPT_SAMPLE_STATUS,
        OPT_PLATE_STATUS,
        OPT_ASSIGN,
    )
    _PROC_TRACK_TEMP_DT: str = "ProcTrackDemo"

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.can_send_client_callback():
            return SapioWebhookResult(False, display_text="Requires client callback.")
        try:
            choice: str = self.callback.option_dialog(
                "ProcessTracking Demo",
                "Select a demonstration:",
                list(self.MENU_OPTIONS),
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        try:
            if choice == self.OPT_SAMPLE_STATUS:
                self._run_sample_status()
            elif choice == self.OPT_PLATE_STATUS:
                self._run_plate_status()
            elif choice == self.OPT_ASSIGN:
                self._run_assign_to_process()
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        except Exception as ex:
            self.callback.display_error(f"Error:\n{ex!s}\n\n{traceback.format_exc()}")
            return SapioWebhookResult(False)
        return SapioWebhookResult(True)

    def _run_sample_status(self) -> None:
        page = self.dr_man.query_all_records_of_type(
            "Sample", DataRecordPojoPageCriteria(page_size=500)
        )
        samples = page.result_list or []
        with_status: list[tuple[int, str]] = []
        for s in samples:
            st = s.get_fields().get("ExemplarSampleStatus")
            if st is not None and str(st).strip():
                with_status.append((s.record_id, str(st)))
        if not with_status:
            self.callback.display_warning("No Sample records with ExemplarSampleStatus on first page.")
            return
        lines: list[str] = ["Sample process status (first page, max 20):\n\n"]
        for rid, st in with_status[:20]:
            lines.append(f" • RecordId {rid}: {st}\n")
        self.callback.display_info("".join(lines))

    def _run_plate_status(self) -> None:
        page = self.dr_man.query_all_records_of_type(
            "Plate", DataRecordPojoPageCriteria(page_size=200)
        )
        plates = page.result_list or []
        if not plates:
            self.callback.display_warning("No Plate records on first page.")
            return
        lines: list[str] = ["Plate records (first page, show status-like fields):\n\n"]
        for p in plates[:15]:
            fields = p.get_fields()
            status = fields.get("ExemplarPlateStatus") or fields.get("PlateStatus") or fields.get("Status")
            lines.append(f" • RecordId {p.record_id}: status={status!r}\n")
        self.callback.display_info("".join(lines))

    def _run_assign_to_process(self) -> None:
        models = self.callback.input_selection_dialog(
            "Sample",
            "Select Samples to assign:",
            multi_select=True,
        )
        if not models:
            self.callback.display_info("No samples selected.")
            return

        proc_page = self.dr_man.query_all_records_of_type(
            "Process", DataRecordPojoPageCriteria(page_size=500)
        )
        process_records = proc_page.result_list or []
        choices: list[tuple[str, str]] = []
        for pr in process_records:
            fields = pr.get_fields()
            raw_name: object = fields.get("ProcessName")
            pn: str = str(raw_name).strip() if raw_name is not None else ""
            if not pn:
                continue
            choices.append((f"{pn} (RecordId {pr.record_id})", pn))
        if not choices:
            self.callback.display_warning(
                "No Process definitions with a non-blank ProcessName found (query first page). "
                "Define processes in Foundations or increase page size if needed."
            )
            return

        try:
            label: str = self.callback.option_dialog(
                "Select Process",
                "Process to assign samples to:",
                [c[0] for c in choices],
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return

        process_name: str = ""
        for disp, pname in choices:
            if disp == label:
                process_name = pname
                break
        if not process_name:
            self.callback.display_warning("Could not resolve selected process.")
            return

        try:
            step_raw: object = self.callback.input_dialog(
                "Process step",
                "Step number (first step is usually 1):",
                VeloxIntegerFieldDefinition(
                    self._PROC_TRACK_TEMP_DT,
                    "StepNumber",
                    "Step number",
                    min_value=1,
                    max_value=999,
                    default_value=1,
                    editable=True,
                ),
                blank_result_handling=BlankResultHandling.REPEAT,
            )
        except SapioUserCancelledException:
            return
        step_number: int = int(step_raw) if step_raw is not None else 1

        if not self.callback.yes_no_dialog(
            "Confirm",
            f"POST assign_to_process for {len(models)} Sample(s) to process {process_name!r}, "
            f"step {step_number}? This changes workflow state.",
            False,
        ):
            return

        ids: list[int] = [m.record_id for m in models]
        ProcessTracking.assign_to_process(
            self.user,
            "Sample",
            ids,
            process_name,
            step_number=step_number,
        )
        self.callback.display_info(
            f"assign_to_process called for {len(ids)} Sample(s), "
            f"process={process_name!r}, step={step_number}."
        )
