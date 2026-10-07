# Connect DY Studio through MCP

This is a **local stdio MCP server**, launched by your desktop AI client. It exposes the same models and job queue as the browser app. It does not add a chat LLM to DY Studio. The connected AI client supplies the reasoning and calls the creative tools.

## 1. Install the bridge

Download/extract the repository, install Python 3.11 or later and Git, then double-click `INSTALL_MCP.bat`. It creates `.mcp-venv/` and installs the pinned official MCP SDK. It does not install model weights or change the global Python environment.

Alternatively, from the repository root:

```powershell
python -m venv .mcp-venv
.\.mcp-venv\Scripts\python.exe -m pip install -r requirements-mcp.txt
```

Install the models you want in the browser's **Model management** screen. An AI can also call `studio_install_model`, but installations can download many gigabytes and should be explicitly approved by the user.

## 2. Configure your AI client

Replace **every** `C:/Apps/DY-Studio` below with your actual extracted folder. Use absolute paths; keep spaces inside quoted strings. No DY Studio API key is required.

### Codex desktop / CLI

Add this entry to your personal `~/.codex/config.toml` (on Windows, `%USERPROFILE%\.codex\config.toml`). Keep other existing MCP entries:

```toml
[mcp_servers.dy_studio]
command = "C:/Apps/DY-Studio/.mcp-venv/Scripts/python.exe"
args = ["C:/Apps/DY-Studio/mcp_server.py", "--start-studio"]
startup_timeout_sec = 30
tool_timeout_sec = 60
```

Restart/reconnect the client or start a new session so it loads the configuration. Ask it to call `studio_status` and check that five models are listed. See the [official Codex MCP documentation](https://developers.openai.com/codex/mcp) for configuration and tool permissions.

### Desktop clients with `mcpServers` JSON settings

Use your client's documented MCP configuration screen/file. Merge this entry with existing settings:

```json
{
  "mcpServers": {
    "dy-studio": {
      "command": "C:/Apps/DY-Studio/.mcp-venv/Scripts/python.exe",
      "args": ["C:/Apps/DY-Studio/mcp_server.py", "--start-studio"]
    }
  }
}
```

Only clients that support launching local stdio MCP processes can use this configuration directly. A cloud-only client cannot run this local executable. The browser UI at `http://127.0.0.1:8768/` is **not** a Streamable HTTP MCP endpoint.

## 3. Use the tools

| Tool | Purpose |
| --- | --- |
| `studio_status` | Five models, installation/license state, GPU and disk space |
| `studio_install_model` | Queue an explicitly approved model install/reinstall |
| `studio_upload_image` | Upload supplied image bytes as base64; returns an upload ID |
| `studio_generate` | Queue image/music/video/3D/background-removal generation |
| `studio_list_jobs` | Recent jobs, up to 100 |
| `studio_get_job` | Progress/status for a returned job ID |
| `studio_cancel_job` | Cancel a queued or running job |
| `studio_get_results` | Recorded output filenames, local paths and download URLs |
| `studio_read_result` | Read a recorded output/provenance notice through MCP, up to 8MB |
| `studio_get_log` | First 64KB of diagnostic log text |

Model IDs are `image`, `music`, `video`, `mesh`, and `cutout`.

Examples of `studio_generate` arguments:

```json
{"kind":"image","prompt":"a tiny glass greenhouse on a floating island","size":512,"seed":42}
```

```json
{"kind":"music","prompt":"instrumental, soft piano and warm bass, relaxed evening","duration":30,"instrumental":true}
```

```json
{"kind":"video","prompt":"A paper boat gently floats on a calm pond, steady cinematic camera."}
```

For 3D or background removal, first call `studio_upload_image` with `name` (PNG/JPEG/WebP) and `data_base64` (base64-encoded file bytes without a `data:` prefix, up to 20MB). Pass the returned `upload` value:

```json
{"kind":"mesh","upload":"UPLOAD_ID_FROM_STUDIO"}
```

The bridge does not read arbitrary input paths. Your client must supply the image bytes, using its own authorized file access. Prompts can contain up to 1500 characters (512 for music); lyrics up to 4096. Image sizes: 384, 512 or 640. Music durations: 10, 20, 30 or 60 seconds. A seed of -1 means random. Video is silent.

Generation returns immediately with a job ID. Poll `studio_get_job` about every 5–10 seconds. When status is `completed`, call `studio_get_results`, then `studio_read_result` for a selected file if needed. Larger assets can be opened using their local path/download URL. URLs work on the same computer while Studio is running. A cancelled or failed job may have no results.

Example request to your AI: “Use DY Studio to make a 30-second instrumental piano track. Check the music model first, ask me before installing it if needed, then report the completed WAV path.”

## Lifecycle and access

- `--start-studio` starts the loopback app, without opening a browser, on the first tool call if it is not running. It never starts a model install or generation by itself.
- Some clients stop child processes when they disconnect. If MCP started Studio, keep the client connected until jobs finish. To keep jobs running independently of the AI client, start Studio separately with `START.bat` before connecting; close it through **Exit app** after jobs finish.
- UI and MCP jobs share one queue, preserving sequential GPU use. Starting another MCP session does not create another worker queue.
- The bridge checks that the running app belongs to the same extracted folder, obtains its current request token internally, and sends requests only to `127.0.0.1`. Tokens never appear in tool output.
- To use another app port, add `"--port", "8770"` to the MCP arguments and start the UI with `python server.py --port 8770` if starting it manually.
- Connecting an AI gives it access to job prompts, supplied lyrics, logs and generated results through these tools. An external AI provider may receive tool responses. Use a local AI client if those responses must stay on your computer.
- Tool annotations describe reads, submissions, installation downloads and cancellation. Your AI client's permission settings decide when to ask for approval; annotations are not an authorization system. Keep confirmations enabled for installations/generation/cancellation as appropriate.
- Generated files remain subject to model licenses, input rights and the [generated content disclaimer](README.md#generated-content-disclaimer).

## Troubleshooting and validation

- **Missing dependency:** run `INSTALL_MCP.bat` again; configure its `.mcp-venv/Scripts/python.exe`, not a different Python.
- **Older/different Studio on the port:** finish/cancel its work, close it, and restart the updated app from the same folder as `mcp_server.py`, or select another port.
- **Model not installed:** use Model management or explicitly approve `studio_install_model`.
- **MCP has no tools:** check absolute paths and the client's stdio support, then reconnect. Standard output is reserved for MCP protocol messages; diagnostics use standard error.
- **Network failure during submission:** do not automatically retry; inspect `studio_list_jobs` first to avoid duplicate generation.

Run the ordinary tests with `python -m unittest discover -s tests -v`. To include the real stdio MCP round-trip tests, use `.mcp-venv/Scripts/python.exe -m unittest discover -s tests -v`. These tests use isolated HTTP/job fixtures; they do not download weights or rerun GPU generation. The five-engine GPU measurements in `VALIDATION.md` are separate evidence.
