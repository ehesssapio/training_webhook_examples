"""
Created: 2026-03-19 15:20
Agent type: Composer
Modified: 2026-03-19 22:30
Agent type: Composer
Modified: 2026-03-20 12:00
Agent type: Composer

Python counterpart to Java AccessionManagerExample.java
(`sapio://examples/java/features/accession-manager`).

Uses AccessionManager.accession_for_field / accession_for_system (sapiopylib). Accession by configuration lists
AccessionConfig records from the system.
"""

from __future__ import annotations

import traceback

from sapiopycommons.callbacks.callback_util import BlankResultHandling
from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.AccessionService import (
    AccessionDataFieldCriteriaPojo,
    AccessionSystemCriteriaPojo,
)
from sapiopylib.rest.pojo.DataRecordPaging import DataRecordPojoPageCriteria
from sapiopylib.rest.pojo.datatype.FieldDefinition import VeloxIntegerFieldDefinition, VeloxStringFieldDefinition
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult


class AccessionManagerFeatureExample(CommonsWebhookHandler):
    OPT_BY_CONFIG: str = "Accession by Configuration"
    OPT_BY_DATA_TYPE: str = "Accession by Data Type (Programmatic)"
    OPT_GLOBAL: str = "Global Accessioning"
    OPT_REQUEST_ID: str = "Request ID Accessioning"
    OPT_BATCH: str = "Batch Accessioning Demo"

    MENU_OPTIONS: tuple[str, ...] = (
        OPT_BY_CONFIG,
        OPT_BY_DATA_TYPE,
        OPT_GLOBAL,
        OPT_REQUEST_ID,
        OPT_BATCH,
    )

    _ACCESSION_CONFIG_TYPE: str = "AccessionConfig"

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.can_send_client_callback():
            return SapioWebhookResult(False, display_text="Requires client callback.")
        try:
            choice: str = self.callback.option_dialog(
                "Accession Service Examples",
                "Select which demonstration mode to run:\n\n"
                "• Accession by Configuration — AccessionConfig records in the system\n"
                "• Accession by Data Type — programmatic field accession (unique field)\n"
                "• Global Accessioning — sequence key (Foundations)\n"
                "• Request ID Accessioning — global sequence demo (configure key for your site)\n"
                "• Batch Accessioning — multiple IDs in one call",
                list(self.MENU_OPTIONS),
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        try:
            results: str | None = None
            if choice == self.OPT_BY_CONFIG:
                results = self._run_accession_by_configuration()
            elif choice == self.OPT_BY_DATA_TYPE:
                results = self._run_accession_by_data_type()
            elif choice == self.OPT_GLOBAL:
                results = self._run_global_accessioning()
            elif choice == self.OPT_REQUEST_ID:
                results = self._run_request_id_accessioning()
            elif choice == self.OPT_BATCH:
                results = self._run_batch_accessioning()
            else:
                self.callback.display_error("Unknown option selected.")
                return SapioWebhookResult(False)
            if results is not None:
                self.callback.display_info("Accession Demo Complete\n\n" + results)
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        except Exception as ex:
            self.callback.display_error(
                f"Accession Example Error:\n{ex!s}\n\n{traceback.format_exc()}"
            )
            return SapioWebhookResult(False)
        return SapioWebhookResult(True)

    def _run_accession_by_configuration(self) -> str:
        if self._ACCESSION_CONFIG_TYPE not in self.dt_man.get_data_type_name_list():
            return (
                "AccessionConfig data type is not configured in this system.\n"
                "Create AccessionConfig records in Configuration Manager first."
            )
        page = self.dr_man.query_all_records_of_type(
            self._ACCESSION_CONFIG_TYPE, DataRecordPojoPageCriteria(page_size=200)
        )
        configs = page.result_list or []
        if not configs:
            return (
                "No AccessionConfig records found.\n"
                "Create AccessionConfig records in Configuration Manager to define accessioning rules."
            )
        lines: list[str] = [
            "=== Accession by Configuration Demo ===\n\n",
            f"Found {len(configs)} AccessionConfig record(s) (first page).\n\n",
            "Configured rules (field keys from first records):\n",
            "---------------------------\n",
        ]
        for i, rec in enumerate(configs[:15]):
            keys: str = ", ".join(sorted(rec.get_fields().keys())[:12])
            lines.append(f"  {i + 1}. RecordId={rec.record_id} fields: {keys}\n")
        if len(configs) > 15:
            lines.append(f"  ... and {len(configs) - 15} more on this page\n")
        return "".join(lines)

    def _run_accession_by_data_type(self) -> str:
        dt_raw: object = self.callback.input_dialog(
            "Accession by data type",
            "Data type name (must have a Unique field):",
            VeloxStringFieldDefinition("AccDemo", "DataType", "Data type", max_length=200, editable=True),
            blank_result_handling=BlankResultHandling.REPEAT,
        )
        dt_name: str = str(dt_raw).strip() if dt_raw is not None else ""
        field_raw: object = self.callback.input_dialog(
            "Accession by data type",
            "Data field name to accession:",
            VeloxStringFieldDefinition("AccDemo", "Field", "Field name", max_length=200, editable=True),
            blank_result_handling=BlankResultHandling.REPEAT,
        )
        field_name: str = str(field_raw).strip() if field_raw is not None else ""
        key_raw: object = self.callback.input_dialog(
            "Accession by data type",
            "Sequence key (unique per format):",
            VeloxStringFieldDefinition("AccDemo", "SeqKey", "Sequence key", max_length=200, editable=True),
            blank_result_handling=BlankResultHandling.REPEAT,
        )
        seq_key: str = str(key_raw).strip() if key_raw is not None else ""
        n_raw: object = self.callback.input_dialog(
            "Accession by data type",
            "How many IDs:",
            VeloxIntegerFieldDefinition("AccDemo", "NumIds", "Count", editable=True),
            blank_result_handling=BlankResultHandling.REPEAT,
        )
        n: int = int(n_raw) if n_raw is not None else 1
        crit = AccessionDataFieldCriteriaPojo(dt_name, field_name, seq_key)
        ids: list[str] = self.acc_man.accession_for_field(n, crit)
        return (
            "=== Accession by Data Type ===\n\n"
            f"Data type: {dt_name}\nField: {field_name}\nSequence key: {seq_key}\n\n"
            "Generated IDs:\n" + "\n".join(f" • {x}" for x in ids)
        )

    def _run_global_accessioning(self) -> str:
        key_raw: object = self.callback.input_dialog(
            "Global accessioning",
            "Sequence key (Foundations accession config):",
            VeloxStringFieldDefinition("AccDemo", "SeqKey", "Sequence key", max_length=200, editable=True),
            blank_result_handling=BlankResultHandling.REPEAT,
        )
        key: str = str(key_raw).strip() if key_raw is not None else ""
        n_raw: object = self.callback.input_dialog(
            "Global accessioning",
            "How many IDs:",
            VeloxIntegerFieldDefinition("AccDemo", "NumIds", "Count", editable=True),
            blank_result_handling=BlankResultHandling.REPEAT,
        )
        n: int = int(n_raw) if n_raw is not None else 1
        crit = AccessionSystemCriteriaPojo(sequence_key=key)
        ids: list[str] = self.acc_man.accession_for_system(n, crit)
        return "=== Global Accessioning ===\n\n" + "\n".join(f" • {x}" for x in ids)

    def _run_request_id_accessioning(self) -> str:
        key_raw: object = self.callback.input_dialog(
            "Request ID accessioning",
            "Sequence key for request-style IDs:",
            VeloxStringFieldDefinition("AccDemo", "ReqKey", "Sequence key", max_length=200, editable=True),
            blank_result_handling=BlankResultHandling.REPEAT,
        )
        key: str = str(key_raw).strip() if key_raw is not None else ""
        crit = AccessionSystemCriteriaPojo(sequence_key=key)
        ids: list[str] = self.acc_man.accession_for_system(1, crit)
        return "=== Request ID Accessioning (via accession_for_system) ===\n\n" f" • {ids[0] if ids else '(none)'}"

    def _run_batch_accessioning(self) -> str:
        key_raw: object = self.callback.input_dialog(
            "Batch accessioning",
            "Sequence key:",
            VeloxStringFieldDefinition("AccDemo", "SeqKey", "Sequence key", max_length=200, editable=True),
            blank_result_handling=BlankResultHandling.REPEAT,
        )
        key: str = str(key_raw).strip() if key_raw is not None else ""
        n_raw: object = self.callback.input_dialog(
            "Batch accessioning",
            "How many IDs (batch):",
            VeloxIntegerFieldDefinition("AccDemo", "NumIds", "Count", editable=True),
            blank_result_handling=BlankResultHandling.REPEAT,
        )
        n: int = int(n_raw) if n_raw is not None else 5
        n = max(1, min(n, 100))
        crit = AccessionSystemCriteriaPojo(sequence_key=key)
        ids: list[str] = self.acc_man.accession_for_system(n, crit)
        return (
            f"=== Batch Accessioning Demo ({n} IDs) ===\n\n" + "\n".join(f" • {x}" for x in ids)
        )
