"""Bounded DLC uploads; encrypted containers are decoded by JDownloader."""
import base64
import binascii
import re
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field

MAX_FILES = 20
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 10 * 1024 * 1024
MAX_REQUEST_BYTES = 4 * ((MAX_TOTAL_BYTES + 2) // 3) + 64 * 1024


class DlcFile(BaseModel):
    name: str = Field(min_length=5, max_length=255)
    content: str = Field(min_length=1, max_length=4 * ((MAX_FILE_BYTES + 2) // 3))


class DlcUpload(BaseModel):
    confirmed: Literal[True]
    files: list[DlcFile] = Field(min_length=1, max_length=MAX_FILES)


def data_urls(files):
    """Validate the whole batch before submitting any part of it."""
    urls = []
    total = 0
    seen = set()
    for file in files:
        if not file.name.lower().endswith('.dlc') or any(
            char in '/\\' or ord(char) < 32 for char in file.name
        ):
            raise HTTPException(422, 'Bitte ausschließlich DLC-Dateien auswählen.')
        try:
            content = base64.b64decode(file.content, validate=True)
        except (ValueError, binascii.Error):
            raise HTTPException(422, 'Eine DLC-Datei konnte nicht gelesen werden.') from None
        if not content or len(content) > MAX_FILE_BYTES:
            raise HTTPException(422, 'Jede DLC-Datei muss zwischen 1 Byte und 2 MB groß sein.')
        total += len(content)
        if total > MAX_TOTAL_BYTES:
            raise HTTPException(413, 'Die DLC-Dateien dürfen zusammen höchstens 10 MB groß sein.')
        # DLC has encrypted base64 text plus a key suffix. Decryption and link
        # discovery belong to the engine, not the portal.
        if len(content.strip()) <= 88 or not re.fullmatch(rb'[A-Za-z0-9+/=\r\n\t ]+', content):
            raise HTTPException(422, 'Eine Datei enthält keinen gültigen DLC-Container.')
        if content not in seen:
            seen.add(content)
            urls.append('data:application/dlc;base64,' + base64.b64encode(content).decode('ascii'))
    return urls
