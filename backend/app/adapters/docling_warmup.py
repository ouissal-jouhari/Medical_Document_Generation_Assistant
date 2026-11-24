"""Précharge les modèles Docling au build de l'image (une conversion à vide)."""

import io

from PIL import Image

from app.adapters.docling_converter import DoclingMarkdownConverter


def main() -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (400, 200), "white").save(buffer, format="PNG")
    DoclingMarkdownConverter().convert_to_markdown(buffer.getvalue(), "png")
    print("Modèles Docling préchargés")  # noqa: T201


if __name__ == "__main__":
    main()
