from src.username import is_valid_username


def test_valid_username():
    assert is_valid_username("Jagan123") is True


def test_username_too_short():
    assert is_valid_username("ab") is False


def test_username_with_spaces():
    assert is_valid_username("Jagan 123") is False


def test_username_with_special_characters():
    assert is_valid_username("Jagan@123") is False


def test_empty_username():
    assert is_valid_username("") is False


def test_non_string_username():
    assert is_valid_username(None) is False
