"""Local-only native extraction/OCR. No document content is sent to an AI API."""

import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree
from django.core.exceptions import ValidationError
from tribunal.models import FileVersion, DocumentText, MedicalRelease
from .files import private_path
from .applications import safe_file


def extract_local(file_id):
    file = FileVersion.objects.select_related("attachment__application").get(pk=file_id)
    if not safe_file(file):
        raise ValidationError("Technical validation required first.")
    if (
        (file.attachment.visibility == "medical" or (file.attachment.report_request_id
            and file.attachment.report_request.kind in {"medical", "psychological"}))
        and not MedicalRelease.objects.filter(
            request_id=file.attachment.report_request_id, subject_id=file.attachment.owner_id,
            request__subject__account_id=file.attachment.owner_id, scope__council=True
        ).exists()
    ):
        raise ValidationError("Await signed medical disclosure before extraction.")
    path = private_path(file.object_key)
    if not path.is_file():
        raise ValidationError("Original file is unavailable.")
    text = ""
    engine = ""
    try:
        if file.mime_type == "application/pdf":
            result = subprocess.run(
                ["pdftotext", "-layout", str(path), "-"],
                capture_output=True,
                timeout=180,
                check=True,
            )
            text = result.stdout.decode("utf-8", errors="replace")
            engine = "pdftotext"
            if len(text.strip()) < 20:
                with tempfile.TemporaryDirectory() as tmp:
                    sidecar = Path(tmp) / "text.txt"
                    output = Path(tmp) / "searchable.pdf"
                    subprocess.run(
                        [
                            "ocrmypdf",
                            "--skip-text",
                            "-l",
                            "eng+ara",
                            "--sidecar",
                            str(sidecar),
                            str(path),
                            str(output),
                        ],
                        capture_output=True,
                        timeout=1800,
                        check=True,
                    )
                    text = sidecar.read_text(encoding="utf-8")
                    engine = "ocrmypdf-tesseract-eng-ara"
        elif file.mime_type.startswith("image/"):
            result = subprocess.run(
                ["tesseract", str(path), "stdout", "-l", "eng+ara"],
                capture_output=True,
                timeout=300,
                check=True,
            )
            text = result.stdout.decode("utf-8", errors="replace")
            engine = "tesseract-eng-ara"
        elif (
            file.mime_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):
            with zipfile.ZipFile(path) as archive:
                info = archive.getinfo("word/document.xml")
                if info.file_size > 25 * 1024 * 1024:
                    raise ValidationError(
                        "Uncompressed document is too large to parse safely."
                    )
                xml = ElementTree.fromstring(archive.read(info))
                text = "\n".join(
                    node.text
                    for node in xml.iter()
                    if node.tag.endswith("}t") and node.text
                )
            engine = "docx-native"
        else:
            raise ValidationError(
                "This format requires the configured document/media adapter."
            )
    except (
        FileNotFoundError,
        subprocess.SubprocessError,
        UnicodeError,
        zipfile.BadZipFile,
        ElementTree.ParseError,
    ):
        raise ValidationError(
            "Local extraction failed or engine is not installed; original is retained."
        )
    if len(text) > 5_000_000:
        raise ValidationError(
            "Extracted text requires large-document processing; original is retained without silently truncating the record."
        )
    return DocumentText.objects.create(file=file, engine=engine, text=text)
