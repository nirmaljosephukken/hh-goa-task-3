from pathlib import Path

from PIL import Image, ImageDraw

from src.image_matcher import compare_images


def test_accepts_a_recompressed_copy(tmp_path: Path):
    original = tmp_path / "original.png"
    copy = tmp_path / "copy.jpg"

    image = Image.new("RGB", (120, 80), "white")
    ImageDraw.Draw(image).rectangle((20, 15, 100, 65), fill="navy")
    image.save(original)
    image.resize((240, 160)).save(copy, quality=80)

    assert compare_images(original, copy).matches


def test_rejects_a_different_image(tmp_path: Path):
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"

    first_image = Image.new("RGB", (120, 80), "white")
    ImageDraw.Draw(first_image).rectangle((20, 15, 100, 65), fill="navy")
    first_image.save(first)

    second_image = Image.new("RGB", (120, 80), "black")
    second_draw = ImageDraw.Draw(second_image)
    for index in range(0, 120, 12):
        second_draw.line((index, 0, 120 - index, 80), fill="gold", width=4)
    second_image.save(second)

    assert not compare_images(first, second).matches


def test_accepts_a_crop_of_the_same_image(tmp_path: Path):
    original = tmp_path / "original.png"
    cropped = tmp_path / "cropped.jpg"

    image = Image.new("RGB", (180, 120), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 10, 160, 110), fill="navy")
    draw.ellipse((65, 25, 125, 85), fill="gold")
    image.save(original)
    image.crop((30, 0, 150, 120)).save(cropped, quality=85)

    assert compare_images(original, cropped).matches
