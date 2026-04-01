"""
Created: 2026-03-19 15:05
Agent type: Composer
Modified: 2026-03-19 17:05
Agent type: Composer

`WebhookEndpointType.SELECTIONDATAFIELD`: returns `list_values` from a CustomReport on Sample (Study.StudyId).

Optional: pass tag text via `context_data` for custom gating. Field tag constant below should match Data Designer.
"""

from __future__ import annotations

from sapiopycommons.customreport.auto_pagers import CustomReportDictAutoPager
from sapiopycommons.customreport.custom_report_builder import CustomReportBuilder
from sapiopycommons.customreport.term_builder import TermBuilder
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult


class SelectionListWebhookExample(CommonsWebhookHandler):
    STUDIES_WITH_SAMPLES_SELECTION_LIST_TAG: str = "STUDIES WITH SAMPLES SELECTION LIST"
    STUDY_DATA_TYPE_NAME: str = "Study"
    SAMPLE_DATA_TYPE_NAME: str = "Sample"
    STUDY_ID_FIELD_NAME: str = "StudyId"

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        dtnames: list[str] = self.dt_man.get_data_type_name_list()
        if self.STUDY_DATA_TYPE_NAME not in dtnames or self.SAMPLE_DATA_TYPE_NAME not in dtnames:
            return SapioWebhookResult(True, list_values=[])

        study_id_field_type = None
        for fdef in self.dt_man.get_field_definition_list(self.SAMPLE_DATA_TYPE_NAME) or []:
            if str(getattr(fdef, "data_field_name", "")) == self.STUDY_ID_FIELD_NAME:
                study_id_field_type = getattr(fdef, "data_field_type", None) or getattr(
                    fdef, "field_type", None
                )
                break
        if study_id_field_type is None:
            return SapioWebhookResult(True, list_values=[])

        rb: CustomReportBuilder = CustomReportBuilder(self.SAMPLE_DATA_TYPE_NAME)
        tb: TermBuilder = rb.get_term_builder()
        rb.set_root_term(tb.gt_term("RecordId", 0))
        rb.add_column("RecordId")
        rb.add_column(self.STUDY_ID_FIELD_NAME, field_type=study_id_field_type)
        rows: list[dict] = CustomReportDictAutoPager(self.user, rb.build_report_criteria()).get_all_at_once()

        study_ids: set[str] = set()
        study_key: str = f"{self.STUDY_DATA_TYPE_NAME}.{self.STUDY_ID_FIELD_NAME}"
        for row in rows:
            raw: object | None = row.get(self.STUDY_ID_FIELD_NAME)
            if raw is None and study_key in row:
                raw = row.get(study_key)
            if raw is not None:
                s: str = str(raw).strip()
                if s:
                    study_ids.add(s)
        ordered: list[str] = sorted(study_ids)
        return SapioWebhookResult(True, list_values=ordered)
