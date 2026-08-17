# Eltex MES firmware automation with Ansible

This project performs a one-shot firmware upgrade. It does **not** configure the
switch to download firmware on every reboot.

The workflow is:

1. `show bootvar`
2. If target version is already active: do nothing.
3. If target version is already in the inactive image: select it.
4. Otherwise run `boot system tftp://...`, which downloads the image to the
   inactive area and makes it active after reboot.
5. `reload`
6. Wait for SSH.
7. Run `show bootvar` again and verify the target version.

The Eltex MES CLI documentation describes `boot system source_url` as copying
firmware from the server into the inactive memory area, and `boot system
inactive-image` as booting the inactive image. It also documents `show bootvar`
for inspecting the two images.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install ansible

ansible-galaxy collection install -r requirements.yml
```

## Configure

Edit:

- `inventory/hosts.yml`
- `group_vars/eltex.yml`

Make sure the TFTP server is reachable from the switch itself.

The `reload_prompt` is intentionally configurable because the exact confirmation
prompt can differ between firmware trains. Test `reload` manually on one lab
switch before mass rollout.

## Check only

```bash
ansible-playbook playbooks/check.yml --ask-pass
```

## Upgrade one switch

```bash
ansible-playbook playbooks/upgrade.yml --limit sw01 --ask-pass
```

## Upgrade the whole group

The playbook uses `serial: 1`, so switches are upgraded one at a time.

```bash
ansible-playbook playbooks/upgrade.yml --ask-pass
```

## Important

Do not enable Eltex's persistent "download firmware on boot" mechanism for this
workflow. The playbook explicitly chooses the image for this one upgrade only,
so an ordinary reboot later will not trigger another TFTP download.

Before production use, test:

- the exact `boot system tftp://...` syntax on your MES model;
- the exact `reload` confirmation prompt;
- the target image compatibility with the hardware model;
- that the inactive image is preserved as the rollback image.
