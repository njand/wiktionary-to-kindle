"""JSON Lines reading and writing, with orjson when it is installed (the `fast` extra)."""

import json

USING_ORJSON = False
try:
    import orjson

    def json_loads(line):
        return orjson.loads(line)

    def json_dumps(obj):
        return orjson.dumps(obj).decode("utf-8")

    USING_ORJSON = True
except ImportError:

    def json_loads(line):
        return json.loads(line)

    # Written as orjson writes it, since popup_order weighs entries by this text's length
    def json_dumps(obj):
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
