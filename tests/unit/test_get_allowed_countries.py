"""Tests for the get_allowed_countries function."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from usdb_syncer.utils import _parse_polsy_html, get_allowed_countries


@pytest.fixture
def country_codes(resource_dir: Path) -> None:
    """Load country codes from JSON file once."""
    json_file = resource_dir / "html" / "polsy-org-uk" / "codes.json"
    with json_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def check_valid_country_code(country_codes: list, country_code: str) -> bool:
    """Check if the country code is valid."""
    return (
        len(country_code) == 2
        and country_code.isalpha()
        and country_code in country_codes
    )


def get_test_resources() -> list[tuple[Path, Path]]:
    """Get pairs of HTML and JSON files for testing."""
    resources_dir = Path(__file__).parent.parent / "resources" / "html" / "polsy-org-uk"

    # Find all HTML files with matching JSON files
    html_files = list(resources_dir.glob("*.html"))
    test_cases: list[tuple[Path, Path]] = []

    for html_file in html_files:
        json_file = resources_dir / f"{html_file.stem}.json"
        if json_file.exists():
            test_cases.append((html_file, json_file))

    return test_cases


class MockResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code
        self.ok = status_code == 200


@pytest.mark.parametrize("html_file, json_file", get_test_resources())
def test_get_allowed_countries(
    html_file: Path, json_file: Path, resource_dir: Path, country_codes: list
) -> None:
    """Test get_allowed_countries with different HTML/JSON pairs."""
    # Load test data
    html_content = html_file.read_text(encoding="utf-8")

    with json_file.open("r", encoding="utf-8") as f:
        expected_data: dict = json.load(f)

    # Extract expected allowed countries
    expected_allowed_countries = None
    if expected_data.get("none") is False and "allowed" in expected_data:
        expected_allowed_countries = expected_data["allowed"]

    result = _parse_polsy_html(html_content)
    for cc in result if result else []:
        assert check_valid_country_code(country_codes, cc), (
            f"Invalid country code: {cc}"
        )

    if expected_data.get("none") is True:
        assert result is None
    else:
        if expected_allowed_countries:
            assert result == expected_allowed_countries
        else:
            assert result is not None


def test_get_allowed_countries_request_error() -> None:
    """Test get_allowed_countries when the request fails."""
    with patch("requests.get") as mock_get:
        mock_get.return_value = MockResponse("", status_code=404)

        result = get_allowed_countries("dummy-video-id")

        assert result is None
