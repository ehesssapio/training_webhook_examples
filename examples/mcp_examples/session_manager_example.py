"""
Created: 2026-03-19 15:20
Agent type: Composer
Modified: 2026-03-19 21:10
Agent type: Composer
Modified: 2026-03-20 12:00
Agent type: Composer

Python counterpart to Java SessionManagerExample.java
(`sapio://examples/java/features/session-manager`).

Messaging via SapioMessenger and VeloxMessage (user_message, group_message, broadcast_message).
"""

from __future__ import annotations

import traceback

from sapiopycommons.callbacks.callback_util import BlankResultHandling
from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.Message import VeloxMessage
from sapiopylib.rest.pojo.datatype.FieldDefinition import VeloxStringFieldDefinition
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult


class SessionManagerFeatureExample(CommonsWebhookHandler):
    OPT_USER: str = "Send User Message"
    OPT_GROUP: str = "Send Group Message"
    OPT_APP: str = "Send App Message"
    OPT_ACCOUNT: str = "Send Account Message"
    OPT_SYSTEM: str = "Send System Message"
    OPT_ALL: str = "Demonstrate All Methods"
    MENU_OPTIONS: tuple[str, ...] = (
        OPT_USER,
        OPT_GROUP,
        OPT_APP,
        OPT_ACCOUNT,
        OPT_SYSTEM,
        OPT_ALL,
    )

    @staticmethod
    def _input_as_string(value: object | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return str(value)

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.can_send_client_callback():
            return SapioWebhookResult(False, display_text="Requires client callback.")
        try:
            choice: str = self.callback.option_dialog(
                "SessionManager Send Message Examples",
                "Select which send message method to demonstrate:",
                list(self.MENU_OPTIONS),
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        try:
            if choice == self.OPT_USER:
                self._run_send_user_message_demo()
            elif choice == self.OPT_GROUP:
                self._run_send_group_message_demo()
            elif choice == self.OPT_APP:
                self._run_send_app_message_demo()
            elif choice == self.OPT_ACCOUNT:
                self._run_send_account_message_demo()
            elif choice == self.OPT_SYSTEM:
                self._run_send_system_message_demo()
            elif choice == self.OPT_ALL:
                self._run_all_methods_demo()
            else:
                self.callback.display_error("Unknown option selected.")
                return SapioWebhookResult(False)
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        except Exception as ex:
            self.callback.display_error(
                f"SessionManager Example Error:\n{ex!s}\n\n{traceback.format_exc()}"
            )
            return SapioWebhookResult(False)
        return SapioWebhookResult(True)

    def _run_send_user_message_demo(self) -> None:
        raw_u: object = self.callback.input_dialog(
            "Send User Message",
            "Enter usernames separated by commas:",
            VeloxStringFieldDefinition("SessionDemo", "Usernames", "Usernames", max_length=2000, editable=True),
            blank_result_handling=BlankResultHandling.CANCEL,
        )
        usernames_input: str | None = self._input_as_string(raw_u)
        if usernames_input is None or not usernames_input.strip():
            self.callback.display_warning("No usernames provided. Cancelling operation.")
            return
        recipient_users: list[str] = [p.strip() for p in usernames_input.split(",") if p.strip()]
        if not recipient_users:
            self.callback.display_warning("No valid usernames provided. Cancelling operation.")
            return
        raw_m: object = self.callback.input_dialog(
            "Send User Message",
            "Enter the message to send:",
            VeloxStringFieldDefinition("SessionDemo", "Message", "Message", max_length=4000, editable=True),
            blank_result_handling=BlankResultHandling.CANCEL,
        )
        message: str | None = self._input_as_string(raw_m)
        if message is None or not message.strip():
            self.callback.display_warning("No message provided. Cancelling operation.")
            return
        self.messenger.send_message(VeloxMessage.user_message(recipient_users, message))
        self.callback.display_info(
            f"User Message Sent\n\nMessage sent to {len(recipient_users)} user(s)."
        )

    def _run_send_group_message_demo(self) -> None:
        available_groups: list[str] = self.group_man.get_user_group_name_list()
        groups_hint: str = ", ".join(available_groups) if available_groups else "None"
        raw_g: object = self.callback.input_dialog(
            "Send Group Message",
            f"Enter group names separated by commas. Available groups: {groups_hint}",
            VeloxStringFieldDefinition("SessionDemo", "Groups", "Group names", max_length=2000, editable=True),
            blank_result_handling=BlankResultHandling.CANCEL,
        )
        groups_input: str | None = self._input_as_string(raw_g)
        if groups_input is None or not groups_input.strip():
            self.callback.display_warning("No group names provided. Cancelling operation.")
            return
        recipient_groups: list[str] = [p.strip() for p in groups_input.split(",") if p.strip()]
        if not recipient_groups:
            self.callback.display_warning("No valid group names provided. Cancelling operation.")
            return
        raw_m: object = self.callback.input_dialog(
            "Send Group Message",
            "Enter the message to send:",
            VeloxStringFieldDefinition("SessionDemo", "Message", "Message", max_length=4000, editable=True),
            blank_result_handling=BlankResultHandling.CANCEL,
        )
        message: str | None = self._input_as_string(raw_m)
        if message is None or not message.strip():
            self.callback.display_warning("No message provided. Cancelling operation.")
            return
        self.messenger.send_message(VeloxMessage.group_message(recipient_groups, message))
        self.callback.display_info(
            f"Group Message Sent\n\nMessage sent to {len(recipient_groups)} group(s)."
        )

    def _run_send_app_message_demo(self) -> None:
        raw_m: object = self.callback.input_dialog(
            "Send App Message",
            "Enter the message to send to all logged-in users:",
            VeloxStringFieldDefinition("SessionDemo", "Message", "Message", max_length=4000, editable=True),
            blank_result_handling=BlankResultHandling.CANCEL,
        )
        message: str | None = self._input_as_string(raw_m)
        if message is None or not message.strip():
            self.callback.display_warning("No message provided. Cancelling operation.")
            return
        if not self.callback.yes_no_dialog(
            "Confirm App Message", "Send to all logged-in users?", True
        ):
            self.callback.display_info("App message cancelled by user.")
            return
        self.messenger.send_message(VeloxMessage.broadcast_message(message))
        self.callback.display_info("App Message Sent\n\nMessage sent to all logged-in users.")

    def _run_send_account_message_demo(self) -> None:
        raw_m: object = self.callback.input_dialog(
            "Send Account Message",
            "Enter the message to send to all users in the account:",
            VeloxStringFieldDefinition("SessionDemo", "Message", "Message", max_length=4000, editable=True),
            blank_result_handling=BlankResultHandling.CANCEL,
        )
        message: str | None = self._input_as_string(raw_m)
        if message is None or not message.strip():
            self.callback.display_warning("No message provided. Cancelling operation.")
            return
        if not self.callback.yes_no_dialog(
            "Confirm Account Message", "Send to ALL users in the account?", True
        ):
            self.callback.display_info("Account message cancelled by user.")
            return
        self.messenger.send_message(VeloxMessage.broadcast_message(message))
        self.callback.display_info("Account Message Sent\n\nMessage broadcast via VeloxMessage.")

    def _run_send_system_message_demo(self) -> None:
        self.callback.display_info(
            "Use sendAppMessage or sendAccountMessage for application- or account-wide broadcast."
        )

    def _run_all_methods_demo(self) -> None:
        current_username: str = self.user.username or ""
        if not current_username.strip():
            self.callback.display_warning(
                "Current SapioUser has no username; sendUserMessage demo may not target you."
            )
        available_groups: list[str] = self.group_man.get_user_group_name_list()
        summary_parts: list[str] = ["SessionManager / messenger demonstration:\n"]

        test_users: list[str] = [current_username] if current_username.strip() else []
        if test_users:
            self.messenger.send_message(VeloxMessage.user_message(test_users, "Test user message"))
            summary_parts.append(f"1. sendUserMessage - sent to {current_username}\n")
        else:
            summary_parts.append("1. sendUserMessage - skipped (no username on token user)\n")

        if available_groups:
            test_groups: list[str] = [available_groups[0]]
            self.messenger.send_message(
                VeloxMessage.group_message(test_groups, "Test group message")
            )
            summary_parts.append(f"2. sendGroupMessage - sent to {available_groups[0]}\n")
        else:
            summary_parts.append("2. sendGroupMessage - skipped (no groups)\n")

        self.messenger.send_message(VeloxMessage.broadcast_message("Test app message"))
        summary_parts.append("3. sendAppMessage (broadcast) - sent\n")

        self.messenger.send_message(VeloxMessage.broadcast_message("Test account message"))
        summary_parts.append("4. sendAccountMessage (broadcast via REST) - sent\n")

        summary_parts.append("5. sendSystemMessage - skipped (see menu)\n")

        self.callback.display_info("All Methods Demonstration\n\n" + "".join(summary_parts))
