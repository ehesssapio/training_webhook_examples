"""
Register every webhook / webservice handler defined under ``examples/mcp_examples``.

Modules ``__init__`` and ``webhook_registry`` are skipped. Each ``*.py`` file is imported; every **concrete**
subclass of :class:`~sapiopylib.rest.WebhookService.AbstractWebhookHandler` **defined in that module** is
registered.

URL rules:

* One handler in the module → ``/mcp-examples/<kebab-module-stem>`` (e.g. ``accession_manager_example`` →
  ``/mcp-examples/accession-manager-example``).
* Several handlers in one module → ``/mcp-examples/<kebab-module-stem>--<kebab-class-name>``, except entries in
  ``_PATH_OVERRIDES`` (keeps stable URLs for ``complex_data_loader_example``).

:mod:`server` calls :func:`register_mcp_example_webhooks` at startup.
"""

from __future__ import annotations

import inspect
import re
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Type

from sapiopylib.rest.WebhookService import AbstractWebhookHandler

if TYPE_CHECKING:
    from sapiopylib.rest.WebhookService import WebhookConfiguration

# (module stem without package, handler class name) -> exact URL path (only where multiple handlers share a module
# and we want short, stable paths).
_PATH_OVERRIDES: dict[tuple[str, str], str] = {
    ("complex_data_loader_example", "ComplexDataLoaderExample"): "/mcp-examples/complex-data-loader-example",
    ("complex_data_loader_example", "SimpleCDLExample"): "/mcp-examples/simple-cdl-example",
}


def _class_kebab(name: str) -> str:
    x = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", name)
    x = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", x)
    return x.lower().replace("_", "-")


def _handlers_defined_in_module(module) -> list[Type[AbstractWebhookHandler]]:
    found: list[Type[AbstractWebhookHandler]] = []
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if obj.__module__ != module.__name__:
            continue
        if not issubclass(obj, AbstractWebhookHandler):
            continue
        if inspect.isabstract(obj):
            continue
        found.append(obj)
    return sorted(found, key=lambda c: c.__name__)


def _url_for_handler(module_stem: str, cls: Type[AbstractWebhookHandler], module_handlers: list[type]) -> str:
    key = (module_stem, cls.__name__)
    if key in _PATH_OVERRIDES:
        return _PATH_OVERRIDES[key]
    base = "/mcp-examples/" + module_stem.replace("_", "-")
    if len(module_handlers) == 1:
        return base
    return base + "--" + _class_kebab(cls.__name__)


def _discover_registrations() -> list[tuple[str, Type[AbstractWebhookHandler]]]:
    pkg_dir = Path(__file__).resolve().parent
    rows: list[tuple[str, Type[AbstractWebhookHandler]]] = []
    for path in sorted(pkg_dir.glob("*.py")):
        stem = path.stem
        if stem in ("__init__", "webhook_registry"):
            continue
        mod = import_module(f"examples.mcp_examples.{stem}")
        handlers = _handlers_defined_in_module(mod)
        for cls in handlers:
            url = _url_for_handler(stem, cls, handlers)
            rows.append((url, cls))
    by_url: dict[str, Type[AbstractWebhookHandler]] = {}
    for url, cls in rows:
        if url in by_url:
            raise ValueError(
                f"Duplicate MCP example URL {url!r}: {by_url[url].__name__} and {cls.__name__}. "
                "Adjust _PATH_OVERRIDES or rename a handler."
            )
        by_url[url] = cls
    return sorted(rows, key=lambda t: t[0])


def register_mcp_example_webhooks(config: WebhookConfiguration) -> None:
    """
    Attach every discovered MCP example handler to ``config``.

    :param config: The same configuration object passed to
        :func:`~sapiopylib.rest.WebhookService.WebhookServerFactory.configure_flask_app`.
    """
    for url_path, handler_cls in _discover_registrations():
        config.register(url_path, handler_cls)
