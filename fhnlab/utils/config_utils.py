def set_nested(d: dict, key: str, value):
    parts = key.split(".")
    for p in parts[:-1]:
        d = d.setdefault(p, {})
    d[parts[-1]] = value


def parse_value(val: str):
    for cast in (int, float):
        try:
            return cast(val)
        except ValueError:
            pass
    if val.lower() in ("true", "false"):
        return val.lower() == "true"
    return val
