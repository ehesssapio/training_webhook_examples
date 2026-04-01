"""
Created: 2026-03-19 15:20
Agent type: Composer
Modified: 2026-03-19 22:30
Agent type: Composer

Python counterpart to Java RecordModelRelationshipManagerExample.java
(`sapio://examples/java/features/record-model-relationship-manager`).

Relationship loading via RecordModelRelationshipManager: direct parents/children, multi-type loop, paths, and add-child.
"""

from __future__ import annotations

import time
import traceback

from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.DataRecordPaging import DataRecordPojoPageCriteria
from sapiopylib.rest.utils.recordmodel.PyRecordModel import PyRecordModel
from sapiopylib.rest.utils.recordmodel.properties import Child, Children, Parents
from sapiopylib.rest.utils.recordmodel.RelationshipPath import RelationshipPath
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult


class RecordModelRelationshipManagerFeatureExample(CommonsWebhookHandler):
    OPT_LOAD_CHILDREN: str = "Load Direct Children"
    OPT_LOAD_PARENTS: str = "Load Direct Parents"
    OPT_LOAD_ALL: str = "Load All Children/Parents"
    OPT_LOAD_PATH: str = "Load Path (Multi-Level Traversal)"
    OPT_LOAD_AND_GET: str = "Load and Get (Combined Operation)"
    OPT_ADD_CHILD: str = "Add a child Sample to first record"

    MENU_OPTIONS: tuple[str, ...] = (
        OPT_LOAD_CHILDREN,
        OPT_LOAD_PARENTS,
        OPT_LOAD_ALL,
        OPT_LOAD_PATH,
        OPT_LOAD_AND_GET,
        OPT_ADD_CHILD,
    )

    @staticmethod
    def _to_display(value: object | None) -> str:
        return "" if value is None else str(value)

    def _samples(self, n: int = 5) -> list[PyRecordModel]:
        page = self.dr_man.query_all_records_of_type(
            "Sample", DataRecordPojoPageCriteria(page_size=max(n, 10))
        )
        recs = page.result_list or []
        if not recs:
            return []
        return self.inst_man.add_existing_records(recs[:n])

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.can_send_client_callback():
            return SapioWebhookResult(False, display_text="Requires client callback.")
        try:
            choice: str = self.callback.option_dialog(
                "RecordModelRelationshipManager Demo",
                "Select a demonstration:",
                list(self.MENU_OPTIONS),
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        try:
            if choice == self.OPT_LOAD_CHILDREN:
                self._demo_load_children()
            elif choice == self.OPT_LOAD_PARENTS:
                self._demo_load_parents()
            elif choice == self.OPT_LOAD_ALL:
                self._demo_load_all()
            elif choice == self.OPT_LOAD_PATH:
                self._demo_load_path()
            elif choice == self.OPT_LOAD_AND_GET:
                self._demo_load_and_get()
            elif choice == self.OPT_ADD_CHILD:
                self._demo_add_child()
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        except Exception as ex:
            self.callback.display_error(f"Error:\n{ex!s}\n\n{traceback.format_exc()}")
            return SapioWebhookResult(False)
        return SapioWebhookResult(True)

    def _demo_load_children(self) -> None:
        samples = self._samples(5)
        if not samples:
            self.callback.display_warning("No Sample records found.")
            return
        self.rel_man.load_children(samples, "Sample")
        lines: list[str] = ["loadChildren Demo — child type 'Sample'\n\n", "─" * 50 + "\n\n"]
        for s in samples:
            sid = self._to_display(s.get_field_value("SampleId"))
            ch: list[PyRecordModel] = s.get(Children.of_type_name("Sample"))
            lines.append(f"Sample: {sid}\n")
            lines.append(f"  └─ child Samples loaded: {len(ch)}\n")
            for c in ch[:3]:
                lines.append(f"      • {self._to_display(c.get_field_value('SampleId'))}\n")
            lines.append("\n")
        self.callback.display_info("Load Direct Children\n\n" + "".join(lines))

    def _demo_load_parents(self) -> None:
        samples = self._samples(5)
        if not samples:
            self.callback.display_warning("No Sample records found.")
            return
        self.rel_man.load_parents(samples, "Request")
        lines: list[str] = ["loadParents Demo — parent type 'Request'\n\n", "─" * 50 + "\n\n"]
        for s in samples:
            sid = self._to_display(s.get_field_value("SampleId"))
            par: list[PyRecordModel] = s.get(Parents.of_type_name("Request"))
            lines.append(f"Sample: {sid}\n")
            if not par:
                lines.append("  └─ (no Request parent)\n\n")
            else:
                for p in par:
                    lines.append(f"  └─ Request: {self._to_display(p.get_field_value('RequestId'))}\n")
                lines.append("\n")
        self.callback.display_info("Load Direct Parents\n\n" + "".join(lines))

    def _demo_load_all(self) -> None:
        samples = self._samples(3)
        if not samples:
            self.callback.display_warning("No Sample records found.")
            return
        parent_types: tuple[str, ...] = ("Request", "Sample", "Study")
        child_types: tuple[str, ...] = ("Sample", "Attachment")
        for pt in parent_types:
            self.rel_man.load_parents(samples, pt)
        for ct in child_types:
            self.rel_man.load_children(samples, ct)
        lines: list[str] = [
            "Load parents/children for several types in a loop\n\n",
            "─" * 55 + "\n\n",
        ]
        for s in samples:
            sid = self._to_display(s.get_field_value("SampleId"))
            lines.append(f"Sample: {sid}\n  Parents:\n")
            for pt in parent_types:
                par = s.get(Parents.of_type_name(pt))
                if par:
                    lines.append(f"    • {pt}: {len(par)}\n")
            lines.append("  Children:\n")
            for ct in child_types:
                ch = s.get(Children.of_type_name(ct))
                if ch:
                    lines.append(f"    • {ct}: {len(ch)}\n")
            lines.append("\n")
        self.callback.display_info("Load All\n\n" + "".join(lines))

    def _demo_load_path(self) -> None:
        samples = self._samples(3)
        if not samples:
            self.callback.display_warning("No Sample records found.")
            return
        path = RelationshipPath().parent("Request")
        self.rel_man.load_path(samples, path)
        lines: list[str] = ["loadPath Demo — path: parent(Request)\n\n"]
        for s in samples:
            par = s.get_parents_of_type("Request")
            lines.append(
                f"Sample {self._to_display(s.get_field_value('SampleId'))}: "
                f"{len(par)} Request parent(s)\n"
            )
        self.callback.display_info("Load Path\n\n" + "".join(lines))

    def _demo_load_and_get(self) -> None:
        samples = self._samples(5)
        if not samples:
            self.callback.display_warning("No Sample records found.")
            return
        path = RelationshipPath().parent("Request")
        self.rel_man.load_path(samples, path)
        lines: list[str] = ["After load_path + Parents.of_type_name(Request):\n\n"]
        for s in samples:
            sid = self._to_display(s.get_field_value("SampleId"))
            reqs = s.get(Parents.of_type_name("Request"))
            lines.append(f"Sample: {sid}\n")
            if not reqs:
                lines.append("  └─ (no Request parent)\n\n")
            else:
                for r in reqs:
                    lines.append(f"  └─ Request: {self._to_display(r.get_field_value('RequestId'))}\n")
                lines.append("\n")
        self.callback.display_info("Load and Get\n\n" + "".join(lines))

    def _demo_add_child(self) -> None:
        samples = self._samples(1)
        if not samples:
            self.callback.display_warning("No Sample records found.")
            return
        parent: PyRecordModel = samples[0]
        pid = self._to_display(parent.get_field_value("SampleId")) or str(parent.record_id)
        try:
            confirm: str = self.callback.option_dialog(
                "Add child Sample",
                f"Create a new child Sample under {pid} and commit?",
                ["Proceed", "Cancel"],
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return
        if confirm != "Proceed":
            return
        child: PyRecordModel = parent.add(Child.create_by_name("Sample"))
        child.set_field_value("SampleId", f"REL-CHILD-{int(time.time() * 1000)}")
        child.set_field_value("OtherSampleId", "RecordModelRelationship demo child")
        child.set_field_value("ExemplarSampleType", "Test")
        self.rec_man.store_and_commit()
        self.callback.display_info(
            f"Added child Sample; new RecordId={child.record_id}\n"
            f"SampleId={self._to_display(child.get_field_value('SampleId'))}"
        )
