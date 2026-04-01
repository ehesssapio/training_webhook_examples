from sapiopycommons.callbacks.callback_util import BlankResultHandling
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.datatype.FieldDefinition import VeloxIntegerFieldDefinition
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookDirective import TableDirective
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from sapiopylib.rest.utils.recordmodel.PyRecordModel import PyRecordModel


class MainToolbarWebhookExample(CommonsWebhookHandler):
    """
    Webhook that's invoked from the click of a main toolbar button linked to this webhook.
    """
    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        # Prompt the user to enter the number of samples to create.
        num_samples: int = self.callback.input_dialog("Create Samples", "Enter the number of samples to register",
                                                      VeloxIntegerFieldDefinition("NumSamples", "NumSamples", "Number of Samples"),
                                                      require_input=True, blank_result_handling=BlankResultHandling.REPEAT,
                                                      repeat_message="Please provide a non-blank numerical value to continue.",
                                                      cancel_message="User cancelled dialog.")

        # Create that many samples.
        sample_models: list[PyRecordModel] = self.inst_man.add_new_records("Sample", num_samples)

        # Store and commit changes.
        self.rec_man.store_and_commit()

        # Return a SapioWebhookResult of True with a TableDirective to show the user the newly created samples in a table.
        return SapioWebhookResult(True, directive=TableDirective([x.get_data_record() for x in sample_models]))
