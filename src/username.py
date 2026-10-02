def is_valid_username(username: str) -> bool:
    if not isinstance(username, str):
        return False

    username = username.strip()

    if len(username) < 3:
        return False

    return username.isalnum()
