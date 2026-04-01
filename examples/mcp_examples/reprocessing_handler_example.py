"""
Created: 2026-03-19 15:20
Agent type: Composer
Modified: 2026-03-19 23:45
Agent type: Composer
Modified: 2026-03-20 12:00
Agent type: Composer

Python counterpart to Java ReprocessingHandlerExample.java
(`sapio://examples/java/features/reprocessing-handler`).

ReturnPoint reprocess, fail samples, and read-only views of AssignedProcess / ReturnPoint records via ProcessTracking.
"""

from __future__ import annotations

import traceback

from sapiopycommons.callbacks.callback_util import BlankResultHandling
from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.processtracking.endpoints import ProcessTracking
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.DataRecordPaging import DataRecordPojoPageCriteria
from sapiopylib.rest.pojo.datatype.FieldDefinition import VeloxStringFieldDefinition
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult


class ReprocessingHandlerFeatureExample(CommonsWebhookHandler):
    OPT_HANDLE: str = "Handle Reprocessing (Basic)"
    OPT_FAIL_ONLY: str = "Fail Records Only"
    OPT_VIEW_ASSIGNED: str = "View AssignedProcess Records"
    OPT_VIEW_RETURN: str = "View ReturnPoint Records"

    MENU_OPTIONS: tuple[str, ...] = (
        OPT_HANDLE,
        OPT_FAIL_ONLY,
        OPT_VIEW_ASSIGNED,
        OPT_VIEW_RETURN,
    )

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.can_send_client_callback():
            return SapioWebhookResult(False, display_text="Requires client callback.")
        try:
            choice: str = self.callback.option_dialog(
                "ReprocessingHandler Examples",
                "Select which demonstration to run:\n\n"
                "Select a demonstration:",
                list(self.MENU_OPTIONS),
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        try:
            if choice == self.OPT_HANDLE:
                self._run_handle_reprocessing()
            elif choice == self.OPT_FAIL_ONLY:
                self._run_fail_only()
            elif choice == self.OPT_VIEW_ASSIGNED:
                self._run_view_assigned()
            elif choice == self.OPT_VIEW_RETURN:
                self._run_view_return_points()
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        except Exception as ex:
            self.callback.display_error(f"Error:\n{ex!s}\n\n{traceback.format_exc()}")
            return SapioWebhookResult(False)
        return SapioWebhookResult(True)

    def _run_handle_reprocessing(self) -> None:
        models = self.callback.input_selection_dialog(
            "ReturnPoint",
            "Select ReturnPoint record(s) to reprocess to (creates new AssignedProcess):",
            multi_select=True,
        )
        if not models:
            self.callback.display_info("No ReturnPoint records selected.")
            return
        ids: list[int] = [m.record_id for m in models]
        if not self.callback.yes_no_dialog(
            "Confirm reprocess",
            f"POST reprocess for {len(ids)} ReturnPoint record ID(s)? This changes workflow state.",
            False,
        ):
            return
        ProcessTracking.reprocess(self.user, ids)
        self.callback.display_info(
            f"ProcessTracking.reprocess completed for ReturnPoint record IDs: {ids}"
        )

    def _run_fail_only(self) -> None:
        if not self.callback.yes_no_dialog(
            "Fail samples",
            "POST ProcessTracking.fail? Tracked records must be In Process for the given experiment.",
            False,
        ):
            return
        exp_raw: object = self.callback.input_dialog(
            "Experiment",
            "Notebook / experiment ID (integer):",
            VeloxStringFieldDefinition("ExpId", "Experiment", "Notebook ID", max_length=32, editable=True),
            blank_result_handling=BlankResultHandling.REPEAT,
        )
        exp_str: str = str(exp_raw).strip() if exp_raw is not None else ""
        try:
            exp_id: int = int(exp_str)
        except ValueError:
            self.callback.display_warning(f"Not an integer: {exp_str!r}")
            return
        models = self.callback.input_selection_dialog(
            "Sample",
            "Select Sample record(s) to fail:",
            multi_select=True,
        )
        if not models:
            self.callback.display_info("No samples selected.")
            return
        ids: list[int] = [m.record_id for m in models]
        ProcessTracking.fail(self.user, "Sample", ids, exp_id)
        self.callback.display_info(
            f"ProcessTracking.fail called for {len(ids)} Sample(s), experiment_id={exp_id}."
        )

    def _run_view_assigned(self) -> None:
        page = self.dr_man.query_all_records_of_type(
            "AssignedProcess", DataRecordPojoPageCriteria(page_size=50)
        )
        recs = page.result_list or []
        if not recs:
            self.callback.display_warning("No AssignedProcess records on first page.")
            return
        lines: list[str] = ["AssignedProcess (first page, key fields):\n\n"]
        for r in recs[:20]:
            fields = r.get_fields()
            status = fields.get("Status") or fields.get("ExemplarSampleStatus")
            lines.append(f" • RecordId {r.record_id}: Status={status!r}\n")
        self.callback.display_info("".join(lines))

    def _run_view_return_points(self) -> None:
        page = self.dr_man.query_all_records_of_type(
            "ReturnPoint", DataRecordPojoPageCriteria(page_size=50)
        )
        recs = page.result_list or []
        if not recs:
            self.callback.display_warning("No ReturnPoint records on first page.")
            return
        lines: list[str] = ["ReturnPoint (first page):\n\n"]
        for r in recs[:20]:
            fields = r.get_fields()
            step = fields.get("ProcessStepNumber") or fields.get("StepNumber")
            lines.append(f" • RecordId {r.record_id}: step hint={step!r}\n")
        lines.append(
            "\nUse these ReturnPoint record IDs with ProcessTracking.reprocess (not Sample IDs)."
        )
        self.callback.display_info("".join(lines))
