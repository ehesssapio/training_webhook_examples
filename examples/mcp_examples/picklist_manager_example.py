"""
Created: 2026-03-19 15:20
Agent type: Composer
Modified: 2026-03-19 20:05
Agent type: Composer
Modified: 2026-03-19 16:50
Agent type: Composer

Python counterpart to Java PicklistManagerExample.java
(`sapio://examples/java/features/picklist-manager`).

Same four demos: list all picklists, get values, create demo picklist, modify picklist.
Uses EXAMPLE_PICKLIST_NAME and list_man.get_picklist_config_list / get_picklist /
update_picklist_value_list (creates picklist if name does not exist).
"""

from __future__ import annotations

import time
import traceback

from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.Picklist import PickListConfig
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult


class PicklistManagerFeatureExample(CommonsWebhookHandler):
    EXAMPLE_PICKLIST_NAME: str = "PicklistManagerExample_Demo"

    OPT_LIST_ALL: str = "List all picklists"
    OPT_GET_VALUES: str = "Get values from a specific picklist"
    OPT_CREATE: str = "Create a new picklist"
    OPT_MODIFY: str = "Modify an existing picklist"
    MENU_OPTIONS: tuple[str, ...] = (
        OPT_LIST_ALL,
        OPT_GET_VALUES,
        OPT_CREATE,
        OPT_MODIFY,
    )

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.can_send_client_callback():
            return SapioWebhookResult(False, display_text="Requires client callback.")
        try:
            choice: str = self.callback.option_dialog(
                "PickListManager Examples",
                "Select which demonstration to run:",
                list(self.MENU_OPTIONS),
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        try:
            if choice == self.OPT_LIST_ALL:
                self._run_list_all_picklists()
            elif choice == self.OPT_GET_VALUES:
                self._run_get_picklist_values()
            elif choice == self.OPT_CREATE:
                self._run_create_picklist()
            elif choice == self.OPT_MODIFY:
                self._run_modify_picklist()
            else:
                self.callback.display_error("Unknown option selected.")
                return SapioWebhookResult(False)
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        except Exception as ex:
            self.callback.display_error(
                f"PickListManager Example Error:\n{ex!s}\n\n{traceback.format_exc()}"
            )
            return SapioWebhookResult(False)
        return SapioWebhookResult(True)

    def _run_list_all_picklists(self) -> None:
        """Java runListAllPicklists."""
        configs: list[PickListConfig] = self.list_man.get_picklist_config_list()
        count: int = len(configs) if configs else 0
        self.callback.display_info(f"Total picklists: {count}")
        if not configs:
            self.callback.display_info("No picklists are defined.")
            return
        max_show: int = 30
        names: list[str] = [c.pick_list_name for c in configs[:max_show]]
        suffix: str = ""
        if len(configs) > max_show:
            suffix = f", ... and {len(configs) - max_show} more"
        self.callback.display_info("Picklist names: " + ", ".join(names) + suffix)

    def _run_get_picklist_values(self) -> None:
        """Java runGetPicklistValues."""
        cfg: PickListConfig | None = self.list_man.get_picklist(self.EXAMPLE_PICKLIST_NAME)
        if cfg is None:
            all_cfgs: list[PickListConfig] = self.list_man.get_picklist_config_list()
            if all_cfgs:
                cfg = all_cfgs[0]
        if cfg is None:
            self.callback.display_info(
                "No picklists available. Create one first (e.g. via Create a new picklist)."
            )
            return
        name: str = cfg.pick_list_name
        entries: list[str] | None = cfg.entry_list
        size: int = len(entries) if entries else 0
        self.callback.display_info(f'Picklist "{name}" has {size} value(s).')
        if not entries:
            return
        max_show: int = 15
        shown: list[str] = entries[:max_show]
        vals: str = ", ".join(shown)
        if len(entries) > max_show:
            vals += f", ... and {len(entries) - max_show} more"
        self.callback.display_info(f"Values: {vals}")

    def _run_create_picklist(self) -> None:
        """Java runCreatePicklist."""
        existing: PickListConfig | None = self.list_man.get_picklist(self.EXAMPLE_PICKLIST_NAME)
        if existing is not None:
            self.callback.display_info(
                f'Picklist "{self.EXAMPLE_PICKLIST_NAME}" already exists. Use Modify to change it.'
            )
            return
        self.list_man.update_picklist_value_list(
            self.EXAMPLE_PICKLIST_NAME, ["Option A", "Option B", "Option C"]
        )
        self.callback.display_info(
            f'Created picklist "{self.EXAMPLE_PICKLIST_NAME}" with 3 initial values.'
        )

    def _run_modify_picklist(self) -> None:
        """Java runModifyPicklist."""
        cfg: PickListConfig | None = self.list_man.get_picklist(self.EXAMPLE_PICKLIST_NAME)
        if cfg is None:
            all_cfgs: list[PickListConfig] = self.list_man.get_picklist_config_list()
            if all_cfgs:
                cfg = all_cfgs[0]
        if cfg is None:
            self.callback.display_info(
                f'No picklist to modify. Create "{self.EXAMPLE_PICKLIST_NAME}" first.'
            )
            return
        entries: list[str] = list(cfg.entry_list) if cfg.entry_list else []
        new_entry: str = f"Added at {int(time.time() * 1000)}"
        entries.append(new_entry)
        self.list_man.update_picklist_value_list(cfg.pick_list_name, entries)
        self.callback.display_info(
            f'Updated picklist "{cfg.pick_list_name}"; added entry. Total entries now: {len(entries)}'
        )
