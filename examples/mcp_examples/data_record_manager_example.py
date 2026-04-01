"""
Created: 2026-03-19 15:20
Agent type: Composer
Modified: 2026-03-19 21:10
Agent type: Composer

Python counterpart to Java DataRecordManagerExample.java
(`sapio://examples/java/features/data-record-manager`).

Uses paged query_all_records_of_type, query_data_records(field, value_list), and Custom Reports for complex filters.
Create/rollback demo uses RecordModelManager.rollback() because REST add_data_record persists immediately.
"""

from __future__ import annotations

import traceback

from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.DataRecord import DataRecord
from sapiopylib.rest.pojo.DataRecordPaging import DataRecordPojoPageCriteria
from sapiopylib.rest.utils.recordmodel.PyRecordModel import PyRecordModel
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult


class DataRecordManagerFeatureExample(CommonsWebhookHandler):
    OPT_QUERY_VALUES: str = "Query by Known Values (Recommended)"
    OPT_QUERY_ALL: str = "Query All Records of Type"
    OPT_GET_FIELDS: str = "Get Fields for Records"
    OPT_CREATE_COMMIT: str = "Create and Commit Records"
    OPT_CREATE_ROLLBACK: str = "Create and Rollback (demo)"
    OPT_RELATIONSHIPS: str = "Navigate Relationships"
    OPT_BATCH: str = "Batch Operations"
    OPT_CANCEL: str = "Cancel"

    MENU_OPTIONS: tuple[str, ...] = (
        OPT_QUERY_VALUES,
        OPT_QUERY_ALL,
        OPT_GET_FIELDS,
        OPT_CREATE_COMMIT,
        OPT_CREATE_ROLLBACK,
        OPT_RELATIONSHIPS,
        OPT_BATCH,
        OPT_CANCEL,
    )

    @staticmethod
    def _to_display_string(value: object | None) -> str:
        return "" if value is None else str(value)

    def _collect_all_records(
        self, data_type_name: str, max_records: int = 100_000, page_size: int = 500
    ) -> list[DataRecord]:
        out: list[DataRecord] = []
        criteria: DataRecordPojoPageCriteria | None = DataRecordPojoPageCriteria(
            page_size=page_size
        )
        pages: int = 0
        while len(out) < max_records and pages < 500:
            pages += 1
            page = self.dr_man.query_all_records_of_type(data_type_name, criteria)
            out.extend(page.result_list)
            if not page.is_next_page_available or page.next_page_criteria is None:
                break
            criteria = page.next_page_criteria
        return out[:max_records]

    def _prompt_for_data_type(self) -> str | None:
        names_sorted: list[str] = []
        for dt_name in self.dt_man.get_data_type_name_list():
            names_sorted.append(dt_name)
        names_sorted.sort()
        if not names_sorted:
            self.callback.display_warning("No data types available for selection.")
            return None
        if "Sample" in names_sorted:
            names_sorted.remove("Sample")
            names_sorted.insert(0, "Sample")
        try:
            selected: list[str] = self.callback.list_dialog(
                "Select a Data Type",
                names_sorted,
                multi_select=False,
                shortcut_single_option=False,
            )
        except SapioUserCancelledException:
            return None
        return selected[0] if selected else None

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.can_send_client_callback():
            return SapioWebhookResult(False, display_text="Requires client callback.")
        try:
            choice: str = self.callback.option_dialog(
                "DataRecordManager Examples",
                "Select which demonstration to run:\n\n"
                "These examples show how to use the DataRecordManager\n"
                "to query, create, and manage data records.",
                list(self.MENU_OPTIONS),
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        if choice == self.OPT_CANCEL:
            return SapioWebhookResult(True)
        try:
            if choice == self.OPT_QUERY_VALUES:
                self._run_query_by_values_demo()
            elif choice == self.OPT_QUERY_ALL:
                self._run_query_all_records_demo()
            elif choice == self.OPT_GET_FIELDS:
                self._run_get_fields_demo()
            elif choice == self.OPT_CREATE_COMMIT:
                self._run_create_and_commit_demo()
            elif choice == self.OPT_CREATE_ROLLBACK:
                self._run_create_rollback_demo()
            elif choice == self.OPT_RELATIONSHIPS:
                self._run_relationships_demo()
            elif choice == self.OPT_BATCH:
                self._run_batch_operations_demo()
            else:
                self.callback.display_error("Unknown option selected.")
                return SapioWebhookResult(False)
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        except Exception as ex:
            self.callback.display_error(
                f"DataRecordManager Example Error:\n{ex!s}\n\n{traceback.format_exc()}"
            )
            return SapioWebhookResult(False)
        return SapioWebhookResult(True)

    def _run_query_by_values_demo(self) -> None:
        data_type_name: str | None = self._prompt_for_data_type()
        if data_type_name is None:
            return
        all_recs: list[DataRecord] = self._collect_all_records(data_type_name, max_records=5000)
        if not all_recs:
            self.callback.display_info(f"No records of type '{data_type_name}' found (first pages).")
            return
        sample: DataRecord = all_recs[0]
        field_names: list[str] = sorted(sample.get_fields().keys())
        try:
            chosen: list[str] = self.callback.list_dialog(
                "Select field to query by",
                field_names,
                multi_select=False,
                shortcut_single_option=False,
            )
        except SapioUserCancelledException:
            return
        if not chosen:
            return
        field_name: str = chosen[0]
        try:
            selected_models: list[PyRecordModel] = self.callback.input_selection_dialog(
                data_type_name,
                "Select records to derive value(s) for query",
                multi_select=True,
            )
        except SapioUserCancelledException:
            return
        if not selected_models:
            self.callback.display_info("No records selected.")
            return
        values: list[object] = []
        for m in selected_models:
            v: object = m.get_field_value(field_name)
            if v is not None:
                values.append(v)
        if not values:
            self.callback.display_info(f"No values for field '{field_name}'.")
            return
        page = self.dr_man.query_data_records(data_type_name, field_name, values)
        found: list[DataRecord] = page.result_list
        sb: list[str] = [
            "=== Query by Known Values ===\n\n",
            f"Data Type: {data_type_name}\n",
            f"Field: {field_name}\n",
            f"Value(s) queried: {values!r}\n",
            f"Records found (first page): {len(found)}\n",
        ]
        if found:
            first_fields: dict[str, object] = found[0].get_fields()
            sb.append("\nFirst record fields (sample):\n")
            n: int = 0
            for k, v in first_fields.items():
                if n >= 5:
                    break
                sb.append(f"  {k}: {self._to_display_string(v)}\n")
                n += 1
        self.callback.display_info("".join(sb))

    def _run_query_all_records_demo(self) -> None:
        data_type_name: str | None = self._prompt_for_data_type()
        if data_type_name is None:
            return
        all_recs: list[DataRecord] = self._collect_all_records(data_type_name)
        total_count: int = len(all_recs)
        lines: list[str] = [
            "=== QUERY ALL RECORDS OF TYPE ===\n\n",
            f"Data Type: {data_type_name}\n\n",
            "--- Using query_all_records_of_type() (paged) ---\n\n",
            f"Total records retrieved (up to cap): {total_count}\n\n",
        ]
        if all_recs:
            lines.append("First 3 RecordIds: ")
            lines.append(" ".join(str(all_recs[i].record_id) for i in range(min(3, len(all_recs)))))
            lines.append("\n\nFirst 5 records:\n")
            for i in range(min(5, len(all_recs))):
                rec: DataRecord = all_recs[i]
                line: str = f"  {i + 1}. RecordId: {rec.record_id}"
                fields: dict[str, object] = rec.get_fields()
                for fn in ("SampleId", "RequestId", "Name", "ExperimentName"):
                    if fn in fields and fields[fn] is not None:
                        line += f", {fn}: {self._to_display_string(fields[fn])}"
                        break
                lines.append(line + "\n")
            if len(all_recs) > 5:
                lines.append(f"  ... and {len(all_recs) - 5} more\n")
        self.callback.display_info("".join(lines))

    def _run_get_fields_demo(self) -> None:
        data_type_name: str | None = self._prompt_for_data_type()
        if data_type_name is None:
            return
        try:
            selected_models: list[PyRecordModel] = self.callback.input_selection_dialog(
                data_type_name,
                "Select records to get fields for",
                multi_select=True,
            )
        except SapioUserCancelledException:
            return
        if not selected_models:
            self.callback.display_info("No records selected.")
            return
        first: PyRecordModel = selected_models[0]
        field_map: dict[str, object] = first.fields.copy_to_dict()
        sb: list[str] = [
            "=== Get Fields for Records ===\n\n",
            f"Data Type: {data_type_name}\n",
            f"Records selected: {len(selected_models)}\n",
            f"\nFirst record field count: {len(field_map)}\n",
        ]
        n: int = 0
        for k, v in field_map.items():
            if n >= 5:
                break
            sb.append(f"  {k}: {self._to_display_string(v)}\n")
            n += 1
        self.callback.display_info("".join(sb))

    def _run_create_and_commit_demo(self) -> None:
        data_type_name: str | None = self._prompt_for_data_type()
        if data_type_name is None:
            return
        if not self.callback.yes_no_dialog(
            "Create and Commit Records",
            f"This will create a new {data_type_name} record and save it to the database.\n\nProceed?",
            True,
        ):
            self.callback.display_info("Cancelled.")
            return
        record: DataRecord = self.dr_man.add_data_record(data_type_name)
        description: str = "Created by DataRecordManager Python example"
        try:
            record.set_field_value("Description", description)
        except Exception:
            pass
        if data_type_name == "Sample":
            try:
                record.set_field_value("SampleId", f"DRM-PY-{record.record_id}")
            except Exception:
                pass
        self.dr_man.commit_data_records([record])
        self.callback.display_info(
            f"Created and committed {data_type_name} record.\n\nRecordId: {record.record_id}"
        )

    def _run_create_rollback_demo(self) -> None:
        data_type_name: str | None = self._prompt_for_data_type()
        if data_type_name is None:
            return
        if not self.callback.yes_no_dialog(
            "Create and Update Records (Demo)",
            f"This will create pending {data_type_name} record models then roll back (no data saved). Proceed?",
            True,
        ):
            self.callback.display_info("Demo cancelled.")
            return
        try:
            lines: list[str] = ["=== Create and Rollback (RecordModel transaction) ===\n\n"]
            lines.append(
                "Uses inst_man pending models + rec_man.rollback() (no rows committed).\n\n"
            )
            one: PyRecordModel = self.inst_man.add_new_record(data_type_name)
            lines.append(f"Created 1 pending model, temp RecordId: {one.record_id}\n")
            two_batch: list[PyRecordModel] = self.inst_man.add_new_records(data_type_name, 2)
            lines.append(f"Created {len(two_batch)} more pending models via add_new_records.\n")
            self.rec_man.rollback()
            lines.append("\nRolled back all pending record-model changes (no new rows saved).")
            self.callback.display_info("".join(lines))
        except Exception:
            self.rec_man.rollback()
            raise

    def _run_relationships_demo(self) -> None:
        data_type_name: str | None = self._prompt_for_data_type()
        if data_type_name is None:
            return
        try:
            selected_models: list[PyRecordModel] = self.callback.input_selection_dialog(
                data_type_name,
                "Select records to navigate relationships from",
                multi_select=True,
            )
        except SapioUserCancelledException:
            return
        if not selected_models:
            self.callback.display_info("No records selected.")
            return
        directions: tuple[str, ...] = (
            "Parents (getParentsOfType)",
            "Children (getChildrenOfType)",
            "Ancestors (getAncestorsOfType)",
            "Descendants (getDescendantsOfType)",
        )
        try:
            dir_choice: str = self.callback.option_dialog(
                "Relationship direction",
                "Choose direction:",
                list(directions),
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return
        related_type: str | None = self._prompt_for_data_type()
        if related_type is None:
            return
        idx: int = directions.index(dir_choice)
        ids: list[int] = sorted({m.record_id for m in selected_models})
        total: int = 0
        if idx == 0:
            res = self.dr_man.get_parents_list(ids, data_type_name, related_type)
            for _k, lst in (res.result_map or {}).items():
                total += len(lst or [])
        elif idx == 1:
            res = self.dr_man.get_children_list(ids, related_type)
            for _k, lst in (res.result_map or {}).items():
                total += len(lst or [])
        elif idx == 2:
            res = self.dr_man.get_ancestors_list(ids, data_type_name, related_type)
            for _k, lst in (res.result_map or {}).items():
                total += len(lst or [])
        else:
            res = self.dr_man.get_descendants_list(ids, related_type)
            for _k, lst in (res.result_map or {}).items():
                total += len(lst or [])
        self.callback.display_info(
            f"=== Navigate Relationships ===\n\n"
            f"From {len(ids)} {data_type_name} record(s), related type: {related_type}\n\n"
            f"Total related records (first result page/map): {total}"
        )

    def _run_batch_operations_demo(self) -> None:
        data_type_name: str | None = self._prompt_for_data_type()
        if data_type_name is None:
            return
        page = self.dr_man.query_all_records_of_type(
            data_type_name, DataRecordPojoPageCriteria(page_size=500)
        )
        all_batch: list[DataRecord] = page.result_list
        if not all_batch:
            self.callback.display_info(f"No records of type '{data_type_name}' found.")
            return
        sample: list[DataRecord] = all_batch[:20]
        fields_maps: int = len(sample)
        record_ids: list[object] = [r.get_fields().get("RecordId", r.record_id) for r in sample]
        parent_type_name: str | None = self._prompt_for_data_type()
        with_parents: int | str = 0
        if parent_type_name is not None:
            try:
                id_list: list[int] = [r.record_id for r in sample]
                parents_res = self.dr_man.get_parents_list(
                    id_list, data_type_name, parent_type_name
                )
                for _k, pl in (parents_res.result_map or {}).items():
                    if pl:
                        with_parents += 1
            except Exception:
                with_parents = "error"
        self.callback.display_info(
            f"=== Batch Operations ===\n\nData Type: {data_type_name}\n"
            f"Records in batch: {len(sample)}\n"
            f"Field maps (from record.get_fields()): {fields_maps}\n"
            f"RecordId values gathered: {len(record_ids)}\n"
            + (
                f"Records with {parent_type_name} parents: {with_parents}\n"
                if parent_type_name
                else ""
            )
        )
