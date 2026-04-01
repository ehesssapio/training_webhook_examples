"""
Created: 2026-03-19 15:20
Agent type: Composer
Modified: 2026-03-19 22:30
Agent type: Composer

Python counterpart to Java PluginDirectiveExample.java
(`sapio://examples/java/features/plugin-directive`).

Demonstrates WebhookDirective types exposed in sapiopylib (form, table, adaptive, home, custom report, ELN).
"""

from __future__ import annotations

import traceback

from sapiopycommons.customreport.custom_report_builder import CustomReportBuilder
from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.CustomReportService import CustomReportManager
from sapiopylib.rest.pojo.DataRecordPaging import DataRecordPojoPageCriteria
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookDirective import HomePageDirective
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult


class PluginDirectiveFeatureExample(CommonsWebhookHandler):
    OPT_FORM: str = "FormDirective (first Sample)"
    OPT_TABLE: str = "TableDirective (first 5 Samples)"
    OPT_ADAPTIVE: str = "record_adaptive (DirectiveUtil)"
    OPT_HOME: str = "HomePageDirective"
    OPT_REPORT: str = "CustomReportDirective (ad-hoc Sample)"
    OPT_ELN_EXP: str = "ElnExperimentDirective (needs experiment context / id)"
    OPT_ELN_ENTRY: str = "ExperimentEntryDirective (needs experiment + entry ids)"

    MENU_OPTIONS: tuple[str, ...] = (
        OPT_FORM,
        OPT_TABLE,
        OPT_ADAPTIVE,
        OPT_HOME,
        OPT_REPORT,
        OPT_ELN_EXP,
        OPT_ELN_ENTRY,
    )

    def _sample_page(self, page_size: int) -> list:
        page = self.dr_man.query_all_records_of_type(
            "Sample", DataRecordPojoPageCriteria(page_size=page_size)
        )
        return page.result_list or []

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.can_send_client_callback():
            return SapioWebhookResult(False, display_text="Requires client callback.")
        try:
            choice: str = self.callback.option_dialog(
                "Plugin Directive Examples",
                "Select directive demo:",
                list(self.MENU_OPTIONS),
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        try:
            if choice == self.OPT_HOME:
                return SapioWebhookResult(True, directive=HomePageDirective())
            if choice == self.OPT_FORM:
                recs = self._sample_page(1)
                if not recs:
                    self.callback.display_warning("No Sample records.")
                    return SapioWebhookResult(True)
                return SapioWebhookResult(True, directive=self.directive.record_form(recs[0]))
            if choice == self.OPT_TABLE:
                recs = self._sample_page(5)
                if not recs:
                    self.callback.display_warning("No Sample records.")
                    return SapioWebhookResult(True)
                return SapioWebhookResult(True, directive=self.directive.record_table(recs))
            if choice == self.OPT_ADAPTIVE:
                recs = self._sample_page(2)
                if not recs:
                    self.callback.display_warning("No Sample records.")
                    return SapioWebhookResult(True)
                return SapioWebhookResult(True, directive=self.directive.record_adaptive(recs))
            if choice == self.OPT_REPORT:
                rb = CustomReportBuilder("Sample")
                tb = rb.get_term_builder()
                rb.set_root_term(tb.gt_term("RecordId", 0))
                rb.add_column("RecordId")
                crit = rb.build_report_criteria()
                rep = CustomReportManager(self.user).run_custom_report(crit)
                return SapioWebhookResult(True, directive=self.directive.custom_report(rep))
            if choice == self.OPT_ELN_EXP:
                if context.eln_experiment is None:
                    self.callback.display_warning("No eln_experiment on context.")
                    return SapioWebhookResult(True)
                exp_id: int = context.eln_experiment.notebook_experiment_id
                return SapioWebhookResult(True, directive=self.directive.eln_experiment(exp_id))
            if choice == self.OPT_ELN_ENTRY:
                if context.eln_experiment is None or context.experiment_entry is None:
                    self.callback.display_warning("Need eln_experiment and experiment_entry on context.")
                    return SapioWebhookResult(True)
                return SapioWebhookResult(
                    True,
                    directive=self.directive.eln_entry(
                        context.eln_experiment.notebook_experiment_id,
                        context.experiment_entry.entry_id,
                    ),
                )
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        except Exception as ex:
            self.callback.display_error(f"{ex!s}\n{traceback.format_exc()}")
            return SapioWebhookResult(False)
        return SapioWebhookResult(True)
