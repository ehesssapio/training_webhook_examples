"""
Created: 2026-03-19 15:20
Agent type: Composer
Modified: 2026-03-19 21:10
Agent type: Composer

Python counterpart to Java RecordModelManagerExample.java
(`sapio://examples/java/features/record-model-manager`).

Five demos using PyRecordModel and Child / Children / Parent / Parents from sapiopylib.
"""

from __future__ import annotations

import time
import traceback

from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.DataRecord import DataRecord
from sapiopylib.rest.pojo.DataRecordPaging import DataRecordPojoPageCriteria
from sapiopylib.rest.utils.recordmodel.PyRecordModel import PyRecordModel
from sapiopylib.rest.utils.recordmodel.properties import Child, Children, Parent, Parents
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult


class RecordModelManagerFeatureExample(CommonsWebhookHandler):
    OPT_QUERY: str = "Query Records as RecordModels"
    OPT_MANAGERS: str = "Show Sub-Managers"
    OPT_CREATE: str = "Create New Records"
    OPT_REL: str = "Add Relationships (Parent/Child)"
    OPT_API: str = "RecordModel API (fields, references, wrappers)"

    MENU_OPTIONS: tuple[str, ...] = (
        OPT_QUERY,
        OPT_MANAGERS,
        OPT_CREATE,
        OPT_REL,
        OPT_API,
    )

    @staticmethod
    def _to_display_string(value: object | None) -> str:
        return "" if value is None else str(value)

    def _load_sample_records(self, limit: int = 10) -> list[DataRecord]:
        page = self.dr_man.query_all_records_of_type(
            "Sample", DataRecordPojoPageCriteria(page_size=limit)
        )
        return page.result_list or []

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.can_send_client_callback():
            return SapioWebhookResult(False, display_text="Requires client callback.")
        try:
            choice: str = self.callback.option_dialog(
                "RecordModelManager Examples",
                "Select which demonstration to run:",
                list(self.MENU_OPTIONS),
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        try:
            if choice == self.OPT_QUERY:
                self._run_query_records_demo()
            elif choice == self.OPT_MANAGERS:
                self._run_show_managers_demo()
            elif choice == self.OPT_CREATE:
                self._run_create_records_demo()
            elif choice == self.OPT_REL:
                self._run_relationships_demo()
            elif choice == self.OPT_API:
                self._run_record_model_api_demo()
            else:
                self.callback.display_error("Error\n\nUnknown option selected.")
                return SapioWebhookResult(False)
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        except Exception as ex:
            self.callback.display_error(
                f"RecordModelManager Example Error:\n{ex!s}\n\n{traceback.format_exc()}"
            )
            return SapioWebhookResult(False)
        return SapioWebhookResult(True)

    def _run_query_records_demo(self) -> None:
        lines: list[str] = [
            "=== QUERY RECORDS AS RECORDMODELS ===\n\n",
            "✓ RecordModelManager obtained\n",
            "✓ RecordModelInstanceManager obtained\n\n",
        ]
        sample_records: list[DataRecord] = self._load_sample_records(50)
        lines.append(f"Sample DataRecords found (first page): {len(sample_records)}\n\n")
        if sample_records:
            limited: list[DataRecord] = sample_records[:10]
            models: list[PyRecordModel] = self.inst_man.add_existing_records(limited)
            lines.append(f"Converted {len(models)} to RecordModels:\n")
            for i in range(min(5, len(models))):
                m: PyRecordModel = models[i]
                sid: object = m.get_field_value("SampleId")
                lines.append(
                    f"  • RecordId: {m.record_id}, Type: {m.data_type_name}"
                    + (f", SampleId: {self._to_display_string(sid)}" if sid is not None else "")
                    + "\n"
                )
            if len(models) > 5:
                lines.append(f"  ... and {len(models) - 5} more\n")
        else:
            lines.append("No Sample records found in the system (first page).\n")
        self.callback.display_info("Query Records Demo\n\n" + "".join(lines))

    def _run_show_managers_demo(self) -> None:
        text: str = (
            "=== RECORDMODELMANAGER SUB-MANAGERS ===\n\n"
            "✓ RecordModelManager obtained\n\n"
            "Available Sub-Managers:\n\n"
            "• RecordModelInstanceManager\n"
            "  - Creates and tracks RecordModel instances\n"
            "  - add_new_record(), add_existing_records()\n\n"
            "• RecordModelTransactionManager\n"
            "  - Handles storing and rolling back changes\n"
            "  - rollback()\n\n"
            "• RecordModelRelationshipManager\n"
            "  - Manages parent-child relationships\n"
            "  - add_parent(), add_child(), get_children_of_type()\n\n"
            "Main Methods:\n"
            "• store_and_commit() - Persist changes to Sapio\n"
            "• Webhook handlers use SapioWebhookContext and self.user instead of a separate exemplar context\n"
        )
        self.callback.display_info("Sub-Managers Demo\n\n" + text)

    def _run_create_records_demo(self) -> None:
        if not self.callback.yes_no_dialog(
            "Create Test Records?",
            "This demo will create test Sample records in the system.\n\n"
            "Do you want to proceed?\n\n"
            "(Records will be created with test data that you can delete later)",
            True,
        ):
            self.callback.display_info("Cancelled\n\nRecord creation cancelled.")
            return
        lines: list[str] = ["=== CREATE NEW RECORDS ===\n\n", "✓ RecordModelManager obtained\n\n"]
        lines.append("1. Creating empty Sample record:\n")
        new1: PyRecordModel = self.inst_man.add_new_record("Sample")
        lines.append("   ✓ Created new RecordModel (pending save)\n")
        lines.append(f"   • DataType: {new1.data_type_name}\n")
        lines.append(f"   • IsNew: {new1.is_new}\n\n")
        test_id: str = f"TEST-{int(time.time() * 1000)}"
        new1.set_field_value("SampleId", test_id)
        new1.set_field_value("OtherSampleId", "RecordModel Demo Sample")
        new1.set_field_value("ExemplarSampleType", "Test")
        lines.append(f"   ✓ Set fields: SampleId={test_id}\n\n")

        lines.append("2. Creating Sample with follow-up field sets:\n")
        new2: PyRecordModel = self.inst_man.add_new_record("Sample")
        test_id2: str = f"TEST2-{int(time.time() * 1000)}"
        new2.set_field_value("SampleId", test_id2)
        new2.set_field_value("OtherSampleId", "RecordModel Demo Sample 2")
        new2.set_field_value("ExemplarSampleType", "Test")
        lines.append("   ✓ Created and set fields\n")
        lines.append(
            f"   • SampleId: {self._to_display_string(new2.get_field_value('SampleId'))}\n\n"
        )

        lines.append("3. Creating multiple records:\n")
        batch: list[PyRecordModel] = self.inst_man.add_new_records("Sample", 3)
        for i, bm in enumerate(batch, start=1):
            bm.set_field_value("SampleId", f"BATCH-{int(time.time() * 1000)}-{i}")
            bm.set_field_value("OtherSampleId", f"Batch Sample {i}")
            bm.set_field_value("ExemplarSampleType", "Test")
        lines.append(f"   ✓ Created {len(batch)} records in batch\n\n")

        lines.append("4. Storing changes to database:\n")
        self.rec_man.store_and_commit()
        lines.append("   ✓ All records saved!\n\n")
        lines.append("Saved Record IDs:\n")
        lines.append(f"  • Record 1: {new1.record_id}\n")
        lines.append(f"  • Record 2: {new2.record_id}\n")
        for i, bm in enumerate(batch):
            lines.append(f"  • Batch {i + 1}: {bm.record_id}\n")
        self.callback.display_info("Create Records Demo\n\n" + "".join(lines))

    def _run_relationships_demo(self) -> None:
        if not self.callback.yes_no_dialog(
            "Create Records with Relationships?",
            "This demo will create Request and Sample records with parent-child relationships.\n\n"
            "Do you want to proceed?",
            True,
        ):
            self.callback.display_info("Cancelled\n\nRelationship demo cancelled.")
            return
        if self.dt_man.get_data_type_definition("Request") is None:
            self.callback.display_warning(
                "Data Type Not Found\n\nThe 'Request' data type is required for this demo."
            )
            return
        lines: list[str] = ["=== ADD RELATIONSHIPS ===\n\n"]
        lines.append("✓ RecordModelManager obtained\n")
        lines.append("✓ RelationshipManager obtained\n\n")

        lines.append("1. Creating parent Request record:\n")
        request_rec: PyRecordModel = self.inst_man.add_new_record("Request")
        request_id: str = f"REQ-{int(time.time() * 1000)}"
        request_rec.set_field_value("RequestId", request_id)
        request_rec.set_field_value("RequestName", "Relationship Demo Request")
        lines.append(f"   ✓ Created Request: {request_id}\n\n")

        lines.append("2. Adding child Sample using add(Child.create_by_name()):\n")
        child1: PyRecordModel = request_rec.add(Child.create_by_name("Sample"))
        child1.set_field_value("SampleId", f"CHILD1-{int(time.time() * 1000)}")
        child1.set_field_value("OtherSampleId", "Child Sample via add()")
        child1.set_field_value("ExemplarSampleType", "Test")
        lines.append(
            f"   ✓ Added child Sample: {self._to_display_string(child1.get_field_value('SampleId'))}\n\n"
        )

        lines.append("3. Creating Samples and adding as children:\n")
        child2: PyRecordModel = self.inst_man.add_new_record("Sample")
        child2.set_field_value("SampleId", f"CHILD2-{int(time.time() * 1000)}")
        child2.set_field_value("OtherSampleId", "Child Sample via Children.refs()")
        child2.set_field_value("ExemplarSampleType", "Test")
        child3: PyRecordModel = self.inst_man.add_new_record("Sample")
        child3.set_field_value("SampleId", f"CHILD3-{int(time.time() * 1000)}")
        child3.set_field_value("OtherSampleId", "Child Sample 3")
        child3.set_field_value("ExemplarSampleType", "Test")
        request_rec.add(Children.refs([child2, child3]))
        lines.append("   ✓ Added 2 more children using Children.refs()\n\n")

        lines.append("4. Creating Sample that adds a parent Request:\n")
        sample_wp: PyRecordModel = self.inst_man.add_new_record("Sample")
        sample_wp.set_field_value("SampleId", f"WITHPARENT-{int(time.time() * 1000)}")
        sample_wp.set_field_value("OtherSampleId", "Sample that created its parent")
        sample_wp.set_field_value("ExemplarSampleType", "Test")
        new_parent: PyRecordModel = sample_wp.add(Parent.create_by_name("Request"))
        new_parent.set_field_value("RequestId", f"REQ2-{int(time.time() * 1000)}")
        new_parent.set_field_value("RequestName", "Parent created from child")
        lines.append("   ✓ Sample created with new parent Request\n\n")

        lines.append("5. Storing all relationships to database:\n")
        self.rec_man.store_and_commit()
        lines.append("   ✓ All records and relationships saved!\n\n")
        lines.append("Summary:\n")
        lines.append(
            f"  • Request 1 (ID: {request_rec.record_id}) has linked child Samples\n"
            f"  • Request 2 (ID: {new_parent.record_id}) has linked child Sample\n\n"
        )
        lines.append(
            "Key Methods Used:\n"
            "  • record.add(Child.create_by_name(\"DataType\"))\n"
            "  • record.add(Children.refs([...]))\n"
            "  • record.add(Parent.create_by_name(\"DataType\"))\n"
            "  • rec_man.store_and_commit()\n"
        )
        self.callback.display_info("Relationships Demo\n\n" + "".join(lines))

    def _run_record_model_api_demo(self) -> None:
        sample_records: list[DataRecord] = self._load_sample_records(25)
        if not sample_records:
            self.callback.display_warning(
                "No Sample records found.\n\nThis demo needs at least one Sample record."
            )
            return
        limited: list[DataRecord] = sample_records[:3]
        models: list[PyRecordModel] = self.inst_man.add_existing_records(limited)
        first: PyRecordModel = models[0]
        lines: list[str] = ["=== RECORDMODEL API (fields, references, wrappers) ===\n\n"]

        lines.append("1. Fields (individual) – get_field_value / set_field_value\n")
        lines.append(
            f"   • get_field_value(\"SampleId\"): {self._to_display_string(first.get_field_value('SampleId'))}\n"
        )
        lines.append(
            f"   • get_field_value(\"ExemplarSampleType\"): "
            f"{self._to_display_string(first.get_field_value('ExemplarSampleType'))}\n"
        )
        lines.append(
            f"   • get_field_value(\"OtherSampleId\") before: "
            f"{self._to_display_string(first.get_field_value('OtherSampleId'))}\n"
        )
        updated_other: str = f"RecordModel API demo {int(time.time() * 1000)}"
        first.set_field_value("OtherSampleId", updated_other)
        lines.append(
            f"   • set_field_value then get_field_value: "
            f"{self._to_display_string(first.get_field_value('OtherSampleId'))}\n\n"
        )

        lines.append("2. Fields (map) – fields[] / set_field_values\n")
        snapshot: dict[str, object] = first.fields.copy_to_dict()
        lines.append(f"   • fields snapshot size: {len(snapshot)}\n")
        shown: int = 0
        for k, v in snapshot.items():
            if shown >= 3:
                break
            lines.append(f"     - {k}: {self._to_display_string(v)}\n")
            shown += 1
        first.set_field_values(
            {"OtherSampleId": f"Updated via set_field_values {int(time.time() * 1000)}"}
        )
        lines.append(
            f"   • set_field_values then get_field_value(\"OtherSampleId\"): "
            f"{self._to_display_string(first.get_field_value('OtherSampleId'))}\n\n"
        )

        lines.append("3. References – adding (Child / Children.refs / Parent)\n")
        if self.dt_man.get_data_type_definition("Request") is not None:
            request_m: PyRecordModel = self.inst_man.add_new_record("Request")
            req_id: str = f"API-REQ-{int(time.time() * 1000)}"
            request_m.set_field_value("RequestId", req_id)
            request_m.set_field_value("RequestName", "RecordModel API demo")
            child: PyRecordModel = request_m.add(Child.create_by_name("Sample"))
            child.set_field_value("SampleId", f"API-CHILD-{int(time.time() * 1000)}")
            child.set_field_value("OtherSampleId", 'Added via record.add(Child.create_by_name("Sample"))')
            child.set_field_value("ExemplarSampleType", "Test")
            lines.append(
                f"   • Child.create_by_name SampleId: "
                f"{self._to_display_string(child.get_field_value('SampleId'))}\n"
            )
            ch_list: list[PyRecordModel] = first.get(Children.of_type_name("Sample"))
            lines.append(f"   • record.get(Children.of_type_name(\"Sample\")): {len(ch_list)} loaded\n")
            par_list: list[PyRecordModel] = first.get(Parents.of_type_name("Request"))
            lines.append(f"   • record.get(Parents.of_type_name(\"Request\")): {len(par_list)} loaded\n")
            self.rec_man.store_and_commit()
            lines.append("   ✓ store_and_commit() called (new Request + child saved)\n\n")
        else:
            lines.append("   (Request type not found; skipping add Child/Parent demo)\n\n")

        lines.append("4. References – removing\n")
        lines.append(
            "   Relationship removal is typically done in the UI; on save, use server APIs "
            "to detect removed parents where applicable.\n\n"
        )

        lines.append("5. Typed wrappers\n")
        lines.append(
            "   Use PyRecordModel with field names and properties; generate per-type wrappers from your data model if needed.\n"
        )
        self.callback.display_info("RecordModel API Demo\n\n" + "".join(lines))
