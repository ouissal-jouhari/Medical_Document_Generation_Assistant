"""Précharge les modèles Docling au build de l'image (une conversion à vide)."""

import io

from PIL import Image, ImageDraw, ImageFont

from app.adapters.docling_converter import DoclingMarkdownConverter


def main() -> None:
    buffer = io.BytesIO()
    # Du texte est nécessaire : sans lui, les modèles OCR ne sont jamais chargés (donc jamais
    # téléchargés) et le premier dépôt d'une image les chercherait sur le réseau.
    image = Image.new("RGB", (800, 300), "white")
    ImageDraw.Draw(image).text(
        (40, 100), "Superbill 2026 CPT 99213", fill="black", font=ImageFont.load_default(size=48)
    )
    image.save(buffer, format="PNG")
    DoclingMarkdownConverter().convert_to_markdown(buffer.getvalue(), "png")
    print("Modèles Docling préchargés")  # noqa: T201


if __name__ == "__main__":
    main()
