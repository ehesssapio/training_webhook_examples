"""
Created: 2026-03-19 15:20
Agent type: Composer
Modified: 2026-03-19 16:50
Agent type: Composer

Python counterpart to Java ExemplarContextExample.java
(`sapio://examples/java/features/exemplar-context`).

Shows SapioWebhookContext and CommonsWebhookHandler manager fields used from webhooks.
"""

from __future__ import annotations

from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.DataMgmtService import DataMgmtServer
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult


class ExemplarContextFeatureExample(CommonsWebhookHandler):
    OPT_BUILTIN: str = "Accessing Built-In Managers"
    OPT_VARS: str = "Context Variables"
    OPT_FACETS: str = "Accessing Context Facets"
    OPT_ALL_MANAGERS: str = "Retrieving All Managers"
    OPT_ALL_CTX_VARS: str = "Retrieving All Context Variables"

    MENU_OPTIONS: tuple[str, ...] = (
        OPT_BUILTIN,
        OPT_VARS,
        OPT_FACETS,
        OPT_ALL_MANAGERS,
        OPT_ALL_CTX_VARS,
    )

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.can_send_client_callback():
            return SapioWebhookResult(False, display_text="Requires client callback.")
        try:
            choice: str = self.callback.option_dialog(
                "Webhook context examples",
                "Select a demonstration:",
                list(self.MENU_OPTIONS),
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        if choice == self.OPT_BUILTIN:
            self._demo_accessing_built_in_managers(context)
        elif choice == self.OPT_VARS:
            self._demo_context_variables(context)
        elif choice == self.OPT_FACETS:
            self._demo_accessing_context_facets(context)
        elif choice == self.OPT_ALL_MANAGERS:
            self._demo_retrieving_all_managers()
        elif choice == self.OPT_ALL_CTX_VARS:
            self._demo_retrieving_all_context_variables(context)
        else:
            self.callback.display_error("Unknown option selected.")
            return SapioWebhookResult(False)
        return SapioWebhookResult(True)

    def _demo_accessing_built_in_managers(self, context: SapioWebhookContext) -> None:
        _ = self.dr_man
        _ = self.dt_man
        self.callback.display_info(
            "CommonsWebhookHandler: dr_man, dt_man, inst_man, rec_man, rel_man, …\n"
            "DataMgmtServer.get_* for additional managers.\n\n"
            f"end_point_type={context.end_point_type!r}, "
            f"data_type_name={context.data_type_name!r}, "
            f"eln_experiment={'set' if context.eln_experiment else 'none'}."
        )

    def _demo_context_variables(self, context: SapioWebhookContext) -> None:
        raw: str | None = context.context_data
        nbytes: int = len(raw) if raw else 0
        self.callback.display_info(
            f"SapioWebhookContext.context_data length: {nbytes} byte(s)."
        )

    def _demo_accessing_context_facets(self, context: SapioWebhookContext) -> None:
        self.callback.display_info(
            f"user set: {self.user is not None!r}, "
            f"dr_man set: {self.dr_man is not None!r}, "
            f"client_callback_available={self.can_send_client_callback()!r}"
        )

    def _demo_retrieving_all_managers(self) -> None:
        lines: list[str] = [
            "Obtain managers explicitly, e.g.:\n",
            " • DataMgmtServer.get_data_type_manager(user)\n",
            " • DataMgmtServer.get_picklist_manager(user)\n",
            " • context.data_record_manager (on webhook)\n",
            " • self.group_man / self.messenger on CommonsWebhookHandler\n",
        ]
        try:
            _ = DataMgmtServer.get_data_type_manager(self.user)
            lines.append("\nDataMgmtServer.get_data_type_manager(user): ok\n")
        except Exception as ex:
            lines.append(f"\nDataMgmtServer.get_data_type_manager(user): {ex!s}\n")
        self.callback.display_info("".join(lines))

    def _demo_retrieving_all_context_variables(self, context: SapioWebhookContext) -> None:
        self.callback.display_info(
            f"context_data preview: {(context.context_data or '')[:500]!r}"
        )
