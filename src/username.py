from typing import Final

USERNAME_MIN_LENGTH: Final[int] = 3


def is_valid_username(username: str) -> bool:
    if not isinstance(username, str):
        return False

    username = username.strip()

    if len(username) < USERNAME_MIN_LENGTH:
        return False

    return username.isalnum()
