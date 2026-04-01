from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from sapiopylib.rest.utils.recordmodel.PyRecordModel import PyRecordModel


class OnSaveWebhookExample(CommonsWebhookHandler):
    """
    Webhook that runs within invocation from an on-save rule. This webhook makes use of the OnSaveRuleHandler class
    to grab records from the rule context.
    """
    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        # Grab the records from the rule context.
        subjects: list[PyRecordModel] = self.rule_handler.get_models("Subject")

        # Load the previous field values for the records.
        self.saved_vals_man.load(subjects)

        # Update fields.
        for subject in subjects:
            if self.saved_vals_man.get_last_saved_value(subject, "C_DateTreated") < subject.get_field_value("C_DateTreated"):
                subject.set_field_value("C_TreatmentDateRevised", True)

        # Store and commit changes.
        self.rec_man.store_and_commit()

        return SapioWebhookResult(True)
