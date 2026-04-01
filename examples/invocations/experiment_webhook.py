from sapiopycommons.general.time_util import TimeUtil
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.eln.SapioELNEnums import ElnExperimentStatus
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from sapiopylib.rest.utils.recordmodel.PyRecordModel import PyRecordModel


class ExperimentWebhookExample(CommonsWebhookHandler):
    """
    Webhook that runs within the context of an experiment. It makes use of the ElnRuleHandler and ExperimentHandler
    classes.
    """
    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        # Grab the samples from the rule context.
        sample_models: list[PyRecordModel] = self.rule_handler.get_models("Sample")  # This is using the ElnRuleHandler, since the webhook is invoked in the context of an experiment.
        for sample_model in sample_models:
            sample_model.set_field_value("C_Completed", True)

        # Grab the records from the instrument results entry and set fields.
        datum_models: list[PyRecordModel] = self.exp_handler.get_step_models("Instrument Results")
        for datum_model in datum_models:
            datum_model.set_field_value("C_DateCompleted", TimeUtil.now_in_millis())

        # Store and commit changes.
        self.rec_man.store_and_commit()

        # Complete the experiment.
        self.exp_handler.update_experiment(experiment_status=ElnExperimentStatus.Completed)

        return SapioWebhookResult(True)
