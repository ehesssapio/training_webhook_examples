# Webhook Development Examples Project
This project contains a series of Sapio webhook examples that utilize our official Python libraries, sapiopylib and
sapiopycommons. Start with the files in the `examples` folder (e.g. `A_webhook_handlers.py` through
`D_handling_experiments.py`) in alphabetical order. **`examples/mcp_examples`** holds extended demos that mirror
many Java examples; import them as `examples.mcp_examples.<module>` or call them via the URLs registered in `server.py`.
Hands-on scratch work lives under **`exercises/`** (e.g. `exercises/practice`, `exercises/training_event`).

Note that the example webhooks are designed to teach the fundamentals of using our Python libraries to write webhooks
for a Sapio system. This means that they are not necessarily designed as functional webhooks if you were to register
an endpoint for them and run them from within the system.

### Prerequisites
Install the following:
* [Python 3.10](https://www.python.org/downloads/release/python-31011/)
* The Python packages in requirements.txt
  * For sapiopylib and sapiopycommons, visit our PyPI pages (linked below) to ensure that you are grabbing the 
    latest compatible library versions for your Sapio system's version.

Sapio utilizes [PyCharm](https://www.jetbrains.com/pycharm/) as our Python IDE. Some comments will include tips that 
reference key shortcuts or behaviors in PyCharm. Behavior may be different if you are using another IDE.

### MCP / extended examples (`examples/mcp_examples`)
`server.py` registers handlers in this folder automatically by **scanning** `examples/mcp_examples/*.py` for concrete
subclasses of Sapio’s `AbstractWebhookHandler` (see `webhook_registry.py`). The **HTTP path is not the folder name**:
use **`mcp-examples`** (hyphens), not `mcp_examples`, and **kebab-case** for the module stem (underscores in the
filename become hyphens). Example: module `table_dialog_example.py` → URL path **`/mcp-examples/table-dialog-example`**
(full URL: `https://<your-ngrok-host>/mcp-examples/table-dialog-example`). Endpoints accept **POST** only (Sapio calls
them); opening that URL in a browser with GET often returns 404 or 405.

Typical patterns: **`/mcp-examples/<kebab-module-name>`**; a module with more than one handler uses
**`/mcp-examples/<module>--<kebab-class-name>`** unless listed in `_PATH_OVERRIDES` (e.g. `simple-cdl-example`).

### Testing Locally
Webhooks can be tested locally by spinning up a webhook server within your IDE. Run the server.py file to start a
webhook server on your localhost port defined by the "port" variable at the bottom of the file.
In order to have Sapio make requests to your defined webhook endpoints, you will need to make your localhost port
available to the Sapio server.

If your local machine is on a separate network, you will need to use a tunneling/port forwarding service to make your
webhooks available to the Sapio server. Sapio's developers currently utilize [ngrok](https://ngrok.com/) for this
purpose. Once installed, you can run `ngrok http 8091` from a terminal to start an ngrok instance (use the same port as
the `port` variable at the bottom of `server.py`, currently **8091**). The final value in
the command is the port that the ngrok instance will make available, which should match the port in the server.py file.
Going to http://localhost:4040 in your browser while an ngrok instance is running will allow you to review the requests
that the Sapio server makes to your webhook server, including displaying the JSON of the requests. This can be a useful
tool for understanding what Sapio is sending for the context of a particular endpoint. 

If your local machine is on the same network as the Sapio server, contact your IT team about making your local device's
IP available to the Sapio server.

#### HTTPS / self-signed certificates
By default, `server.py` sets `verify_sapio_cert` to **off** so local training against Sapio with self-signed (or private CA)
HTTPS works without setting environment variables in your IDE.

For production—or whenever Sapio presents a certificate trusted by public CAs—set **`SapioWebhooksVerifySsl`** to `true`,
`1`, or `yes` before starting the server. The included **Dockerfile** sets `SapioWebhooksVerifySsl=true` so container
deployments verify TLS by default.

Legacy: `SapioWebhooksInsecure` or `SapioWebhooksAllowSelfSigned` still force verification **off** when
`SapioWebhooksVerifySsl` is not enabled (they are ignored if `SapioWebhooksVerifySsl` is true).

When verification is off, sapiopylib logs a security warning when building the `SapioUser` client; that is expected.

#### Local debug server
To run Flask's built-in server with debug mode instead of Waitress, set `SapioWebhooksDebug` to `true`, `1`, or `yes`.

### Deploying Webhooks
This project contains a Dockerfile that can be used to build this project into a Docker image. This Docker image can 
then be deployed to your service of choice to run a webhook server with a permanent URL that the Sapio system can 
access.

### Resources

* [sapiopylib](https://pypi.org/project/sapiopylib/): Our PyPI page for all sapiopylib releases.
* [sapiopycommons](https://pypi.org/project/sapiopycommons/): Our PyPI page for all sapiopycommons releases.
* [Sapio Py Tutorials](https://github.com/sapiosciences/sapio-py-tutorials): Our GitHub repository containing further 
information and examples for sapiopylib.