#!/usr/bin/env python3

import os
import re
import time
import signal
import urllib3
import sys
from pathlib import Path


import requests
from bs4 import BeautifulSoup


URL = "https://validator-v2.eltex.loc"
DOWNLOAD_DIR = Path.home() / "work_pc"

VALIDATOR_USER = os.environ["VALIDATOR_USER"]
VALIDATOR_PASSWORD = os.environ["VALIDATOR_PASSWORD"]

session = requests.Session()

# Аналог curl -ks
session.verify = False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_csrf_from_login():
    response = session.get(f"{URL}/login/")
    response.raise_for_status()

    match = re.search(
        r'name="csrf_token"\s+value="([^"]+)"',
        response.text,
    )

    if not match:
        raise RuntimeError("CSRF token not found")

    return match.group(1)


def login():
    csrf_token = get_csrf_from_login()

    response = session.post(
        f"{URL}/login/",
        data={
            "login": VALIDATOR_USER,
            "password": VALIDATOR_PASSWORD,
            "csrf_token": csrf_token,
        },
    )
    response.raise_for_status()


def get_upload_csrf():
    response = session.get(f"{URL}/files/")
    response.raise_for_status()

    match = re.search(
        r'<meta\s+name="csrf-token"\s+content="([^"]+)"',
        response.text,
    )

    if not match:
        raise RuntimeError("Upload CSRF token not found")

    return match.group(1)


def get_latest_file():
    response = session.get(f"{URL}/files/")
    response.raise_for_status()

    return response.text


def parse_latest_file(html):
    soup = BeautifulSoup(html, "html.parser")

    last_id = None

    for td in soup.find_all("td"):
        text = td.get_text(strip=True)

        if text.isdigit():
            last_id = text
            break

    element = soup.find(attrs={"data-file-name": True})

    if element is None:
        last_name = None
    else:
        last_name = element["data-file-name"]
        last_name = Path(last_name).name

    return last_id, last_name


def download_file(file_id, file_name):
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    output_path = DOWNLOAD_DIR / file_name

    print(f"[*] Downloading: {file_name}")
    print(f"    ID: {file_id}")
    print(f"    Path: {output_path}")

    response = session.get(
        f"{URL}/files/{file_id}",
        stream=True,
    )
    response.raise_for_status()

    with output_path.open("wb") as file:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                file.write(chunk)

    print("[+] Download complete")

def get_tftp_link(html: string ) -> string:
    soup = BeautifulSoup(html, "html.parser")

    split_btn = soup.find("div", class_="split-btn")
    if split_btn is None:
        raise RuntimeError("split-btn not found")

    server_ip = split_btn.get("data-tftp-host")
    file_id = split_btn.get("data-file-id")

    tftp_url = f"tftp://{server_ip}/{file_id}"

    return tftp_url


def main():
    print("[*] Logging in...")

    login()

    print("[+] Login successful")

    get_upload_csrf()
    html = get_latest_file()

    last_id, last_name = parse_latest_file(html)

    if last_id is None:
        print("ERROR: Latest file ID not found", file=sys.stderr)
        sys.exit(1)

    if last_name is None:
        print("ERROR: Latest file name not found", file=sys.stderr)
        sys.exit(1)

    print("[*] Latest file:")
    print(f"    ID:   {last_id}")
    print(f"    Name: {last_name}")

    while True:
        time.sleep(10)

        try:
            html = get_latest_file()

            current_id, current_name = parse_latest_file(html)

            if current_id is None:
                print("ERROR: Current file ID not found", file=sys.stderr)
                continue

            if current_id != last_id:
                last_id = current_id
                last_name = current_name

                tftp_link = get_tftp_link(html)

                print(tftp_link)



            else:
                print("\nNo new image")

        except requests.RequestException as error:
            print(f"[!] HTTP error: {error}", file=sys.stderr)

        except Exception as error:
            print(f"[!] Error: {error}", file=sys.stderr)


if __name__ == "__main__":
    main()
