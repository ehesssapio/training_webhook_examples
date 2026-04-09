"""
Receive Shipment — form / table toolbar webhook.

Sapio setup (App Setup → Manage Rules & Webhooks → Webhooks), two separate webhook definitions:
  1) Invocation: Data Record Form Toolbar — URL: ``{webhook-server-base}/receive-shipment`` — data type: Shipment.
  2) Invocation: Data Record Table Toolbar — same URL — data type: Shipment.

Data Designer checklist (tenant-specific — verify before production use):
  * Shipment has child type Sample (REST children query from Shipment record id → Sample).
  * Sample has child type SampleReceipt (receipt linked via ``sample.add_children([receipt])``).
  * Shipment fields: ``Status`` (picklist includes Pending / Completed), ``ReceivedBy`` (type compatible
    with ``SapioUser.username`` string — adjust if your field expects user record id / selection JSON).
  * Optional Shipment ``ReceivedDate`` — set when present on the type.
  * Sample ``ExemplarSampleStatus`` includes picklist entry for available samples (default literal ``Available``).
  * ``SampleReceipt`` field API names match those used in ``RECEIPT_TABLE_FIELDS`` / ``RECEIPT_APPLY_FIELDS`` below.

Already-received rule: a Shipment is treated as already received if ``Status`` is ``Completed`` OR
``ReceivedBy`` is non-empty. Only rows with ``Status == Pending`` (and not already received) are eligible.

Shipments with no child Samples are skipped for receiving (no receipts, not marked completed) and listed
in the result dialog.
"""
from __future__ import annotations

from typing import Any

from sapiopycommons.callbacks.callback_util import CallbackUtil
from sapiopycommons.general.exceptions import SapioUserErrorException
from sapiopycommons.general.time_util import TimeUtil
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.DataRecord import DataRecord
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from sapiopylib.rest.utils.autopaging import GetChildrenListAutoPager

from utilities.data_type_models import SampleModel, SampleReceiptModel

SHIPMENT_DATA_TYPE_NAME: str = "Shipment"

FIELD_DATA_RECORD_NAME: str = "DataRecordName"
FIELD_STATUS: str = "Status"
FIELD_RECEIVED_BY: str = "ReceivedBy"
FIELD_RECEIVED_DATE: str = "ReceivedDate"

STATUS_PENDING: str = "Pending"
STATUS_COMPLETED: str = "Completed"

SAMPLE_STATUS_AVAILABLE: str = "Available"

# Columns shown in the table entry dialog (API names on SampleReceipt).
RECEIPT_TABLE_FIELDS: list[str] = [
    "SampleId",
    "SampleReceivedRejected",
    "FailureComment",
    "RejectionReason",
    "Volume",
]

# Subset applied back to each SampleReceipt model after the dialog (editable receipt fields).
RECEIPT_APPLY_FIELDS: list[str] = [
    "SampleReceivedRejected",
    "FailureComment",
    "RejectionReason",
    "Volume",
]


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def _record_label(record: DataRecord) -> str:
    name = record.get_field_value(FIELD_DATA_RECORD_NAME)
    if not _is_blank(name):
        return str(name).strip()
    return f"{record.get_data_type_name()}:{record.get_record_id()}"


def _already_received(rec: DataRecord) -> bool:
    status = rec.get_field_value(FIELD_STATUS)
    if status == STATUS_COMPLETED:
        return True
    if not _is_blank(rec.get_field_value(FIELD_RECEIVED_BY)):
        return True
    return False


def _is_pending(rec: DataRecord) -> bool:
    return rec.get_field_value(FIELD_STATUS) == STATUS_PENDING


def _apply_field_maps_to_receipts(
    receipts: list[SampleReceiptModel],
    field_maps: list[dict[str, Any]],
) -> None:
    if len(field_maps) != len(receipts):
        raise SapioUserErrorException(
            f"Table dialog returned {len(field_maps)} row(s) for {len(receipts)} receipt(s); cannot apply edits."
        )
    for model, fm in zip(receipts, field_maps):
        for fn in RECEIPT_APPLY_FIELDS:
            if fn in fm:
                model.set_field_value(fn, fm[fn])


class ReceiveShipment(CommonsWebhookHandler):
    """Load child Samples, edit SampleReceipt rows in a table dialog, then commit shipment + samples + receipts."""

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not (self.is_form_toolbar() or self.is_table_toolbar()):
            raise SapioUserErrorException(
                "Receive Shipment must be invoked from the data record form or table toolbar."
            )

        selected = _selected_records(context)
        shipments: list[DataRecord] = []
        not_shipment: list[DataRecord] = []
        for rec in selected:
            if rec.get_data_type_name() == SHIPMENT_DATA_TYPE_NAME:
                shipments.append(rec)
            else:
                not_shipment.append(rec)

        not_pending: list[DataRecord] = []
        already_received_list: list[DataRecord] = []
        eligible: list[DataRecord] = []

        for rec in shipments:
            if _already_received(rec):
                already_received_list.append(rec)
            elif not _is_pending(rec):
                not_pending.append(rec)
            else:
                eligible.append(rec)

        no_samples: list[DataRecord] = []
        receiving_shipments: list[DataRecord] = []
        sample_records: list[DataRecord] = []

        if eligible:
            parent_ids = [s.record_id for s in eligible]
            child_map = GetChildrenListAutoPager(
                parent_ids, SampleModel.DATA_TYPE_NAME, self.user
            ).get_all_at_once()

            for sh in eligible:
                kids = sorted(child_map.get(sh.record_id), key=lambda r: r.record_id)
                if not kids:
                    no_samples.append(sh)
                else:
                    receiving_shipments.append(sh)
                    sample_records.extend(kids)

        receipts: list[SampleReceiptModel] = []
        if sample_records:
            if not self.can_send_client_callback():
                raise SapioUserErrorException(
                    "Receive Shipment requires a client callback to show the receipt table dialog."
                )

            now_ms = TimeUtil.now_in_millis()
            received_by = self.user.username

            sample_models: list[SampleModel] = self.inst_man.add_existing_records_of_type(
                sample_records, SampleModel
            )

            for sample in sample_models:
                receipt: SampleReceiptModel = self.inst_man.add_new_record_of_type(SampleReceiptModel)
                sid = sample.get_SampleId_field()
                receipt.set_SampleId_field(sid)
                receipt.set_OtherSampleId_field(sample.get_OtherSampleId_field())
                receipt.set_ExemplarSampleType_field(sample.get_ExemplarSampleType_field())
                receipt.set_Volume_field(sample.get_Volume_field())
                receipt.set_ReceivedDate_field(now_ms)
                receipt.set_ReceivedBy_field(received_by)
                sample.add_children([receipt])
                receipts.append(receipt)

            callback = CallbackUtil(context)
            field_maps = callback.record_table_dialog(
                "Receive shipment — sample receipts",
                "<p>Edit receipt details for each sample, then confirm to complete receiving.</p>",
                RECEIPT_TABLE_FIELDS,
                receipts,
            )
            _apply_field_maps_to_receipts(receipts, field_maps)

            for sample in sample_models:
                sample.set_ExemplarSampleStatus_field(SAMPLE_STATUS_AVAILABLE)

            shipment_fields = self.dt_cache.get_fields_for_type(SHIPMENT_DATA_TYPE_NAME)
            set_shipment_received_date = FIELD_RECEIVED_DATE in shipment_fields

            for sh in receiving_shipments:
                sm = self.inst_man.add_existing_record(sh)
                sm.set_field_value(FIELD_STATUS, STATUS_COMPLETED)
                sm.set_field_value(FIELD_RECEIVED_BY, received_by)
                if set_shipment_received_date:
                    sm.set_field_value(FIELD_RECEIVED_DATE, now_ms)

            self.rec_man.store_and_commit()

        if self.can_send_client_callback():
            msg = _build_summary_html(
                received_shipment_count=len(receiving_shipments),
                receipt_count=len(receipts),
                not_shipment=not_shipment,
                already_received_list=already_received_list,
                not_pending=not_pending,
                no_samples=no_samples,
            )
            CallbackUtil(context).ok_dialog("Receive shipment — result", msg)

        toaster = (
            f"Received {len(receiving_shipments)} shipment(s), {len(receipts)} sample receipt(s)."
            if receiving_shipments
            else None
        )
        return SapioWebhookResult(True, toaster)


def _selected_records(context: SapioWebhookContext) -> list[DataRecord]:
    rows = context.data_record_list
    if rows:
        return list(rows)
    if context.data_record is not None:
        return [context.data_record]
    raise SapioUserErrorException("No shipment record was selected.")


def _build_summary_html(
    received_shipment_count: int,
    receipt_count: int,
    not_shipment: list[DataRecord],
    already_received_list: list[DataRecord],
    not_pending: list[DataRecord],
    no_samples: list[DataRecord],
) -> str:
    parts: list[str] = []
    parts.append(
        f"<p><b>Completed receiving:</b> {received_shipment_count} shipment(s), "
        f"{receipt_count} sample receipt(s).</p>"
    )
    if not_shipment:
        lines = "<br/>".join(_record_label(r) for r in not_shipment)
        parts.append(f"<p><b>Skipped (not Shipment data type):</b><br/>{lines}</p>")
    if already_received_list:
        lines = "<br/>".join(_record_label(r) for r in already_received_list)
        parts.append(f"<p><b>Skipped (already received or completed):</b><br/>{lines}</p>")
    if not_pending:
        lines = "<br/>".join(_record_label(r) for r in not_pending)
        parts.append(f"<p><b>Skipped (status not Pending):</b><br/>{lines}</p>")
    if no_samples:
        lines = "<br/>".join(_record_label(r) for r in no_samples)
        parts.append(f"<p><b>Skipped (no child Samples under shipment):</b><br/>{lines}</p>")
    if received_shipment_count == 0 and not any(
        (not_shipment, already_received_list, not_pending, no_samples)
    ):
        parts.append("<p>No shipments were eligible to receive.</p>")
    return "".join(parts)
