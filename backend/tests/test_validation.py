import pytest

from app.utils.validation import InvalidTickerError, normalize_and_validate_ticker


def test_valid_ticker_uppercased_and_stripped():
    assert normalize_and_validate_ticker("  aapl ") == "AAPL"


def test_ticker_with_dot_and_dash_allowed():
    assert normalize_and_validate_ticker("brk-b") == "BRK-B"
    assert normalize_and_validate_ticker("bf.b") == "BF.B"


def test_index_ticker_with_caret_allowed():
    assert normalize_and_validate_ticker("^gspc") == "^GSPC"


@pytest.mark.parametrize("bad", ["", "   ", None])
def test_empty_ticker_rejected(bad):
    with pytest.raises(InvalidTickerError):
        normalize_and_validate_ticker(bad)


def test_too_long_ticker_rejected():
    with pytest.raises(InvalidTickerError):
        normalize_and_validate_ticker("THISISWAYTOOLONGATICKER")


@pytest.mark.parametrize("bad", ["AAPL;DROP TABLE", "<script>", "AA PL", "AAPL$$"])
def test_malformed_ticker_rejected(bad):
    with pytest.raises(InvalidTickerError):
        normalize_and_validate_ticker(bad)
