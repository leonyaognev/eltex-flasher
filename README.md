# Eltex Flasher

Automated firmware deployment tool for Eltex MES switches.

Monitors the Eltex Validator web UI for new firmware images and pushes them to switches over TFTP via Ansible — fully hands-off.

## How it works

```
┌──────────────┐      poll       ┌─────────────────┐
│   Flasher    │ ──────────────> │ Eltex Validator  │
│  (Python)    │ <────────────── │   (Web UI API)   │
└──────┬───────┘    new image    └─────────────────┘
       │
       │  ansible-playbook
       ▼
┌──────────────┐     TFTP      ┌──────────────────┐
│   Ansible    │ ────────────> │  Eltex MES Switch │
│              │    firmware    │                   │
└──────────────┘               └──────────────────┘
```

1. **Poll** — the Flasher logs into the Validator and checks for the latest firmware image.
2. **Detect** — if a new image version is found (different from the last known one), deployment starts.
3. **Deploy** — Ansible connects to the target switch via SSH and runs `boot system tftp://...`, which downloads the image to inactive memory and sets it as the next boot image.
4. **Reboot** — the switch reloads and boots into the new firmware.
5. **Repeat** — the Flasher keeps polling in a loop, ready for the next update.

The tool does **not** enable Eltex's persistent "download firmware on boot" mechanism. Each upgrade is a one-shot operation.

## Project structure

```
eltex-flasher/
├── main.py              # Entry point
├── inventory.yml        # Ansible inventory (switch hosts)
├── upgrade.yml          # Ansible playbook (boot + reload)
├── src/
│   ├── api.py           # Eltex Validator HTTP client
│   ├── app.py           # Flasher orchestrator (poll + deploy)
│   ├── config.py        # Configuration from .env
│   └── ui.py            # (reserved)
├── .env.example         # Environment variable template
└── pyproject.toml       # Python project metadata
```

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager
- Ansible with `ansible.netcommon` and `nikitamishagin.eltex_mes` collections
- TFTP server reachable from the target switches
- Network access from the machine running the Flasher to the Validator and the switches

## Installation

```bash
# Clone the repo
git clone <repo-url> && cd eltex-flasher

# Install dependencies
uv sync

# Install Ansible collections
ansible-galaxy collection install ansible.netcommon
ansible-galaxy collection install nikitamishagin.eltex_mes
```

## Configuration

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

| Variable | Description | Default |
|---|---|---|
| `VALIDATOR_URL` | Eltex Validator base URL | `https://validator-v2.eltex.loc` |
| `VALIDATOR_USER` | Validator login | — |
| `VALIDATOR_PASSWORD` | Validator password | — |
| `ANSIBLE_USER` | SSH username for switches | `admin` |
| `ANSIBLE_PASSWORD` | SSH password for switches | `admin` |
| `TFTP_SERVER_IP` | IP of the TFTP server switches pull from | `192.168.246.95` |
| `DOWNLOAD_DIR` | Local dir for downloaded images | `~/work_pc` |
| `POLL_INTERVAL` | Seconds between Validator checks | `30` |
| `ANSIBLE_COMMAND_TIMEOUT` | Ansible command timeout in seconds | `600` |

Edit `inventory.yml` to add your switches and `src/config.py` to map image names to switch IPs.

## Usage

```bash
# Run the Flasher (continuous polling mode)
uv run main.py
```

The Flasher will:
- Log into the Validator
- Parse the latest firmware image from the files page
- Poll periodically for new versions
- Trigger Ansible deployment when a new image appears

### Stop

Press `Ctrl+C` to stop gracefully.

## Upgrade workflow (per switch)

| Step | What happens |
|---|---|
| 1 | Ansible connects via SSH |
| 2 | Runs `boot system tftp://<server>/<image>` — downloads to inactive slot |
| 3 | Runs `reload` — switch reboots |
| 4 | Switch boots from the newly written image |

## Important notes

- **Test first** — verify the `boot system` syntax and `reload` prompt on your specific Eltex MES model before mass rollout.
- **One-shot** — the playbook does not enable persistent TFTP download on boot. Subsequent reboots will not trigger another download.
- **Rollback** — the previous firmware is preserved in the inactive image slot. If the new firmware fails, you can manually switch back.
- **Serial deployment** — add `serial: 1` to the Ansible playbook if deploying to multiple switches to upgrade them one at a time.

## License

MIT
