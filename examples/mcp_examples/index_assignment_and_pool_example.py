"""
Created: 2026-03-19 15:20
Agent type: Composer
Modified: 2026-03-19 16:50
Agent type: Composer

Python counterpart to Java IndexAssignmentAndPoolExamplePlugin.java
(`sapio://examples/java/features/index-assignment-and-pool`).

Assign indexes and pool samples (IndexAssignment, IndexBarcode children, pool Sample, store_andCommit). List-for-pool
uses parent Sample links and IndexBarcode children per constituent.
"""

from __future__ import annotations

import time
import traceback

from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.DataRecord import DataRecord
from sapiopylib.rest.pojo.DataRecordPaging import DataRecordPojoPageCriteria
from sapiopylib.rest.utils.recordmodel.PyRecordModel import PyRecordModel
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult


class IndexAssignmentAndPoolFeatureExample(CommonsWebhookHandler):
    INDEX_ASSIGNMENT: str = "IndexAssignment"
    INDEX_BARCODE: str = "IndexBarcode"
    SAMPLE: str = "Sample"
    INDEX_TYPES_PICKLIST: str = "Index Types"

    OPT_ASSIGN: str = "Assign indexes and pool samples"
    OPT_LIST: str = "List index assignments for a pool"
    OPT_CANCEL: str = "Cancel"

    MENU_OPTIONS: tuple[str, ...] = (OPT_ASSIGN, OPT_LIST, OPT_CANCEL)

    @staticmethod
    def _field_str(fields: dict[str, object], key: str) -> str:
        v: object | None = fields.get(key)
        return "" if v is None else str(v)

    def _index_types(self) -> list[str]:
        cfg = self.list_man.get_picklist(self.INDEX_TYPES_PICKLIST)
        if cfg is not None and cfg.entry_list:
            return list(cfg.entry_list)
        page = self.dr_man.query_all_records_of_type(
            "IndexAssignmentBatch", DataRecordPojoPageCriteria(page_size=200)
        )
        out: list[str] = []
        for rec in page.result_list or []:
            fm = rec.get_fields()
            t = fm.get("IndexType")
            if t is not None and str(t).strip():
                out.append(str(t).strip())
        return sorted(set(out))

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.can_send_client_callback():
            return SapioWebhookResult(False, display_text="Requires client callback.")
        try:
            choice: str = self.callback.option_dialog(
                "Index Assignment and Pool Examples",
                "Select an option:",
                list(self.MENU_OPTIONS),
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        if choice == self.OPT_CANCEL:
            return SapioWebhookResult(True)
        try:
            if choice == self.OPT_ASSIGN:
                self._run_assign_and_pool()
            elif choice == self.OPT_LIST:
                self._run_list_for_pool()
            else:
                self.callback.display_error("Unknown option selected.")
                return SapioWebhookResult(False)
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        except Exception as ex:
            self.callback.display_error(
                f"Index Assignment and Pool Example Error:\n{ex!s}\n\n{traceback.format_exc()}"
            )
            return SapioWebhookResult(False)
        return SapioWebhookResult(True)

    def _run_assign_and_pool(self) -> None:
        index_types: list[str] = self._index_types()
        if not index_types:
            self.callback.display_warning(
                "No index types found. Configure 'Index Types' pick list or create IndexAssignmentBatch records."
            )
            return
        try:
            picked: list[str] = self.callback.list_dialog(
                "Select index type",
                index_types,
                multi_select=False,
                shortcut_single_option=False,
            )
        except SapioUserCancelledException:
            return
        if not picked:
            return
        selected_type: str = picked[0]
        page = self.dr_man.query_data_records(
            self.INDEX_ASSIGNMENT, "IndexType", [selected_type]
        )
        index_assignments: list[DataRecord] = page.result_list or []
        if not index_assignments:
            self.callback.display_warning(
                f"No Index Assignment records found for type: {selected_type}"
            )
            return

        def sort_key(r: DataRecord) -> str:
            return self._field_str(r.get_fields(), "IndexId")

        index_assignments = sorted(index_assignments, key=sort_key)
        assignment_field_rows: list[dict[str, object]] = [r.get_fields() for r in index_assignments]

        try:
            samples: list[PyRecordModel] = self.callback.input_selection_dialog(
                self.SAMPLE,
                "Select samples to assign indexes to and pool",
                multi_select=True,
            )
        except SapioUserCancelledException:
            return
        if not samples:
            self.callback.display_info("No samples selected.")
            return

        if not self.callback.yes_no_dialog(
            "Confirm",
            "Create IndexBarcode children, a pool Sample, and parent links? This commits data.",
            False,
        ):
            return

        per_parent: dict[DataRecord, list[dict[str, object]]] = {}
        for i, sm in enumerate(samples):
            sample_dr: DataRecord = sm.get_data_record()
            sf: dict[str, object] = sample_dr.get_fields()
            af: dict[str, object] = assignment_field_rows[i % len(assignment_field_rows)]
            rid = af.get("RecordId")
            barcode_fields: dict[str, object] = {
                "IndexId": af.get("IndexId"),
                "IndexTag": af.get("IndexTag"),
                "InputAssignmentRecordId": rid,
                "SampleId": sf.get("SampleId"),
                "OtherSampleId": sf.get("OtherSampleId"),
                "RowPosition": sf.get("RowPosition"),
                "ColPosition": sf.get("ColPosition"),
            }
            per_parent[sample_dr] = [barcode_fields]

        self.dr_man.create_children_fields_for_parents(self.INDEX_BARCODE, per_parent)

        pool_id: str = f"Pool-{int(time.time() * 1000)}"
        pool_models: list[PyRecordModel] = self.inst_man.add_new_records(self.SAMPLE, 1)
        pool_models[0].set_field_value("SampleId", pool_id)
        if not pool_models:
            self.callback.display_warning("Could not create pool Sample record.")
            return
        pool_model: PyRecordModel = pool_models[0]
        pool_dr: DataRecord = pool_model.get_data_record()
        for sm in samples:
            sm.add_children([pool_model])
        self.rec_man.store_and_commit()
        self.callback.display_info(
            f"Assigned index type {selected_type!r} to {len(samples)} sample(s) and created pool "
            f"{pool_id!r} (RecordId: {pool_dr.get_record_id()})."
        )

    def _run_list_for_pool(self) -> None:
        try:
            selected: list[PyRecordModel] = self.callback.input_selection_dialog(
                self.SAMPLE,
                "Select a pool (sample tube) to list index assignments for its samples",
                multi_select=False,
            )
        except SapioUserCancelledException:
            return
        if not selected:
            self.callback.display_info("No pool selected.")
            return
        pool_rec: DataRecord = selected[0].get_data_record()
        pool_id: int = pool_rec.get_record_id()

        hier = self.dr_man.get_parents_list(
            [pool_id], child_type_name=self.SAMPLE, parent_type_name=self.SAMPLE
        )
        constituents: list[DataRecord] = hier.result_map.get(pool_id, [])
        if not constituents:
            self.callback.display_warning(
                "Selected record has no parent samples (it may not be a pool)."
            )
            return

        lines: list[str] = [
            f"=== Index data for samples in pool (RecordId: {pool_id}) ===\n",
            "IndexBarcode children per constituent sample:\n\n",
        ]
        for srec in constituents:
            sf = srec.get_fields()
            sid = self._field_str(sf, "SampleId") or f"RecordId {srec.get_record_id()}"
            lines.append(f"Sample: {sid} (RecordId: {srec.get_record_id()})\n")
            ch_page = self.dr_man.get_children(
                srec.get_record_id(), self.INDEX_BARCODE, DataRecordPojoPageCriteria(page_size=50)
            )
            barcodes: list[DataRecord] = ch_page.result_list or []
            if not barcodes:
                lines.append("  IndexId: -  IndexTag: -\n\n")
                continue
            ids: list[str] = []
            tags: list[str] = []
            for bc in barcodes:
                bf = bc.get_fields()
                index_tag = bf.get("IndexTag")
                index_id = bf.get("IndexId")
                if isinstance(index_tag, str) and ":" in index_tag:
                    parts = index_tag.split(":", 1)
                    index_id = parts[0]
                    index_tag = parts[1]
                if index_id is not None:
                    ids.append(str(index_id))
                if index_tag is not None:
                    tags.append(str(index_tag))
            lines.append(
                f"  IndexId: {','.join(ids) if ids else '-'}  "
                f"IndexTag: {','.join(tags) if tags else '-'}\n\n"
            )
        self.callback.display_info("".join(lines))
