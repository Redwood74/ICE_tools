"""Tests for A-number redaction and masking utilities."""

from __future__ import annotations

from findICE.logging_utils import mask_a_number, redact_text


class TestMaskANumber:
    def test_9digit_a_number_with_prefix(self):
        result = mask_a_number("A-123456789")
        assert result.endswith("89")
        assert "*" in result
        assert "12345" not in result

    def test_8digit_a_number_with_prefix(self):
        result = mask_a_number("A-12345678")
        assert result.endswith("78")
        assert "*" in result

    def test_9digit_no_prefix(self):
        result = mask_a_number("123456789")
        assert result.endswith("89")
        assert "12345" not in result

    def test_a_number_with_space(self):
        result = mask_a_number("A 123456789")
        assert "*" in result
        assert "12345" not in result

    def test_no_a_number_in_text(self):
        text = "No numbers here at all."
        assert mask_a_number(text) == text

    def test_preserves_surrounding_text(self):
        result = mask_a_number("Subject is A-123456789 from Mexico.")
        assert "Subject is" in result
        assert "from Mexico." in result

    def test_multiple_a_numbers(self):
        result = mask_a_number("A-123456789 and A-987654321")
        assert "123456" not in result
        assert "987654" not in result


class TestRedactText:
    def test_redacts_known_a_number(self):
        text = "Checking A-123456789 now"
        result = redact_text(text, a_number="A-123456789")
        assert "123456789" not in result

    def test_redacts_digits_only_form(self):
        text = "The number is 123456789 in the system"
        result = redact_text(text, a_number="123456789")
        assert "1234567" not in result

    def test_no_a_number_provided(self):
        text = "No sensitive data here"
        assert redact_text(text) == text

    def test_preserves_non_pii_content(self):
        text = "Country: Mexico | Status: Active | A-123456789"
        result = redact_text(text, a_number="A-123456789")
        assert "Country: Mexico" in result
        assert "Status: Active" in result

    def test_empty_text(self):
        assert redact_text("") == ""
        assert redact_text("", a_number="123456789") == ""


class TestRedactingFilter:
    def test_filter_redacts_log_message(self):
        import logging

        from findICE.logging_utils import RedactingFilter

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Processing A-123456789 for country",
            args=(),
            exc_info=None,
        )
        f = RedactingFilter(a_number="A-123456789")
        f.filter(record)
        assert "123456" not in record.msg

    def test_filter_redacts_log_args(self):
        import logging

        from findICE.logging_utils import RedactingFilter

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="a_number=%s",
            args=("A-123456789",),
            exc_info=None,
        )
        f = RedactingFilter(a_number="A-123456789")
        f.filter(record)
        assert "123456" not in str(record.args)
