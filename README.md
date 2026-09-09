# Eltex Flasher

Automated firmware deployment tool for Eltex MES switches.

Monitors the Eltex Validator web UI for new firmware images and pushes them to switches over TFTP via Ansible — fully hands-off.

## How it works

```
┌──────────────┐      poll       ┌─────────────────┐
│   Flasher    │ ──────────────> │ Eltex Validator │
│  (Python)    │ <────────────── │   (Web UI API)  │
└──────┬───────┘    new image    └─────────────────┘
       │
       │  ansible-playbook
       ▼
┌──────────────┐     TFTP      ┌──────────────────┐
│   Ansible    │ ────────────> │  Eltex MES Switch│
│              │    firmware   │                  │
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
├── main.py                # Entry point
├── config.json            # Main configuration (network, timeouts, images)
├── ansible/
│   ├── inventory.yml      # Ansible inventory (switch hosts)
│   └── upgrade.yml        # Ansible playbook (boot + reload)
├── src/
│   ├── api.py             # Eltex Validator HTTP client
│   ├── app.py             # Flasher orchestrator (poll + deploy)
│   ├── config.py          # Configuration loader (.env + config.json)
│   └── ui.py              # Rich terminal UI
├── .env.example           # Secrets template
└── pyproject.toml         # Python project metadata
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

Configuration is split between two files:

- **`config.json`** — network settings, paths, timeouts, and image-to-switch mapping
- **`.env`** — secrets (credentials only)

### 1. Create `.env` from the template

```bash
cp .env.example .env
```

Fill in the credentials:

| Variable             | Description               | Default |
| -------------------- | ------------------------- | ------- |
| `VALIDATOR_USER`     | Validator login           | `admin` |
| `VALIDATOR_PASSWORD` | Validator password        | `admin` |
| `SWITCH_USERNAME`    | SSH username for switches | `admin` |
| `ANSIBLE_PASSWORD`   | SSH password for switches | `admin` |

### 2. Edit `config.json`

```jsonc
{
    "validator": {
        "url": "https://validator-v2.eltex.loc"   // Validator base URL
    },
    "ssh": {
        "tftp_server_ip": "192.168.246.95"         // TFTP server IP for switches
    },
    "paths": {
        "download_dir": "~/work_pc",               // Local dir for downloaded images
        "ansible_inventory": "ansible/inventory.yml",
        "ansible_playbook": "ansible/upgrade.yml"
    },
    "timeouts": {
        "retry_delay": 2,                          // Seconds before retry on error
        "poll_interval": 30,                       // Seconds between Validator checks
        "poll_granularity": 1,                     // UI refresh granularity
        "post_upgrade_delay": 2,                   // Delay after upgrade completes
        "ansible_command_timeout": 300             // Ansible SSH command timeout
    },
    "download": {
        "chunk_size": 8192                         // Download chunk size in bytes
    },
    "images": {
        "<image_name>": ["<switch_ip>", ...]       // Map firmware images to target switches
    }
}
```

### 3. Map images to switches

The `images` section maps firmware image names (as shown in the Validator UI) to the IP addresses of the switches that should receive them:

```json
"images": {
    "curr_image_msys": ["192.168.246.93"],
    "curr_image_ac5": ["192.168.246.92", "192.168.246.94"]
}
```

When the Flasher detects a new version of `curr_image_msys`, it will deploy it to `192.168.246.93` via Ansible.

## Usage

```bash
uv run main.py
```

The Flasher will:

1. Log into the Validator
2. Display a live terminal UI with firmware status, active deployments, and uptime
3. Poll periodically for new image versions
4. Trigger Ansible deployment to mapped switches when a new image appears

Press `Ctrl+C` to stop.

## Upgrade workflow (per switch)

| Step | What happens                                                            |
| ---- | ----------------------------------------------------------------------- |
| 1    | Ansible connects via SSH                                                |
| 2    | Runs `boot system tftp://<server>/<image>` — downloads to inactive slot |
| 3    | Runs `reload` — switch reboots                                          |
| 4    | Switch boots from the newly written image                               |

## Important notes

- **Test first** — verify the `boot system` syntax and `reload` prompt on your specific Eltex MES model before mass rollout.
- **One-shot** — the playbook does not enable persistent TFTP download on boot. Subsequent reboots will not trigger another download.
- **Rollback** — the previous firmware is preserved in the inactive image slot. If the new firmware fails, you can manually switch back.
- **Serial deployment** — add `serial: 1` to the Ansible playbook if deploying to multiple switches to upgrade them one at a time.

## License

MIT
