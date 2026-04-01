"""
Created: 2026-03-19 15:20
Agent type: Composer
Modified: 2026-03-19 22:30
Agent type: Composer
Modified: 2026-03-20 12:00
Agent type: Composer

Python counterpart to Java NotebookExperimentManagerExample.java
(`sapio://examples/java/features/notebook-experiment-manager`).

Same four menu options. Uses eln_man + query for NotebookExperiment records (data type name typically NotebookExperiment).
"""

from __future__ import annotations

import traceback

from sapiopycommons.callbacks.callback_util import BlankResultHandling
from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.DataRecordPaging import DataRecordPojoPageCriteria
from sapiopylib.rest.pojo.eln.ElnExperiment import TemplateExperimentQueryPojo
from sapiopylib.rest.pojo.eln.protocol_template import ProtocolTemplateQuery
from sapiopylib.rest.pojo.datatype.FieldDefinition import VeloxStringFieldDefinition
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult


class NotebookExperimentManagerFeatureExample(CommonsWebhookHandler):
    ELN_EXPERIMENT_TYPE: str = "NotebookExperiment"

    OPT_LIST: str = "List All Experiments"
    OPT_GET: str = "Get Experiment by Name"
    OPT_INFO: str = "Show Experiment Information"
    OPT_API: str = "NotebookExperimentManager API Overview"

    MENU_OPTIONS: tuple[str, ...] = (OPT_LIST, OPT_GET, OPT_INFO, OPT_API)

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.can_send_client_callback():
            return SapioWebhookResult(False, display_text="Requires client callback.")
        try:
            choice: str = self.callback.option_dialog(
                "NotebookExperimentManager Examples",
                "Select which demonstration to run:",
                list(self.MENU_OPTIONS),
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        try:
            if choice == self.OPT_LIST:
                self._run_list_experiments()
            elif choice == self.OPT_GET:
                self._run_get_experiment()
            elif choice == self.OPT_INFO:
                self._run_experiment_info()
            elif choice == self.OPT_API:
                self._run_manager_api_overview()
            else:
                self.callback.display_error("Error\n\nUnknown option selected.")
                return SapioWebhookResult(False)
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        except Exception as ex:
            self.callback.display_error(
                f"NotebookExperimentManager Example Error:\n{ex!s}\n\n{traceback.format_exc()}"
            )
            return SapioWebhookResult(False)
        return SapioWebhookResult(True)

    def _collect_notebook_records(self, max_pages: int = 20) -> list:
        out: list = []
        criteria: DataRecordPojoPageCriteria | None = DataRecordPojoPageCriteria(page_size=100)
        for _ in range(max_pages):
            page = self.dr_man.query_all_records_of_type(self.ELN_EXPERIMENT_TYPE, criteria)
            out.extend(page.result_list or [])
            if not page.is_next_page_available or page.next_page_criteria is None:
                break
            criteria = page.next_page_criteria
        return out

    def _run_list_experiments(self) -> None:
        records = self._collect_notebook_records()
        if not records:
            self.callback.display_info("List Experiments\n\nNo experiment records found (paged query).")
            return
        lines: list[str] = [
            "=== ALL NOTEBOOK EXPERIMENTS ===\n\n",
            f"Total experiment records (paged): {len(records)}\n\n",
        ]
        max_show: int = min(100, len(records))
        for i in range(max_show):
            rec = records[i]
            exp = self.eln_man.get_eln_experiment_by_record_id(rec.record_id)
            if exp is not None:
                lines.append(
                    f"• {exp.notebook_experiment_name!r}  [id={exp.notebook_experiment_id}]  "
                    f"status={exp.notebook_experiment_status!r}\n"
                )
            else:
                lines.append(f"• (Could not load ElnExperiment for record {rec.record_id})\n")
        if len(records) > max_show:
            lines.append(f"\n... and {len(records) - max_show} more.\n")
        self.callback.display_info("List Experiments\n\n" + "".join(lines))

    def _run_get_experiment(self) -> None:
        raw: object = self.callback.input_dialog(
            "Get experiment",
            "Experiment name (exact match on loaded page):",
            VeloxStringFieldDefinition("NbDemo", "Name", "Name", max_length=500, editable=True),
            blank_result_handling=BlankResultHandling.CANCEL,
        )
        name_match: str = str(raw).strip() if raw is not None else ""
        if not name_match:
            return
        records = self._collect_notebook_records(5)
        found = None
        for rec in records:
            exp = self.eln_man.get_eln_experiment_by_record_id(rec.record_id)
            if exp is not None and exp.notebook_experiment_name == name_match:
                found = exp
                break
        if found is None:
            self.callback.display_info(f"No experiment named {name_match!r} in first pages of records.")
            return
        entries = self.eln_man.get_experiment_entry_list(found.notebook_experiment_id)
        lines: list[str] = [
            f"=== GET EXPERIMENT: {found.notebook_experiment_name!r} ===\n\n",
            f"notebook_experiment_id={found.notebook_experiment_id}\n",
            f"status={found.notebook_experiment_status!r}\n\n",
            f"Entries: {len(entries)}\n",
        ]
        for ent in entries[:30]:
            nrec: int = 0
            try:
                recs = self.eln_man.get_data_records_for_entry(
                    found.notebook_experiment_id, ent.entry_id
                )
                nrec = len(recs or [])
            except Exception:
                nrec = -1
            lines.append(
                f" • {ent.entry_name!r}  order={ent.order}  status={ent.entry_status!r}  records={nrec}\n"
            )
        self.callback.display_info("Get Experiment\n\n" + "".join(lines))

    def _run_experiment_info(self) -> None:
        records = self._collect_notebook_records(3)
        experiments: list = []
        for rec in records:
            exp = self.eln_man.get_eln_experiment_by_record_id(rec.record_id)
            if exp is not None:
                experiments.append(exp)
        if not experiments:
            self.callback.display_info("No experiments could be loaded.")
            return
        labels: list[str] = []
        for e in experiments[:200]:
            labels.append(e.notebook_experiment_name or f"(ID: {e.notebook_experiment_id})")
        try:
            picked: list[str] = self.callback.list_dialog(
                "Show Experiment Information",
                labels,
                multi_select=False,
                shortcut_single_option=False,
            )
        except SapioUserCancelledException:
            return
        if not picked:
            return
        idx: int = labels.index(picked[0])
        exp = experiments[idx]
        entries = self.eln_man.get_experiment_entry_list(exp.notebook_experiment_id)
        lines: list[str] = [
            "=== EXPERIMENT INFORMATION ===\n\n",
            f"name: {exp.notebook_experiment_name!r}\n",
            f"notebook_experiment_id: {exp.notebook_experiment_id}\n",
            f"status: {exp.notebook_experiment_status!r}\n\n",
            f"entry count: {len(entries)}\n\n",
        ]
        for ent in entries[:50]:
            nrec = 0
            try:
                recs = self.eln_man.get_data_records_for_entry(
                    exp.notebook_experiment_id, ent.entry_id
                )
                nrec = len(recs or [])
            except Exception:
                nrec = -1
            lines.append(
                f" • {ent.entry_name!r}  id={ent.entry_id}  type={ent.data_type_name!r}  "
                f"order={ent.order}  entryStatus={ent.entry_status!r}  records={nrec}\n"
            )
        self.callback.display_info("Experiment Information\n\n" + "".join(lines))

    def _run_manager_api_overview(self) -> None:
        lines: list[str] = [
            "=== NOTEBOOK EXPERIMENT MANAGER API (Python) ===\n\n",
            f"• Data type constant used here: {self.ELN_EXPERIMENT_TYPE!r}\n",
            "• ElnManager: get_eln_experiment_by_id / by_record_id / by_criteria\n",
            "• get_experiment_entry_list / get_data_records_for_entry\n",
            "• get_template_experiment_list / get_protocol_template_info_list\n\n",
        ]
        try:
            templates = self.eln_man.get_template_experiment_list(TemplateExperimentQueryPojo())
            lines.append(f"• get_template_experiment_list: {len(templates)} template(s)\n")
        except Exception as e:
            lines.append(f"• get_template_experiment_list: error — {e!s}\n")
        try:
            protos = self.eln_man.get_protocol_template_info_list(ProtocolTemplateQuery())
            lines.append(f"• get_protocol_template_info_list: {len(protos)} protocol template(s)\n")
        except Exception as e:
            lines.append(f"• get_protocol_template_info_list: error — {e!s}\n")
        self.callback.display_info("NotebookExperimentManager API\n\n" + "".join(lines))
