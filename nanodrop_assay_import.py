"""
Nanodrop upload → AssayResult import (ELN webhook).

Sapio setup (App Setup → Manage Rules & Webhooks → Webhooks):

  * **Primary:** Invocation **Velox ELN Rule Action** — URL ``{webhook-server-base}/nanodrop-assay-import``.
    Scope the rule to the workflow/template so it runs when the **Nanodrop Upload** attachment entry is submitted
    (exact rule trigger names depend on your Sapio version).

  * **Alternate:** Invocation **Notebook Experiment Entry Toolbar** — same URL — users can run import manually from
    the entry toolbar.

The handler runs only when ``experiment_entry.entry_name`` is exactly ``Nanodrop Upload``. Other invocations on the
same URL return success without changes.

Prerequisites (tenant-specific):

  * Experiment template includes an attachment entry named **Nanodrop Upload** with a Nanodrop ``.txt`` (tab-separated).
  * A table entry named **Samples** on the same experiment with Sample records whose ``SampleId`` matches the file.
  * Data type **AssayResult** is a child of **Sample** with fields: ``SampleId``, ``MeasurementName``,
    ``MeasurementTextResult``, ``MeasurementNumericResult``.
"""
from __future__ import annotations

import re
from typing import Any, cast

from sapiopycommons.datatype.attachment_util import AttachmentUtil
from sapiopycommons.general.aliases import AliasUtil
from sapiopycommons.general.exceptions import SapioUserErrorException
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.pojo.DataRecord import DataRecord
from sapiopylib.rest.pojo.TableColumn import TableColumn
from sapiopylib.rest.pojo.eln.ExperimentEntry import (
    EntryRecordAttachment,
    EntryStaticAttachment,
    ExperimentAttachmentEntry,
    ExperimentEntry,
)
from sapiopylib.rest.pojo.eln.ExperimentEntryCriteria import ElnTableEntryCriteria
from sapiopylib.rest.pojo.eln.SapioELNEnums import ElnEntryType
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from sapiopylib.rest.utils.autopaging import GetElnEntryRecordAutoPager
from sapiopylib.rest.utils.recordmodel.RecordModelManager import RecordModelInstanceManager
from sapiopylib.rest.utils.recordmodel.PyRecordModel import PyRecordModel
from sapiopylib.rest.utils.recordmodel.properties import Child

from utilities.data_type_models import SampleModel

NANODROP_ENTRY_NAME: str = "Nanodrop Upload"
SAMPLES_ENTRY_NAME: str = "Samples"
RESULT_TABLE_ENTRY_NAME: str = "Nanodrop assay results"
ASSAY_RESULT_TYPE: str = "AssayResult"
ATTACHMENT_TYPE: str = "Attachment"

# Identity columns (normalized header → not emitted as measurements)
_IDENTITY_NORMALIZED: frozenset[str] = frozenset({"plate id", "well", "sample id", "sampleid"})

_WELL_PATTERN = re.compile(r"^[A-Ha-h]\d{1,2}$")
_PLACEHOLDER_SAMPLE = re.compile(r"<!--\s*sampleid\s*-->", re.IGNORECASE)


def _norm_header(h: str) -> str:
    return " ".join(h.strip().split()).lower()


def _decode_text(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1", errors="replace")


def _detect_delimiter(first_line: str) -> str:
    if "\t" in first_line:
        return "\t"
    return ","


def _split_row(line: str, delimiter: str) -> list[str]:
    if delimiter == "\t":
        return line.split("\t")
    return line.split(",")


def _plate_like_first_header(headers_norm: list[str]) -> bool:
    return bool(headers_norm) and headers_norm[0] in ("plate id", "plateid")


def _align_row_cells(headers_norm: list[str], raw_cells: list[str]) -> list[str]:
    """
    If the template has Plate ID but data rows omit the plate column (first cell is Well, not empty), prepend
    an empty plate cell so columns align with headers.
    """
    cells = list(raw_cells)
    if not _plate_like_first_header(headers_norm):
        return cells
    if not cells:
        return cells
    first = cells[0].strip()
    if not first:
        return cells
    if _WELL_PATTERN.match(first) and len(headers_norm) >= 2 and headers_norm[1] == "well":
        return [""] + cells
    return cells


def _parse_numeric_or_text(raw: str) -> tuple[float | None, str | None]:
    s = raw.strip()
    if not s:
        return None, None
    try:
        v = float(s)
        if v != v:  # NaN
            return None, s
        return v, None
    except ValueError:
        return None, s


def _collect_attachment_record_ids(entry: ExperimentEntry) -> tuple[list[int], list[str]]:
    warnings: list[str] = []
    ids: list[int] = []
    seen: set[int] = set()
    if entry.entry_type != ElnEntryType.Attachment:
        return ids, warnings
    att = cast(ExperimentAttachmentEntry, entry)
    if att.entry_attachment_list:
        for item in att.entry_attachment_list:
            if isinstance(item, EntryStaticAttachment):
                warnings.append(
                    "A static template attachment was skipped (only record-backed attachments can be read)."
                )
            elif isinstance(item, EntryRecordAttachment) and item.record_id is not None and item.record_id > 0:
                if item.record_id not in seen:
                    seen.add(item.record_id)
                    ids.append(item.record_id)
    if att.record_id is not None and att.record_id > 0 and att.record_id not in seen:
        ids.insert(0, att.record_id)
    return ids, warnings


def _load_nanodrop_text(context: SapioWebhookContext, entry: ExperimentEntry) -> tuple[str, list[str]]:
    warnings: list[str] = []
    record_ids, w = _collect_attachment_record_ids(entry)
    warnings.extend(w)
    if not record_ids:
        raise SapioUserErrorException(
            "No record-backed attachment was found on this entry. Upload a file to the Nanodrop Upload attachment."
        )
    chunks: list[str] = []
    for rid in record_ids:
        dr = context.data_record_manager.query_system_for_record(ATTACHMENT_TYPE, rid)
        if dr is None:
            warnings.append(f"Attachment record id {rid} was not found; skipped.")
            continue
        if dr.get_data_type_name() != ATTACHMENT_TYPE:
            warnings.append(f"Record {rid} is not an Attachment; skipped.")
            continue
        try:
            data = AttachmentUtil.get_attachment_bytes(context, dr)
        except Exception as ex:  # noqa: BLE001 — surface as warning, continue other attachments
            warnings.append(f"Could not read attachment record {rid}: {ex!s}.")
            continue
        chunks.append(_decode_text(data))
    if not chunks:
        raise SapioUserErrorException(
            "Could not read any attachment bytes. Check that a file is uploaded and permissions are correct."
        )
    if len(chunks) > 1:
        warnings.append(f"Multiple attachments ({len(chunks)}) were concatenated in order for parsing.")
    return "\n".join(chunks), warnings


def _parse_table(text: str) -> tuple[list[str], list[list[str]], int, list[str]]:
    warnings: list[str] = []
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise SapioUserErrorException("The attachment file is empty.")
    delimiter = _detect_delimiter(lines[0])
    header_cells = [c.strip() for c in _split_row(lines[0], delimiter)]
    headers_norm = [_norm_header(h) for h in header_cells]

    try:
        sample_idx = next(i for i, h in enumerate(headers_norm) if h in ("sample id", "sampleid"))
    except StopIteration:
        raise SapioUserErrorException(
            'No "Sample ID" (or SampleId) column found in the file header row.'
        ) from None

    seen_measurement: set[str] = set()
    duplicate_headers: list[str] = []
    for i, hn in enumerate(headers_norm):
        if i == sample_idx or hn in _IDENTITY_NORMALIZED:
            continue
        if hn in seen_measurement:
            duplicate_headers.append(header_cells[i])
        seen_measurement.add(hn)
    if duplicate_headers:
        warnings.append(
            "Duplicate measurement column names after normalization (first occurrence kept): "
            + ", ".join(sorted(set(duplicate_headers)))
        )

    data_rows: list[list[str]] = []
    for line in lines[1:]:
        raw = _split_row(line, delimiter)
        aligned = _align_row_cells(headers_norm, raw)
        if len(aligned) < len(header_cells):
            aligned = aligned + [""] * (len(header_cells) - len(aligned))
        elif len(aligned) > len(header_cells):
            aligned = aligned[: len(header_cells)]
        data_rows.append(aligned)

    return header_cells, data_rows, sample_idx, warnings


def _build_sample_map(
    context: SapioWebhookContext,
    inst_man: RecordModelInstanceManager,
    exp_id: int,
    warnings: list[str],
) -> dict[str, SampleModel]:
    eln = context.eln_manager
    entries = eln.get_experiment_entry_list(exp_id)
    by_name = {e.entry_name: e for e in entries}
    samples_entry = by_name.get(SAMPLES_ENTRY_NAME)
    if samples_entry is None:
        raise SapioUserErrorException(
            f'No experiment entry named "{SAMPLES_ENTRY_NAME}" was found; cannot resolve Sample IDs.'
        )
    pager = GetElnEntryRecordAutoPager(exp_id, samples_entry.entry_id, context.user)
    sample_records = pager.get_all_at_once()
    if not sample_records:
        warnings.append(f'The "{SAMPLES_ENTRY_NAME}" entry has no sample records.')
    models: list[SampleModel] = inst_man.add_existing_records_of_type(sample_records, SampleModel)
    out: dict[str, SampleModel] = {}
    for m in models:
        sid = m.get_SampleId_field()
        if sid is not None and str(sid).strip():
            out[str(sid).strip()] = m
    return out


def _next_entry_order(entries: list[ExperimentEntry], tab_id: int | None) -> int:
    same_tab = [e for e in entries if e.notebook_experiment_tab_id == tab_id]
    if not same_tab:
        return 100
    return max(e.order for e in same_tab) + 10


class NanodropAssayImport(CommonsWebhookHandler):
    """Parse Nanodrop text from the Nanodrop Upload attachment entry and create AssayResult children + results table."""

    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        if not (self.is_eln_rule() or self.is_eln_entry_toolbar()):
            raise SapioUserErrorException(
                "Nanodrop assay import must run from a Velox ELN Rule Action or an experiment entry toolbar."
            )
        if context.eln_experiment is None:
            raise SapioUserErrorException("No notebook experiment in context.")
        entry = context.experiment_entry
        if entry is None or entry.entry_name != NANODROP_ENTRY_NAME:
            return SapioWebhookResult(True, "Nanodrop import skipped (not the Nanodrop Upload entry).")

        if entry.entry_type != ElnEntryType.Attachment:
            raise SapioUserErrorException(
                f'Entry "{NANODROP_ENTRY_NAME}" must be an attachment entry (found {entry.entry_type}).'
            )

        warnings: list[str] = []
        text, w_attach = _load_nanodrop_text(context, entry)
        warnings.extend(w_attach)

        header_cells, data_rows, sample_col, w_parse = _parse_table(text)
        warnings.extend(w_parse)
        headers_norm = [_norm_header(h) for h in header_cells]

        exp_id = context.eln_experiment.notebook_experiment_id
        sample_by_id = _build_sample_map(context, self.inst_man, exp_id, warnings)

        measurement_indices: list[int] = []
        for i, hn in enumerate(headers_norm):
            if i == sample_col:
                continue
            if hn in _IDENTITY_NORMALIZED:
                continue
            # skip duplicate measurement columns (keep first index only)
            name = header_cells[i].strip()
            if not name:
                continue
            first_i = next((j for j, h in enumerate(headers_norm) if header_cells[j].strip() == name), i)
            if first_i != i:
                continue
            measurement_indices.append(i)

        skipped_blank_sample = 0
        skipped_placeholder_rows = 0
        skipped_unknown_sample = 0
        unknown_sample_ids: set[str] = set()
        skipped_empty_measurements = 0
        assay_models: list[PyRecordModel] = []

        for row in data_rows:
            sid_raw = row[sample_col].strip() if sample_col < len(row) else ""
            if not sid_raw:
                skipped_blank_sample += 1
                continue
            if _PLACEHOLDER_SAMPLE.search(sid_raw):
                skipped_placeholder_rows += 1
                continue
            sample = sample_by_id.get(sid_raw)
            if sample is None:
                skipped_unknown_sample += 1
                unknown_sample_ids.add(sid_raw)
                continue

            for mi in measurement_indices:
                cell = row[mi] if mi < len(row) else ""
                if not str(cell).strip():
                    skipped_empty_measurements += 1
                    continue
                num, txt = _parse_numeric_or_text(str(cell))
                ar: PyRecordModel = sample.add(Child.create_by_name(ASSAY_RESULT_TYPE))
                mname = header_cells[mi].strip()
                fv: dict[str, Any] = {
                    "MeasurementName": mname,
                }
                if num is not None:
                    fv["MeasurementNumericResult"] = num
                    fv["MeasurementTextResult"] = None
                else:
                    fv["MeasurementNumericResult"] = None
                    fv["MeasurementTextResult"] = txt
                sid_val = sample.get_SampleId_field()
                if sid_val is not None:
                    fv["SampleId"] = sid_val
                ar.set_field_values(fv)
                assay_models.append(ar)

        if skipped_blank_sample:
            warnings.append(f"Skipped {skipped_blank_sample} row(s) with blank Sample ID.")
        if skipped_placeholder_rows:
            warnings.append(
                f"Skipped {skipped_placeholder_rows} row(s) with placeholder Sample ID (e.g. <!-- SampleId -->)."
            )
        if skipped_unknown_sample:
            preview = ", ".join(sorted(unknown_sample_ids)[:12])
            more = "…" if len(unknown_sample_ids) > 12 else ""
            warnings.append(
                f"Skipped {skipped_unknown_sample} row(s): Sample ID not found in {SAMPLES_ENTRY_NAME} "
                f"({preview}{more})."
            )
        if skipped_empty_measurements:
            warnings.append(
                f"Skipped {skipped_empty_measurements} empty measurement cell(s) (no AssayResult created for those)."
            )

        if not assay_models:
            summary = "No AssayResult records were created."
            if warnings:
                summary += " See warnings."
            return SapioWebhookResult(True, display_text=summary, list_values=warnings or None)

        self.rec_man.store_and_commit()

        criteria = ElnTableEntryCriteria(RESULT_TABLE_ENTRY_NAME, ASSAY_RESULT_TYPE, _next_entry_order(
            context.eln_manager.get_experiment_entry_list(exp_id),
            entry.notebook_experiment_tab_id,
        ))
        criteria.notebook_experiment_tab_id = entry.notebook_experiment_tab_id
        criteria.table_column_list = [
            TableColumn(ASSAY_RESULT_TYPE, "SampleId"),
            TableColumn(ASSAY_RESULT_TYPE, "MeasurementName"),
            TableColumn(ASSAY_RESULT_TYPE, "MeasurementTextResult"),
            TableColumn(ASSAY_RESULT_TYPE, "MeasurementNumericResult"),
        ]
        criteria.show_key_fields = True

        new_entry = context.eln_manager.add_experiment_entry(exp_id, criteria)
        dr_list = [AliasUtil.to_data_record(m) for m in assay_models]
        context.eln_manager.add_records_to_table_entry(exp_id, new_entry.entry_id, dr_list)

        summary = f"Created {len(assay_models)} AssayResult record(s) and table entry {RESULT_TABLE_ENTRY_NAME!r}."
        return SapioWebhookResult(
            True,
            display_text=summary,
            list_values=warnings if warnings else None,
            refresh_notebook_experiment=True,
            eln_entry_refresh_list=[new_entry],
        )
