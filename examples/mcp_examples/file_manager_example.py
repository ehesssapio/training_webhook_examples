"""
Created: 2026-03-19 15:20
Agent type: Composer
Modified: 2026-03-19 20:05
Agent type: Composer

Python counterpart to Java FileManagerExample.java
(`sapio://examples/java/features/file-manager`).

Client file pick, CSV download, and upload via CallbackUtil `request_file` / `write_file`.
"""

from __future__ import annotations

import traceback

from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult


class FileManagerFeatureExample(CommonsWebhookHandler):
    OPT_CLIENT: str = "Client File Operations"
    OPT_DOWNLOAD: str = "Download Sample File"
    OPT_UPLOAD: str = "Upload File"
    MENU_OPTIONS: tuple[str, ...] = (OPT_CLIENT, OPT_DOWNLOAD, OPT_UPLOAD)

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not self.can_send_client_callback():
            return SapioWebhookResult(False, display_text="Requires client callback.")
        try:
            choice: str = self.callback.option_dialog(
                "FileManager Examples",
                "Select which demonstration to run:",
                list(self.MENU_OPTIONS),
                0,
                user_can_cancel=True,
            )
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        try:
            if choice == self.OPT_CLIENT:
                self._run_client_ops_demo()
            elif choice == self.OPT_DOWNLOAD:
                self._run_download_demo()
            elif choice == self.OPT_UPLOAD:
                self._run_upload_demo()
            else:
                self.callback.display_error("Unknown option selected.")
                return SapioWebhookResult(False)
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        except Exception as ex:
            self.callback.display_error(
                f"FileManager Example Error:\n{ex}\n\n{traceback.format_exc()}"
            )
            return SapioWebhookResult(False)
        return SapioWebhookResult(True)

    def _run_client_ops_demo(self) -> None:
        """Java runClientOpsDemo — showFileDialog, display selection or cancel."""
        try:
            file_path: str
            _data: bytes
            file_path, _data = self.callback.request_file("Select a File", enforce_file_extensions=False)
        except SapioUserCancelledException:
            self.callback.display_info(
                "File Selection Result\n\n✓ File selection was cancelled"
            )
            return
        self.callback.display_info(
            "File Selection Result\n\n✓ You selected:\n" + file_path
        )

    def _run_download_demo(self) -> None:
        """Write a sample CSV to the client."""
        csv_content: str = (
            "SampleId,Volume,Concentration,Status\n"
            "SAMPLE-001,100.0,50.5,Active\n"
            "SAMPLE-002,150.0,75.2,Active\n"
            "SAMPLE-003,200.0,100.0,Complete\n"
            "SAMPLE-004,125.0,62.5,Pending"
        )
        self.callback.write_file("sample_export.csv", csv_content.encode("utf-8"))
        self.callback.display_info("✓ CSV file download initiated!")

    def _run_upload_demo(self) -> None:
        """Pick a file, read bytes, report size."""
        try:
            file_name: str
            file_bytes: bytes
            file_name, file_bytes = self.callback.request_file(
                "Select a file to upload", enforce_file_extensions=False
            )
        except SapioUserCancelledException:
            self.callback.display_info("File selection cancelled")
            return
        if not file_bytes:
            self.callback.display_error("Failed to read file bytes")
            return
        self.callback.display_info(
            f"Successfully loaded file: {file_name} ({len(file_bytes)} bytes)"
        )
