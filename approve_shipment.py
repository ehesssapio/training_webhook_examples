"""
Approve Shipment — form / table toolbar webhook.

Sapio setup (App Setup → Manage Rules & Webhooks → Webhooks), two separate webhook definitions:
  1) Invocation: Data Record Form Toolbar — URL: ``{webhook-server-base}/approve-shipment`` — data type: Shipment.
  2) Invocation: Data Record Table Toolbar — same URL — data type: Shipment.

Field API names in this module must match Data Designer for your tenant (defaults are conventional Velox names).
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

# Data type name exactly as in Data Designer.
SHIPMENT_DATA_TYPE_NAME: str = "Shipment"

# API field names — align with your Shipment type in Data Designer.
FIELD_ASSIGNED_APPROVER: str = "AssignedApprover"
FIELD_APPROVED_BY: str = "ApprovedBy"
FIELD_APPROVAL_DATE: str = "ApprovalDate"
# Used for human-readable lists in the summary dialog when present.
FIELD_DATA_RECORD_NAME: str = "DataRecordName"


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


def _normalize_assigned_approver_for_compare(
    value: Any,
    signer_username: str,
    signer_user_record_id: int | None,
) -> bool:
    """
    True if the stored Assigned Approver value designates the same user as the e-sign signer.
    Handles username string, user record id, or common JSON-shaped user references.
    """
    if _is_blank(value):
        return False
    if isinstance(value, str):
        return value.strip() == signer_username
    if isinstance(value, int):
        return signer_user_record_id is not None and value == signer_user_record_id
    if isinstance(value, dict):
        u = value.get("username") or value.get("userName")
        if u is not None and str(u).strip() == signer_username:
            return True
        for key in ("userRecordId", "recordId", "userId", "id"):
            rid = value.get(key)
            if rid is not None and signer_user_record_id is not None:
                try:
                    if int(rid) == signer_user_record_id:
                        return True
                except (TypeError, ValueError):
                    pass
        return False
    return False


class ApproveShipment(CommonsWebhookHandler):
    """E-sign then set Approved By / Approval Date on Shipment rows the signer is allowed to approve."""

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not (self.is_form_toolbar() or self.is_table_toolbar()):
            raise SapioUserErrorException(
                "Approve Shipment must be invoked from the data record form or table toolbar."
            )

        selected = _selected_records(context)
        shipments: list[DataRecord] = []
        not_shipment: list[DataRecord] = []
        for rec in selected:
            if rec.get_data_type_name() == SHIPMENT_DATA_TYPE_NAME:
                shipments.append(rec)
            else:
                not_shipment.append(rec)

        missing_approver: list[DataRecord] = []
        already_approved: list[DataRecord] = []
        pending: list[DataRecord] = []

        for rec in shipments:
            assigned = rec.get_field_value(FIELD_ASSIGNED_APPROVER)
            approved_by = rec.get_field_value(FIELD_APPROVED_BY)
            if _is_blank(assigned):
                missing_approver.append(rec)
            elif not _is_blank(approved_by):
                already_approved.append(rec)
            else:
                pending.append(rec)

        eligible: list[DataRecord] = []
        wrong_assignee: list[DataRecord] = []
        signer_username: str | None = None

        if pending:
            if not self.can_send_client_callback():
                raise SapioUserErrorException(
                    "Electronic signature requires a client callback; this invocation cannot show the e-sign dialog."
                )
            callback = CallbackUtil(context)
            esign = callback.esign_dialog(
                "Approve shipment",
                "<p>Authenticate to approve the selected shipment(s) pending your review.</p>",
                show_comment=True,
            )
            user_info = esign.user_info
            if user_info is None:
                raise SapioUserErrorException("E-sign completed but user information was not returned.")
            signer_username = user_info.username
            signer_rid = user_info.user_record_id
            for rec in pending:
                assigned = rec.get_field_value(FIELD_ASSIGNED_APPROVER)
                if _normalize_assigned_approver_for_compare(assigned, signer_username, signer_rid):
                    eligible.append(rec)
                else:
                    wrong_assignee.append(rec)

        if eligible:
            now_ms = TimeUtil.now_in_millis()
            assert signer_username is not None
            for rec in eligible:
                rec.set_field_value(FIELD_APPROVED_BY, signer_username)
                rec.set_field_value(FIELD_APPROVAL_DATE, now_ms)
            self.dr_man.commit_data_records(eligible)

        if self.can_send_client_callback():
            msg = _build_summary_html(
                approved_count=len(eligible),
                not_shipment=not_shipment,
                missing_approver=missing_approver,
                already_approved=already_approved,
                wrong_assignee=wrong_assignee,
            )
            CallbackUtil(context).ok_dialog("Approve shipment — result", msg)

        toaster = f"Approved {len(eligible)} shipment(s)." if eligible else None
        return SapioWebhookResult(True, toaster)


def _selected_records(context: SapioWebhookContext) -> list[DataRecord]:
    rows = context.data_record_list
    if rows:
        return list(rows)
    if context.data_record is not None:
        return [context.data_record]
    raise SapioUserErrorException("No shipment record was selected.")


def _build_summary_html(
    approved_count: int,
    not_shipment: list[DataRecord],
    missing_approver: list[DataRecord],
    already_approved: list[DataRecord],
    wrong_assignee: list[DataRecord],
) -> str:
    parts: list[str] = []
    parts.append(f"<p><b>Approved:</b> {approved_count} shipment(s).</p>")
    if not_shipment:
        lines = "<br/>".join(_record_label(r) for r in not_shipment)
        parts.append(f"<p><b>Skipped (not Shipment data type):</b><br/>{lines}</p>")
    if missing_approver:
        lines = "<br/>".join(_record_label(r) for r in missing_approver)
        parts.append(f"<p><b>Missing assigned approver:</b><br/>{lines}</p>")
    if already_approved:
        lines = "<br/>".join(_record_label(r) for r in already_approved)
        parts.append(f"<p><b>Already approved:</b><br/>{lines}</p>")
    if wrong_assignee:
        lines = "<br/>".join(_record_label(r) for r in wrong_assignee)
        parts.append(
            f"<p><b>Assigned to another user (signer does not match assigned approver):</b><br/>{lines}</p>"
        )
    if approved_count == 0 and not any(
        (not_shipment, missing_approver, already_approved, wrong_assignee)
    ):
        parts.append("<p>No shipments were pending approval.</p>")
    return "".join(parts)
