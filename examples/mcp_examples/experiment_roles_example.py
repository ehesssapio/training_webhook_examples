"""
Created: 2026-03-19 15:20
Agent type: Composer
Modified: 2026-03-19 22:30
Agent type: Composer
Modified: 2026-03-20 12:00
Agent type: Composer

Python counterpart to Java ExperimentRolesExamplePlugin.java
(`sapio://examples/java/features/experiment-roles`).

Uses eln_man.update_role_assignment with ElnRoleAssignment (set/remove user and group roles on an experiment).
"""

from __future__ import annotations

import traceback

from sapiopycommons.callbacks.callback_util import BlankResultHandling
from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.User import SapioServerException
from sapiopylib.rest.pojo.datatype.FieldDefinition import VeloxStringFieldDefinition
from sapiopylib.rest.pojo.eln.ElnExperimentRole import (
    ElnGroupExperimentRole,
    ElnRoleAssignment,
    ElnUserExperimentRole,
)
from sapiopylib.rest.pojo.UserInfo import UserGroupInfo
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult


class ExperimentRolesFeatureExample(CommonsWebhookHandler):
    ACTION_REMOVE_GROUP: str = "Remove group access"
    ACTION_REMOVE_USER: str = "Remove user access"
    ACTION_SET_GROUP: str = "Set group to role(s)"
    ACTION_SET_USER: str = "Set user to role(s)"

    def _sorted_actions(self) -> list[str]:
        actions: list[str] = [
            self.ACTION_SET_USER,
            self.ACTION_SET_GROUP,
            self.ACTION_REMOVE_USER,
            self.ACTION_REMOVE_GROUP,
        ]
        actions.sort()
        return actions

    def _pick_roles(self) -> tuple[bool, bool, bool, bool] | None:
        """Returns (author, witness, reviewer, approver) or None if cancelled."""
        author: bool = self.callback.yes_no_dialog("Role: Author?", "Grant Author role?", False)
        witness: bool = self.callback.yes_no_dialog("Role: Witness?", "Grant Witness role?", False)
        reviewer: bool = self.callback.yes_no_dialog("Role: Reviewer?", "Grant Reviewer role?", False)
        approver: bool = self.callback.yes_no_dialog("Role: Approver?", "Grant Approver role?", False)
        return author, witness, reviewer, approver

    def _safe_update_role_assignment(
        self,
        exp_id: int,
        assignment: ElnRoleAssignment,
        show_as_error: bool = False,
    ) -> bool:
        try:
            self.eln_man.update_role_assignment(exp_id, assignment)
            return True
        except SapioServerException as ex:
            message = (
                "Role assignment failed validation for this experiment. "
                f"Server response: {ex!s}"
            )
            if show_as_error:
                self.callback.display_error(message)
            else:
                self.callback.display_warning(message)
            return False

    def _pick_group(self) -> tuple[int, str] | None:
        group_infos: list[UserGroupInfo] = self.group_man.get_user_group_info_list()
        if not group_infos:
            self.callback.display_info("No user groups returned from group manager.")
            return None
        by_label: dict[str, tuple[int, str]] = {}
        for info in group_infos:
            label = f"{info.group_name} (id={info.group_id})"
            by_label[label] = (info.group_id, info.group_name)
        labels: list[str] = sorted(by_label.keys())
        try:
            picked: list[str] = self.callback.list_dialog(
                "Select group",
                labels[:500],
                multi_select=False,
                shortcut_single_option=False,
            )
        except SapioUserCancelledException:
            return None
        if not picked:
            return None
        return by_label.get(picked[0])

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.can_send_client_callback():
            return SapioWebhookResult(False, display_text="Requires client callback.")
        exp_id: int | None = (
            context.eln_experiment.notebook_experiment_id if context.eln_experiment else None
        )
        if exp_id is None:
            return SapioWebhookResult(
                True,
                display_text="Run from experiment toolbar context (eln_experiment required).",
            )
        sorted_actions: list[str] = self._sorted_actions()
        try:
            choice: str = self.callback.option_dialog(
                "Choose an example action",
                "Experiment role demos:",
                sorted_actions,
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        try:
            if choice == self.ACTION_SET_USER:
                self._run_set_user_roles(exp_id)
            elif choice == self.ACTION_SET_GROUP:
                self._run_set_group_roles(exp_id)
            elif choice == self.ACTION_REMOVE_USER:
                self._run_remove_user(exp_id)
            elif choice == self.ACTION_REMOVE_GROUP:
                self._run_remove_group(exp_id)
            else:
                self.callback.display_warning(f"Unknown action: {choice}")
                return SapioWebhookResult(False)
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        except Exception as ex:
            self.callback.display_error(
                f"Experiment Roles Example failed: {ex!s}\n{traceback.format_exc()}"
            )
            return SapioWebhookResult(False)
        return SapioWebhookResult(True)

    def _run_set_user_roles(self, exp_id: int) -> None:
        users: list[str] = self.user_man.get_user_name_list(include_deactivated_users=False)
        if not users:
            self.callback.display_info("No active usernames returned from user manager.")
            return
        try:
            picked: list[str] = self.callback.list_dialog(
                "Select user",
                users[:500],
                multi_select=False,
                shortcut_single_option=False,
            )
        except SapioUserCancelledException:
            return
        if not picked:
            return
        username: str = picked[0]
        roles = self._pick_roles()
        if roles is None:
            return
        a, w, r, ap = roles
        if not self.callback.yes_no_dialog(
            "Confirm",
            f"POST role assignment for {username!r} on experiment {exp_id}?",
            False,
        ):
            return
        assign = ElnRoleAssignment(
            [ElnUserExperimentRole(a, w, r, ap, username)],
            [],
        )
        if self._safe_update_role_assignment(exp_id, assign):
            self.callback.display_info("Role assignment updated.")

    def _run_set_group_roles(self, exp_id: int) -> None:
        picked_group = self._pick_group()
        if picked_group is None:
            return
        gid, group_name = picked_group
        roles = self._pick_roles()
        if roles is None:
            return
        a, w, r, ap = roles
        if not self.callback.yes_no_dialog(
            "Confirm",
            f"POST group role assignment for {group_name!r} (group_id={gid}) on experiment {exp_id}?",
            False,
        ):
            return
        assign = ElnRoleAssignment(
            [],
            [ElnGroupExperimentRole(a, w, r, ap, gid)],
        )
        if self._safe_update_role_assignment(exp_id, assign, show_as_error=True):
            self.callback.display_info("Group role assignment updated.")

    def _run_remove_user(self, exp_id: int) -> None:
        raw: object = self.callback.input_dialog(
            "Remove user access",
            "Username to clear roles for:",
            VeloxStringFieldDefinition("RoleDemo", "User", "Username", max_length=200, editable=True),
            blank_result_handling=BlankResultHandling.REPEAT,
        )
        username: str = str(raw).strip() if raw is not None else ""
        if not username:
            return
        if not self.callback.yes_no_dialog(
            "Confirm",
            f"Remove all roles for {username!r} on experiment {exp_id}?",
            False,
        ):
            return
        assign = ElnRoleAssignment(
            [ElnUserExperimentRole(False, False, False, False, username)],
            [],
        )
        if self._safe_update_role_assignment(exp_id, assign):
            self.callback.display_info("User roles cleared (all flags false).")

    def _run_remove_group(self, exp_id: int) -> None:
        picked_group = self._pick_group()
        if picked_group is None:
            return
        gid, group_name = picked_group
        if not self.callback.yes_no_dialog(
            "Confirm",
            f"Remove all roles for {group_name!r} (group_id={gid}) on experiment {exp_id}?",
            False,
        ):
            return
        assign = ElnRoleAssignment(
            [],
            [ElnGroupExperimentRole(False, False, False, False, gid)],
        )
        if self._safe_update_role_assignment(exp_id, assign, show_as_error=True):
            self.callback.display_info("Group roles cleared (all flags false).")
