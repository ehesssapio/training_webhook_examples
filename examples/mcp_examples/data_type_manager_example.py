"""
Created: 2026-03-19 15:20
Agent type: Composer
Modified: 2026-03-19 19:35
Agent type: Composer
Modified: 2026-03-26 17:00
Agent type: Composer

Python counterpart to Java DataTypeManagerExample.java
(`sapio://examples/java/features/data-type-manager`).

Query data type definitions, temporary types, layouts, and fields using DataTypeManager (REST).
"""

from __future__ import annotations

import traceback
from typing import Any

from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.datatype.DataType import DataTypeDefinition
from sapiopylib.rest.pojo.datatype.FieldDefinition import AbstractVeloxFieldDefinition
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult


class DataTypeManagerFeatureExample(CommonsWebhookHandler):
    OPT_ALL: str = "Get All Data Type Definitions"
    OPT_SINGLE: str = "Get Data Type Definition by Name"
    OPT_TEMP: str = "Get Temporary Data Type"
    OPT_DEFAULT_LAYOUT: str = "Get Default Layout for User/Group"
    OPT_SELECT_LAYOUT: str = "List and Select Layout"
    OPT_FIELDS: str = "Get Data Type Fields"
    OPT_DISPLAY_NAMES: str = "Get Display Names"

    MENU_OPTIONS: tuple[str, ...] = (
        OPT_ALL,
        OPT_SINGLE,
        OPT_TEMP,
        OPT_DEFAULT_LAYOUT,
        OPT_SELECT_LAYOUT,
        OPT_FIELDS,
        OPT_DISPLAY_NAMES,
    )

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.can_send_client_callback():
            return SapioWebhookResult(False, display_text="Requires client callback.")
        try:
            choice: str = self.callback.option_dialog(
                "DataTypeManager Examples",
                "Select which demonstration to run:\n\n"
                "These examples show how to use the DataTypeManager\n"
                "to query and work with data type definitions.",
                list(self.MENU_OPTIONS),
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        try:
            if choice == self.OPT_ALL:
                self._run_get_all_definitions_demo()
            elif choice == self.OPT_SINGLE:
                self._run_get_single_definition_demo()
            elif choice == self.OPT_TEMP:
                self._run_get_temporary_data_type_demo()
            elif choice == self.OPT_DEFAULT_LAYOUT:
                self._run_get_default_layout_demo()
            elif choice == self.OPT_SELECT_LAYOUT:
                self._run_select_layout_demo()
            elif choice == self.OPT_FIELDS:
                self._run_get_field_definitions_demo()
            elif choice == self.OPT_DISPLAY_NAMES:
                self._run_get_display_names_demo()
            else:
                self.callback.display_error("Unknown option selected.")
                return SapioWebhookResult(False)
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        except Exception as ex:
            self.callback.display_error(
                f"DataTypeManager Example Error:\n{ex}\n\n{traceback.format_exc()}"
            )
            return SapioWebhookResult(False)
        return SapioWebhookResult(True)

    def _prompt_for_data_type(self) -> str | None:
        """All names in one call (get_data_type_name_list); user picks one; fetch definition only after selection."""
        names_sorted: list[str] = sorted(
            self.dt_man.get_data_type_name_list(),
            key=lambda x: (x or "").upper(),
        )
        if not names_sorted:
            self.callback.display_warning("No data types available for selection.")
            return None
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

    def _run_get_all_definitions_demo(self) -> None:
        """One call for all names (get_data_type_name_list); sample first 20; no per-type definition traffic."""
        all_names: list[str] = sorted(
            self.dt_man.get_data_type_name_list(),
            key=lambda x: (x or "").upper(),
        )
        summary: str = (
            "=== Data Type Summary ===\n\n"
            f"Total data types: {len(all_names)}\n"
            "(Use get_data_type_definition(name) for one type’s metadata, e.g. pseudo / display names.)\n\n"
            "=== All data types (first 20, alphabetical) ===\n"
        )
        for name in all_names[:20]:
            summary += f"  - {name}\n"
        if len(all_names) > 20:
            summary += f"  ... and {len(all_names) - 20} more\n"
        self.callback.display_info(summary)

    def _run_get_single_definition_demo(self) -> None:
        """Java runGetSingleDefinitionDemo — pick type, show name, display names, flags, field count, layouts, parent/child."""
        selected_type_name = self._prompt_for_data_type()
        if not selected_type_name:
            return
        dt_def = self.dt_man.get_data_type_definition(selected_type_name)
        if dt_def is None:
            self.callback.display_warning(f"Data type '{selected_type_name}' not found.")
            return
        layouts = self.dt_man.get_data_type_layout_list(selected_type_name) or []
        field_list = self.dt_man.get_field_definition_list(selected_type_name) or []
        parent_list = dt_def.parent_list or []
        child_list = dt_def.child_list or []
        info: str = (
            f"=== Data Type: {selected_type_name} ===\n\n"
            f"Internal Name: {dt_def.data_type_name}\n"
            f"Display Name: {dt_def.display_name}\n"
            f"Plural Display Name: {dt_def.plural_display_name}\n\n"
            f"Is ELN Data Type: {dt_def.is_pseudo}\n"
            f"Is Attachment Type: {dt_def.is_attachment}\n"
            f"Is Extension Type: {dt_def.is_extension_type}\n\n"
            f"Number of Fields: {len(field_list)}\n"
            f"Number of Layouts: {len(layouts)}\n"
        )
        if layouts:
            info += "Available Layouts:\n"
            for layout in layouts:
                info += f"  - {layout.layout_name}\n"
        info += f"\nParent Types: {len(parent_list)}\n"
        info += f"Child Types: {len(child_list)}\n"
        self.callback.display_info(info)

    def _run_get_temporary_data_type_demo(self) -> None:
        """Java runGetTemporaryDataTypeDemo — pick type, default temp type, optional layout-specific, usage tips."""
        selected_type_name = self._prompt_for_data_type()
        if not selected_type_name:
            return
        dt_def = self.dt_man.get_data_type_definition(selected_type_name)
        if dt_def is None:
            self.callback.display_warning("Data type not found.")
            return
        temp_default = self.dt_man.get_temporary_data_type(selected_type_name)
        layouts = self.dt_man.get_data_type_layout_list(selected_type_name) or []
        selected_layout_name: str | None = None
        temp_with_layout: Any = None
        if layouts:
            if len(layouts) > 1:
                try:
                    picked: list[str] = self.callback.list_dialog(
                        "Select a Layout",
                        [x.layout_name for x in layouts],
                        multi_select=False,
                        shortcut_single_option=False,
                    )
                    if picked:
                        selected_layout_name = picked[0]
                        temp_with_layout = self.dt_man.get_temporary_data_type(
                            selected_type_name, selected_layout_name
                        )
                except SapioUserCancelledException:
                    pass
            else:
                selected_layout_name = layouts[0].layout_name
                temp_with_layout = self.dt_man.get_temporary_data_type(
                    selected_type_name, selected_layout_name
                )
        summary: str = (
            f"=== Temporary Data Type: {selected_type_name} ===\n\n"
            "Method 1 - Default Layout:\n"
        )
        if temp_default:
            summary += f"  Display Name: {temp_default.display_name}\n"
            summary += f"  Field Count: {len(temp_default.get_field_def_list())}\n"
        summary += f"\nMethod 2 - Specific Layout ({selected_layout_name}):\n"
        if temp_with_layout:
            summary += f"  Display Name: {temp_with_layout.display_name}\n"
            summary += f"  Field Count: {len(temp_with_layout.get_field_def_list())}\n"
        summary += (
            "\n--- Usage Tips ---\n"
            "TemporaryDataType is used with:\n"
            "  - clientCallback.showTableEntryDialog()\n"
            "  - clientCallback.showFieldEntryDialog()\n"
            "  - clientCallback.showDataRecordSelectionDialog()\n"
        )
        self.callback.display_info(summary)

    def _run_get_default_layout_demo(self) -> None:
        """Java runGetDefaultLayoutDemo — user layout, data type default, effective, all layouts."""
        selected_type_name = self._prompt_for_data_type()
        if not selected_type_name:
            return
        dt_def = self.dt_man.get_data_type_definition(selected_type_name)
        if dt_def is None:
            self.callback.display_warning("Data type not found.")
            return
        user_layout = getattr(self.user, "get_data_type_layout", None)
        if callable(user_layout):
            user_group_layout = user_layout(selected_type_name)
        else:
            user_group_layout = None
        data_type_default = self.dt_man.get_default_layout(selected_type_name)
        all_layouts = self.dt_man.get_data_type_layout_list(selected_type_name) or []
        effective = data_type_default
        info: str = (
            f"=== Layout Information for: {selected_type_name} ===\n\n"
            "1. User's Assigned Layout (user.getDataTypeLayout()):\n"
        )
        if user_group_layout is not None:
            info += f"   Layout Name: {getattr(user_group_layout, 'layout_name', user_group_layout)}\n"
            info += f"   Display Name: {getattr(user_group_layout, 'display_name', '')}\n"
        else:
            info += "   No user/group-specific layout from user.get_data_type_layout (or method absent).\n"
            info += "   Falls back to data type default below.\n"
        info += "\n2. Data Type's Default Layout (dt_man.get_default_layout()):\n"
        if data_type_default:
            info += f"   Layout Name: {data_type_default.layout_name}\n"
            info += f"   Display Name: {getattr(data_type_default, 'display_name', '')}\n"
        else:
            info += "   No default layout defined.\n"
        info += "\n3. Effective layout (same as data type default here):\n"
        if effective:
            info += f"   Layout Name: {effective.layout_name}\n"
            info += f"   Display Name: {getattr(effective, 'display_name', '')}\n"
        else:
            info += "   No layout available.\n"
        info += "\n4. All Available Layouts:\n"
        if all_layouts:
            for layout in all_layouts:
                current = effective and layout.layout_name == effective.layout_name
                info += f"   - {layout.layout_name}" + (" (current)" if current else "") + "\n"
        else:
            info += "   No layouts defined.\n"
        info += (
            "\n--- Layout Precedence ---\n"
            "1. User-specific layout (if assigned)\n"
            "2. User group layout (if assigned)\n"
            "3. Data type default layout\n"
        )
        self.callback.display_info(info)

    def _run_select_layout_demo(self) -> None:
        """Java runSelectLayoutDemo — pick type, pick layout, show name and display name."""
        selected_type_name = self._prompt_for_data_type()
        if not selected_type_name:
            return
        dt_def = self.dt_man.get_data_type_definition(selected_type_name)
        if dt_def is None:
            self.callback.display_warning("Data type not found.")
            return
        layouts = self.dt_man.get_data_type_layout_list(selected_type_name) or []
        if not layouts:
            self.callback.display_info(f"No layouts defined for {selected_type_name}")
            return
        try:
            picked: list[str] = self.callback.list_dialog(
                f"Select a Layout for {selected_type_name}",
                [x.layout_name for x in layouts],
                multi_select=False,
                shortcut_single_option=False,
            )
        except SapioUserCancelledException:
            return
        if not picked:
            return
        selected_layout_name = picked[0]
        selected_layout = next(
            (x for x in layouts if x.layout_name == selected_layout_name), None
        )
        if selected_layout:
            info: str = (
                f"Data Type: {selected_type_name}\n"
                f"Layout: {selected_layout.layout_name}\n"
                f"Display Name: {getattr(selected_layout, 'display_name', '')}\n"
            )
            self.callback.display_info(info)

    def _run_get_field_definitions_demo(self) -> None:
        """Java runGetFieldDefinitionsDemo — core fields with REQUIRED/KEY, extension count if available."""
        selected_type_name = self._prompt_for_data_type()
        if not selected_type_name:
            return
        dt_def = self.dt_man.get_data_type_definition(selected_type_name)
        if dt_def is None:
            self.callback.display_warning("Data type not found.")
            return
        field_list: list[AbstractVeloxFieldDefinition] = (
            self.dt_man.get_field_definition_list(selected_type_name) or []
        )
        core_count = len(field_list)
        info: str = (
            f"=== Field Definitions for: {selected_type_name} ===\n\n"
            f"Core Fields: {core_count}\n"
            f"Total Fields (with extensions): {core_count}\n\n"
            "--- Core Fields ---\n"
        )
        field_by_name: dict[str, AbstractVeloxFieldDefinition] = {
            f.data_field_name: f for f in field_list
        }
        for field_name in sorted(field_by_name.keys(), key=lambda x: (x or "").upper()):
            fd = field_by_name[field_name]
            disp = getattr(fd, "display_name", field_name)
            info += f"  {field_name} ({disp})"
            if getattr(fd, "required", False):
                info += " [REQUIRED]"
            if getattr(fd, "key_field", False):
                info += " [KEY]"
            info += "\n"
        self.callback.display_info(info)

    def _run_get_display_names_demo(self) -> None:
        """Java runGetDisplayNamesDemo — common types via get_data_type_definition each; total count from name list."""
        all_names: list[str] = self.dt_man.get_data_type_name_list()
        common_types: list[str] = ["Sample", "Plate", "Request", "Process", "ELNExperiment"]
        info: str = (
            "=== Display Names Demo ===\n\n"
            "DataTypeManager methods:\n"
            "  - getDisplayName(typeName) - singular\n"
            "  - getPluralDisplayName(typeName) - plural\n\n"
            "DataTypeDefinition (from get_data_type_definition):\n"
            "  - display_name - singular\n"
            "  - plural_display_name - plural\n\n"
            "--- Examples ---\n\n"
        )
        for type_name in common_types:
            dt_def: DataTypeDefinition | None = self.dt_man.get_data_type_definition(type_name)
            if dt_def is not None:
                info += f"Data Type: {type_name}\n"
                info += f"  Display Name: {dt_def.display_name}\n"
                info += f"  Plural: {dt_def.plural_display_name}\n\n"
        info += (
            "--- Summary ---\n"
            f"Total data types (name list): {len(all_names)}\n"
            "(For display names across all types, call get_data_type_definition per name or only for types you need.)\n"
        )
        self.callback.display_info(info)
