"""Tests for the packaged ASCII logo asset and its loaders.

These guard against the regression where the logo lived under ``examples/``
and silently disappeared from installed wheels (only ``gerdsenai_cli`` is
packaged).
"""

from importlib import resources

from gerdsenai_cli.utils.display import (
    ASCII_ART_FILENAME,
    get_ascii_art_path,
    get_logo_text,
)


def test_logo_asset_is_packaged() -> None:
    """The ASCII art ships inside the importable package, not in examples/."""
    resource = resources.files("gerdsenai_cli").joinpath("assets", ASCII_ART_FILENAME)
    assert resource.is_file()


def test_get_logo_text_non_empty() -> None:
    """The loader returns the logo content."""
    logo = get_logo_text()
    assert logo.strip(), "logo text should not be empty"
    # The wordmark at the bottom of the art renders 'GerdsenAI'.
    assert "$$" in logo  # sanity: the art uses '$' glyphs


def test_get_ascii_art_path_points_into_package() -> None:
    """The path helper resolves to the packaged asset and the file exists."""
    path = get_ascii_art_path()
    assert path.name == ASCII_ART_FILENAME
    assert "gerdsenai_cli" in path.parts
    assert path.exists()
