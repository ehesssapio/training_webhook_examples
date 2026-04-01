import json
from abc import ABC
from typing import Any

from sapiopycommons.webhook.webservice_handlers import CommonsWebserviceHandler, SapioWebserviceResult, \
    SapioWebserviceException
from sapiopylib.rest.User import SapioUser
from sapiopylib.rest.utils.recordmodel.PyRecordModel import PyRecordModel
from werkzeug.datastructures import Headers, MultiDict


class WebserviceExample(CommonsWebserviceHandler, ABC):
    """
    Example of a class extending the CommonsWebserviceHandler base class. This example gives a basic implementation
    of a webhook-based Sapio webservice.

    Registering the webservice is the same as registering a webhook. The WebhookConfiguration in server.py just needs
    to have this class registered to it. "config.register('/my-webservice-endpoint', WebserviceExample)" for example.
    """
    def execute(self, user: SapioUser, payload: Any, headers: Headers, params: MultiDict[str, str]) -> SapioWebserviceResult:
        # Extract data from the headers. We can raise a SapioWebserviceException with an error message and status code
        # to reply with.
        if headers.get("Content-Type") != "application/json":
            raise SapioWebserviceException("application/json content-type is expected.", 500)

        # Extract some data from the payload. In this example, the payload is a dictionary of dict[str, Any].
        location_datas: list[dict[str, Any]] = payload.get("LocationDatas")

        # Validate data in the payload.
        for data in location_datas:
            if (postal_code := data.get("postalCode", None)) is None or postal_code == "":
                raise SapioWebserviceException("LocationDatas must contain a postalCode", 500)

        # Extract data from the params.
        store_data: bool = bool(params.get("TestRun", False))
        if store_data:
            api_request: PyRecordModel = self.inst_man.add_new_record("C_APIRequest")
            api_request.set_field_value("C_RequestJson", json.dumps(payload))

            self.rec_man.store_and_commit()

            # Return a web service result with a status code of 201 since we added/modified data in the database.
            return SapioWebserviceResult("Successfully processed request!", status_code=201)

        return SapioWebserviceResult("Successfully processed request!", status_code=200)
