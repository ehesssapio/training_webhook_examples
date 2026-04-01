"""
Created: 2025-03-10 00:00
Agent type: Composer
Modified: 2026-03-19 15:30
Agent type: Composer
Modified: 2026-03-19 17:05
Agent type: Composer

Python counterpart to Java ComplexDataLoaderConfigurationExample.java (`sapio://examples/java/features/data-loader-config`).

Main toolbar flow: list CDL configurations (paged `query_all_records_of_type`), upload file, `CDL.load_cdl`,
optional `TableDirective` of created rows.

`SimpleCDLExample` subclasses the full wizard without the results table.
"""

from __future__ import annotations

from sapiopycommons.files.complex_data_loader import CDL
from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.DataRecordPaging import DataRecordPojoPageCriteria
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookDirective import TableDirective
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult


class ComplexDataLoaderExample(CommonsWebhookHandler):
    """Main toolbar-style CDL demo with configuration picker + file upload + summary table."""

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        config_name: str | None = self._prompt_for_cdl_configuration()
        if config_name is None:
            return SapioWebhookResult(True, display_text="No CDL configuration selected.")

        file_name: str
        file_bytes: bytes
        try:
            file_name, file_bytes = self._prompt_for_file()
        except SapioUserCancelledException:
            return SapioWebhookResult(True)

        record_ids: list[int] = CDL.load_cdl(context, config_name, file_name, file_bytes)

        if record_ids:
            created_records = self.dr_man.query_data_records_by_id(config_name, record_ids).result_list
            self.callback.display_info(
                f"CDL Load Complete: created {len(record_ids)} record(s) using {config_name!r}."
            )
            return SapioWebhookResult(
                True,
                f"Created {len(record_ids)} records.",
                directive=TableDirective(created_records),
            )
        self.callback.display_warning("CDL Load Complete: no records created.")
        return SapioWebhookResult(True, "No records created.")

    def _prompt_for_cdl_configuration(self) -> str | None:
        out: list = []
        criteria: DataRecordPojoPageCriteria | None = DataRecordPojoPageCriteria(page_size=200)
        pages: int = 0
        while pages < 100:
            pages += 1
            page = self.dr_man.query_all_records_of_type("CDLConfig", criteria)
            out.extend(page.result_list or [])
            if not page.is_next_page_available or page.next_page_criteria is None:
                break
            criteria = page.next_page_criteria

        if not out:
            self.callback.display_warning(
                "No CDL configurations found. Create a CDL configuration in the system first."
            )
            return None

        config_names: set[str] = set()
        for record in out:
            cn = record.get_field_value("ConfigurationName")
            if cn:
                config_names.add(str(cn).strip())
        if not config_names:
            self.callback.display_warning("CDLConfig records exist but none have ConfigurationName set.")
            return None

        sorted_config_names: list[str] = sorted(config_names)
        try:
            selected_config: list[str] = self.callback.list_dialog(
                title=(
                    f"Select a CDL configuration.\n\nFound {len(sorted_config_names)} name(s) "
                    f"from {len(out)} CDLConfig record(s)."
                ),
                options=sorted_config_names,
                multi_select=False,
                shortcut_single_option=False,
            )
        except SapioUserCancelledException:
            return None
        if not selected_config:
            return None
        return selected_config[0]

    def _prompt_for_file(self) -> tuple[str, bytes]:
        return self.callback.request_file(
            title="Select a file to load",
            exts=["csv", "xlsx", "xls", "txt", "tsv"],
        )


class SimpleCDLExample(ComplexDataLoaderExample):
    """Minimal CDL load without TableDirective (inherits configuration + file prompts)."""

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        config_name: str | None = self._prompt_for_cdl_configuration()
        if config_name is None:
            return SapioWebhookResult(True, display_text="No CDL configuration selected.")
        file_name: str
        file_bytes: bytes
        try:
            file_name, file_bytes = self._prompt_for_file()
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        record_ids: list[int] = CDL.load_cdl(context, config_name, file_name, file_bytes)
        return SapioWebhookResult(True, f"Created {len(record_ids)} new records in the system.")
