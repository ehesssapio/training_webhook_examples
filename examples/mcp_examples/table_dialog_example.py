"""
Created: 2025-03-05 00:00
Agent type: Composer
Modified: 2026-03-19 15:30
Agent type: Composer
Modified: 2026-03-19 17:05
Agent type: Composer

Table toolbar webhook: `table_dialog` → `add_new_record` → `store_and_commit` for bulk capture on REST.
"""

from __future__ import annotations

from typing import Any

from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from sapiopylib.rest.utils.recordmodel.PyRecordModel import PyRecordModel
from sapiopylib.rest.pojo.datatype.FieldDefinition import VeloxStringFieldDefinition, VeloxDoubleFieldDefinition
from sapiopycommons.general.exceptions import SapioUserCancelledException


class TableDialogExample(CommonsWebhookHandler):
    """
    Example webhook demonstrating how to use a table dialog for bulk record input.

    TableDialogExample prompts the user with a table-based input dialog, where each row represents data for a new
    record to be created (e.g., registering samples). The user is required to fill out fields for each item, and
    can cancel the dialog at any time. After confirmation, new records are created and committed using the data
    entered in the dialog.

    Key Features:
        - Uses editable, required string and double fields for user input in the dialog.
        - Handles user cancellation gracefully.
        - Automatically creates multiple records based on table input.
        - Illustrates how to use preset values to initialize table dialog rows.

    Typical Use Case:
        Use a table dialog when displaying a table would be more ideal for either input or display purposes.
    """
    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        num_samples: int = 10

        # Define fields to use for the table dialog.
        sample_name_field: VeloxStringFieldDefinition = VeloxStringFieldDefinition(data_type_name="OtherSampleId", data_field_name="OtherSampleId", display_name="Sample Name")
        sample_name_field.editable = True  # Field value should be editable.
        sample_name_field.required = True  # Field value is required (cannot be blank.)

        volume_field: VeloxDoubleFieldDefinition = VeloxDoubleFieldDefinition(data_type_name="Volume", data_field_name="Volume", display_name="Volume")
        volume_field.editable = True

        # Create rows with preset values for the table dialog. In this case, we need num_samples rows, since we need data
        # for each sample the user wants to register.
        preset_values: list[dict[str, Any]] = [{"OtherSampleId": "", "Volume": 0,} for x in range(num_samples)]

        # Prompt the dialog and account for user cancellation.
        try:
            results: list[dict[str, Any]] = self.callback.table_dialog(title="Register Samples", msg="Enter details for the samples.", 
                fields=[sample_name_field, volume_field], values=preset_values)
        except SapioUserCancelledException:
            return SapioWebhookResult(True)
        if results is None or len(results) == 0:
            return SapioWebhookResult(True)

        # Create the samples.
        for row in results:
            sample: PyRecordModel = self.inst_man.add_new_record("Sample")
            sample.set_field_value("OtherSampleId", row.get("OtherSampleId"))  # Retrieve a field value by referencing it's field name, which was set in the VeloxFieldDefinition instance as data_field_name.
            sample.set_field_value("Volume", row.get("Volume"))

        # Store and commit changes.
        self.rec_man.store_and_commit()

        return SapioWebhookResult(True)
