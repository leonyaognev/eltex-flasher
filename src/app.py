import time
import asyncio
import requests

from datetime import datetime

from .api import login, get_latest_file, get_tftp_link, parse_latest_file
from .config import (
    RETRY_DELAY,
    ANSIBLE_INVENTORY,
    ANSIBLE_PLAYBOOK,
    TFTP_SERVER_IP,
    SWITCH_USERNAME,
    ANSIBLE_PASSWORD,
    ANSIBLE_COMMAND_TIMEOUT,
    IMAGE_TO_SWITCH,
)


def log(level: str, message: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {message}", flush=True)
    with open("app.log", "w") as f:
        f.write(f"[{ts}] [{level}] {message}")


class Flasher:
    def __init__(self):
        log("INFO", "Logging in...")

        try:
            login()
        except requests.RequestException as error:
            log("ERROR", f"Login failed: {error}")
            time.sleep(RETRY_DELAY)
            raise

        log("INFO", "Login successful")

        image_id, image_name, _ = self.fetch_latest_image()
        self.IMAGE_NAME_TO_ID = {image_name: image_id}

        log("INFO", f"Current image: {image_name} ({image_id})")

        self.tasks = {}

    async def ansible_switches(self, tftp_link: str, switch_host: str):
        process = await asyncio.create_subprocess_exec(
            "ansible-playbook",
            "-i",
            ANSIBLE_INVENTORY,
            ANSIBLE_PLAYBOOK,
            "--extra-vars",
            f"tftp_link={tftp_link} \
            switch_host={switch_host} \
            tftp_server_ip={TFTP_SERVER_IP} \
            switch_username={SWITCH_USERNAME} \
            ansible_password={ANSIBLE_PASSWORD} \
            ansible_command_timeout={ANSIBLE_COMMAND_TIMEOUT}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(
                f"Deploy failed with code {process.returncode}\n{stderr.decode()}"
            )

        return stdout.decode()

    def fetch_latest_image(self):
        try:
            html = get_latest_file()

            image_id, image_name = parse_latest_file(html)
            if not image_id or not image_name:
                raise RuntimeError("Image name or image id not found")

            tftp_link = get_tftp_link(html)

            return image_id, image_name, tftp_link

        except requests.RequestException as error:
            log("ERROR", f"HTTP: {error}")

        except Exception as error:
            log("ERROR", str(error))

        return None, None, None

    async def deploy(self, current_id, current_name, tftp_link, switch):
        try:
            self.IMAGE_NAME_TO_ID[current_name] = current_id
            await self.ansible_switches(tftp_link, switch)
        except Exception as error:
            log("ERROR", f"Deployment failed for {current_name}: {error}")
            return

        log("NEW", f"New image: {current_name} ({current_id})")
        log("INFO", f"TFTP: {tftp_link}")

    async def run(self) -> int:
        current_id, current_name, tftp_link = self.fetch_latest_image()
        log("INFO", f"Current image: {current_name} ({current_id})")

        old_id = self.IMAGE_NAME_TO_ID.get(current_name)
        if current_id != old_id and not self.tasks.get(current_name):

            def remove_task(done_task):
                if self.tasks.get(current_name) is done_task:
                    self.tasks.pop(current_name, None)

            if current_name and IMAGE_TO_SWITCH.get(current_name):
                switches = IMAGE_TO_SWITCH[current_name]
                for switch in switches:
                    task = asyncio.create_task(
                        self.deploy(current_id, current_name, tftp_link, switch)
                    )

                    self.tasks[current_name] = task
                    task.add_done_callback(remove_task)

                    log("INFO", "New task created")
        else:
            log("INFO", "No new image")

        return 0
