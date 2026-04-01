"""
ComplexDataLoaderExample - Python Main Toolbar Webhook

This example demonstrates how to use the Complex Data Loader (CDL) programmatically
in a Python webhook. The CDL allows loading data from files (CSV, XLSX, etc.) into
Sapio data records using pre-configured loader definitions.

When executed from the main toolbar, this webhook:
1. Queries for existing CDL configurations and lets the user select one
2. Prompts the user to upload a file
3. Loads the file using the selected CDL configuration
4. Displays a summary of the created records

Configuration:
- This webhook should be linked to a main toolbar button in Sapio
- CDL configurations must be pre-created in the system via the CDL Configuration tool
"""

from sapiopycommons.files.complex_data_loader import CDL
from sapiopycommons.general.exceptions import SapioUserCancelledException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookDirective import TableDirective
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult


class ComplexDataLoaderExample(CommonsWebhookHandler):
    """
    Main toolbar webhook that demonstrates using the Complex Data Loader (CDL)
    to create data records from an uploaded file.
    """

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        """
        Main execution method called when the toolbar button is clicked.

        :param context: The webhook context containing user and system information.
        :return: A SapioWebhookResult indicating success/failure.
        """
        # Step 1: Get available CDL configurations and let user select one
        config_name: str | None = self._prompt_for_cdl_configuration()
        if config_name is None:
            raise SapioUserCancelledException("User cancelled CDL configuration selection.")

        # Step 2: Prompt the user to upload a file
        file_name: str
        file_bytes: bytes
        file_name, file_bytes = self._prompt_for_file()

        # Step 3: Load the file using the CDL
        record_ids: list[int] = CDL.load_cdl(context, config_name, file_name, file_bytes)

        # Step 4: Display results to user
        if record_ids:
            # Retrieve the created records to show in a table
            created_records = self.dr_man.query_data_records_by_id(config_name, record_ids).result_list

            self.callback.display_info(
                f"CDL Load Complete: Successfully created {len(record_ids)} record(s) "
                f"using configuration '{config_name}'."
            )

            # Return success with a table showing the created records
            return SapioWebhookResult(
                True,
                f"Created {len(record_ids)} records.",
                directive=TableDirective(created_records)
            )
        else:
            self.callback.display_warning(
                "CDL Load Complete: No records were created. "
                "The file may have been empty or contained no valid data."
            )
            return SapioWebhookResult(True, "No records created.")

    def _prompt_for_cdl_configuration(self) -> str | None:
        """
        Queries for existing CDL configurations and presents them to the user for selection.

        :return: The selected configuration name, or None if cancelled or no configurations exist.
        """
        # Query all CDLConfig records from the system
        config_records = self.dr_man.query_all_records_of_type("CDLConfig").result_list

        if not config_records:
            self.callback.display_warning(
                "No CDL configurations found. "
                "Please create a CDL configuration in the system first."
            )
            return None

        # Extract unique configuration names
        config_names: set[str] = set()
        for record in config_records:
            config_name = record.get_field_value("ConfigurationName")
            if config_name:
                config_names.add(str(config_name).strip())

        if not config_names:
            self.callback.display_warning(
                "CDL configuration records exist but none have a Configuration Name set."
            )
            return None

        # Sort the configuration names alphabetically
        sorted_config_names: list[str] = sorted(config_names)

        # Show selection dialog to user
        selected_config: list[str] = self.callback.list_dialog(
            title=f"Select a CDL configuration to use for loading data.\n\n"
                    f"Found {len(sorted_config_names)} configuration(s) on the system.",
            options=sorted_config_names
        )

        return selected_config[0]

    def _prompt_for_file(self) -> tuple[str, bytes]:
        """
        Prompts the user to upload a file for CDL loading.

        :return: A tuple of (file_name, file_bytes).
        :raises SapioUserCancelledException: If the user cancels the file selection.
        """
        # Request a file from the user - allow common data file formats
        # The CDL configuration determines which file types are actually supported
        file_name: str
        file_bytes: bytes
        file_name, file_bytes = self.callback.request_file(
            title="Select a file to load",
            exts=["csv", "xlsx", "xls", "txt", "tsv"]
        )

        return file_name, file_bytes


class SimpleCDLExample(ComplexDataLoaderExample):
    """
    A minimal CDL example that demonstrates the simplest possible usage.

    This example:
    1. Queries for available CDL configurations and lets the user select one
    2. Prompts the user for a file
    3. Loads the file using the selected CDL configuration

    Inherits helper methods from ComplexDataLoaderExample for prompting.
    Use this as a starting template for basic CDL operations.
    """

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        """Execute the simple CDL load."""
        # Query for CDL configurations and let user select one
        config_name: str | None = self._prompt_for_cdl_configuration()
        if config_name is None:
            raise SapioUserCancelledException("User cancelled CDL configuration selection.")

        # Request file from user
        file_name: str
        file_bytes: bytes
        file_name, file_bytes = self._prompt_for_file()

        # Load the file using the CDL
        record_ids: list[int] = CDL.load_cdl(context, config_name, file_name, file_bytes)

        return SapioWebhookResult(True, f"Created {len(record_ids)} new records in the system.")
