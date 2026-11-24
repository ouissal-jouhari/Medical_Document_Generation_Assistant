"""F-03 / N-06 : le type réel du fichier est contrôlé, pas seulement l'extension."""

import pytest

from app.adapters.file_inspector import MAX_PAGES, inspect_upload
from app.domain.errors import (
    CorruptFile,
    EncryptedPdf,
    FileTooLarge,
    ImageTooLarge,
    SafeError,
    TooManyPages,
    UnsupportedFormat,
)
from tests.superbill_samples import (
    CLEAN_TEXT,
    blank_pdf,
    encrypted_pdf,
    image_bytes,
    pdf_with_text,
)

LIMIT = 50 * 1024 * 1024


def test_F03_accepts_pdf_up_to_three_pages() -> None:
    for pages in range(1, MAX_PAGES + 1):
        info = inspect_upload(blank_pdf(pages), "pdf", LIMIT)
        assert (info.kind, info.pages) == ("pdf", pages)


def test_F03_refuses_a_pdf_of_four_pages() -> None:
    with pytest.raises(TooManyPages):
        inspect_upload(blank_pdf(4), "pdf", LIMIT)


@pytest.mark.parametrize(
    ("fmt", "extension", "kind"),
    [("PNG", "png", "png"), ("JPEG", "jpg", "jpeg"), ("JPEG", "jpeg", "jpeg")],
)
def test_F03_accepts_one_image_per_file(fmt: str, extension: str, kind: str) -> None:
    info = inspect_upload(image_bytes(fmt), extension, LIMIT)
    assert (info.kind, info.pages) == (kind, 1)


def test_F03_refuses_a_file_over_the_size_limit() -> None:
    with pytest.raises(FileTooLarge):
        inspect_upload(blank_pdf(1), "pdf", 100)


def test_F03_refuses_other_formats() -> None:
    for extension in ("txt", "docx", "exe", "gif", ""):
        with pytest.raises(UnsupportedFormat):
            inspect_upload(blank_pdf(1), extension, LIMIT)


def test_N06_renamed_text_file_is_refused_even_with_pdf_extension() -> None:
    with pytest.raises(UnsupportedFormat):
        inspect_upload(b"Ceci est un texte, pas un PDF.", "pdf", LIMIT)


def test_N06_executable_renamed_to_png_is_refused() -> None:
    with pytest.raises(UnsupportedFormat):
        inspect_upload(b"MZ\x90\x00" + b"\x00" * 100, "png", LIMIT)


def test_N06_real_type_must_match_the_extension() -> None:
    for content, extension in (
        (blank_pdf(1), "png"),
        (image_bytes("PNG"), "pdf"),
        (image_bytes("PNG"), "jpg"),
        (image_bytes("JPEG"), "png"),
    ):
        with pytest.raises(UnsupportedFormat):
            inspect_upload(content, extension, LIMIT)


def test_N06_extension_case_is_ignored_but_real_type_is_checked() -> None:
    assert inspect_upload(blank_pdf(1), "PDF", LIMIT).kind == "pdf"
    assert inspect_upload(blank_pdf(1), ".pdf", LIMIT).kind == "pdf"


def test_F03_refuses_an_encrypted_pdf() -> None:
    with pytest.raises(EncryptedPdf):
        inspect_upload(encrypted_pdf(), "pdf", LIMIT)


def test_F03_refuses_corrupt_files() -> None:
    with pytest.raises(CorruptFile):
        inspect_upload(b"%PDF-1.7\ngarbage without structure", "pdf", LIMIT)
    with pytest.raises(CorruptFile):
        inspect_upload(image_bytes("PNG")[:40], "png", LIMIT)


def test_N06_booby_trapped_image_is_refused_by_decompressed_size() -> None:
    huge = image_bytes("PNG", size=(6000, 6000))  # petit fichier, 36 millions de pixels
    assert len(huge) < 200_000
    with pytest.raises(ImageTooLarge):
        inspect_upload(huge, "png", LIMIT)


def test_F03_pdf_with_text_layer_is_accepted() -> None:
    assert inspect_upload(pdf_with_text(CLEAN_TEXT), "pdf", LIMIT).pages == 1


def test_N11_file_errors_expose_only_a_stable_code() -> None:
    for content, extension in ((b"x", "pdf"), (blank_pdf(4), "pdf"), (encrypted_pdf(), "pdf")):
        with pytest.raises(SafeError) as error:
            inspect_upload(content, extension, LIMIT)
        assert str(error.value) == error.value.code
        assert error.value.extra == {}
