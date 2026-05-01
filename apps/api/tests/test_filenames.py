import pytest

from app.core.filenames import safe_filename


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Dragon", "Dragon"),
        ("Dragon Model v2", "Dragon_Model_v2"),
        ("foo/bar\\baz", "foo_bar_baz"),
        ("a<b>c:d|e?f*g", "a_b_c_d_e_f_g"),
        ('quote"name', "quote_name"),
        ("  spaced  out  ", "spaced_out"),
        ("dots...", "dots"),
        ("___under___", "under"),
        ("\x00\x01\x02ctrl", "ctrl"),
        ("Smok 🐉 Złoty", "Smok_Złoty"),  # 🐉 is printable per unicodedata; emoji depends
    ],
)
def test_safe_filename_examples(raw: str, expected: str) -> None:
    # The emoji case is loose — accept either with or without it.
    result = safe_filename(raw)
    if "🐉" in raw:
        assert result in {"Smok_🐉_Złoty", "Smok_Złoty"}
    else:
        assert result == expected


def test_safe_filename_truncates() -> None:
    result = safe_filename("a" * 200, max_len=50)
    assert len(result) == 50
    assert result == "a" * 50


def test_safe_filename_truncates_without_trailing_garbage() -> None:
    # Truncation that lands on a separator-like char is rstripped.
    result = safe_filename("abc" + " " * 50 + "x" * 50, max_len=5)
    # "abc_xxxx..." after collapse -> truncated to "abc_x"
    assert result == "abc_x"
    # If truncation falls on a trailing underscore/space/dot, those get stripped.
    result = safe_filename("abcd" + " " * 50, max_len=5)
    assert result == "abcd"


def test_safe_filename_falls_back_when_empty() -> None:
    assert safe_filename("///") == "model"
    assert safe_filename("   ", fallback="x") == "x"
    assert safe_filename("...") == "model"
