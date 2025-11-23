"""Tests for Quran management commands.

Tests AC #3-5:
- Import commands parse data correctly
- Verification command validates data integrity
"""

from io import StringIO

import pytest
from django.core.management import call_command

from .factories import SurahFactory


@pytest.mark.django_db
class TestVerifyQuranDataCommand:
    """Test cases for verify_quran_data command (AC #5)."""

    def test_verify_empty_database_reports_errors(self):
        """Test verification fails with empty database."""
        out = StringIO()
        err = StringIO()

        # Should not raise but report errors
        call_command("verify_quran_data", stdout=out, stderr=err)

        output = out.getvalue()
        assert "Surah count: 0/114" in output
        assert "verse count: 0/6236" in output

    def test_verify_with_strict_mode_exits_on_error(self):
        """Test --strict flag causes exit on errors."""
        with pytest.raises(SystemExit):
            call_command("verify_quran_data", "--strict")

    def test_verify_partial_data_reports_missing(self):
        """Test verification reports missing Surahs."""
        # Create only 3 Surahs
        SurahFactory(id=1, total_verses=7)
        SurahFactory(id=2, total_verses=286)
        SurahFactory(id=3, total_verses=200)

        out = StringIO()
        call_command("verify_quran_data", stdout=out)

        output = out.getvalue()
        assert "Surah count: 3/114" in output

    def test_verify_includes_report_metadata(self):
        """Test verification report includes date and source."""
        out = StringIO()
        call_command("verify_quran_data", stdout=out)

        output = out.getvalue()
        assert "QURAN DATA VERIFICATION REPORT" in output
        assert "Date:" in output
        assert "Data Source: Tanzil Uthmani v1.1" in output


@pytest.mark.django_db
class TestImportQuranTextCommand:
    """Test cases for import_quran_text command (AC #3)."""

    def test_import_file_not_found(self):
        """Test error when XML file doesn't exist."""
        out = StringIO()
        err = StringIO()

        call_command(
            "import_quran_text",
            "--file", "/nonexistent/path.xml",
            stdout=out,
            stderr=err
        )

        error_output = err.getvalue()
        assert "XML file not found" in error_output

    def test_import_command_has_file_argument(self):
        """Test import command accepts --file argument."""
        out = StringIO()
        err = StringIO()

        # This should fail because file doesn't exist, but proves the arg works
        call_command(
            "import_quran_text",
            "--file", "/custom/path.xml",
            stdout=out,
            stderr=err
        )

        error_output = err.getvalue()
        assert "/custom/path.xml" in error_output


@pytest.mark.django_db
class TestImportQuranMetadataCommand:
    """Test cases for import_quran_metadata command (AC #4)."""

    def test_import_metadata_file_not_found(self):
        """Test error when XML file doesn't exist."""
        out = StringIO()
        err = StringIO()

        call_command(
            "import_quran_metadata",
            "--file", "/nonexistent/path.xml",
            stdout=out,
            stderr=err
        )

        error_output = err.getvalue()
        assert "XML file not found" in error_output

    def test_import_metadata_command_has_file_argument(self):
        """Test import command accepts --file argument."""
        out = StringIO()
        err = StringIO()

        # This should fail because file doesn't exist, but proves the arg works
        call_command(
            "import_quran_metadata",
            "--file", "/custom/path.xml",
            stdout=out,
            stderr=err
        )

        error_output = err.getvalue()
        assert "/custom/path.xml" in error_output
