from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from sapiopylib.rest.utils.recordmodel.PyRecordModel import PyRecordModel


class ExperimentToolbarWebhookExperiment(CommonsWebhookHandler):
    """
    Webhook that is invoked upon clicking an experiment toolbar button linked to this webhook.
    """
    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        # Get the records in the "Volumes" entry of the experiment.
        exp_details: list[PyRecordModel] = self.inst_man.add_existing_records(self.exp_handler.get_step_records("Volumes"))

        # Extract the volume values from each record and compute the average.
        volumes: list[float] = [x.get_field_value("Volume") for x in exp_details]
        avg_volume = sum(volumes) / len(volumes)

        # Update the experiment's average volume field.
        experiment_record: PyRecordModel = self.inst_man.add_existing_record(self.exp_handler.get_experiment_record())
        experiment_record.set_field_value("C_AverageVolume", avg_volume)

        # Store and commit changes.
        self.rec_man.store_and_commit()

        return SapioWebhookResult(True)
