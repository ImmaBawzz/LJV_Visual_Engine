import json
from pathlib import Path
from typing import Any, cast


ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "01_CONFIG"
REPORT_PATH = ROOT / "03_WORK" / "reports" / "schema_validation_report.json"


class SchemaValidationError(Exception):
    pass


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return False


def _validate_node(schema: dict[str, Any], value: Any, path: str, errors: list[str]) -> None:
    expected_type = schema.get("type")
    if expected_type and not _is_type(value, expected_type):
        errors.append(f"{path}: expected {expected_type}, got {type(value).__name__}")
        return

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value '{value}' is not in enum {schema['enum']}")

    if isinstance(value, str):
        min_length = schema.get("minLength")
        if min_length is not None and len(value) < min_length:
            errors.append(f"{path}: string length {len(value)} is less than minLength {min_length}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        if minimum is not None and value < minimum:
            errors.append(f"{path}: value {value} is less than minimum {minimum}")

    if isinstance(value, list):
        list_value = cast(list[Any], value)
        min_items = schema.get("minItems")
        if min_items is not None and len(list_value) < min_items:
            errors.append(f"{path}: item count {len(list_value)} is less than minItems {min_items}")
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(list_value):
                _validate_node(item_schema, item, f"{path}[{i}]", errors)

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required key '{key}'")

        properties = schema.get("properties", {})
        for key, prop_schema in properties.items():
            if key in value:
                _validate_node(prop_schema, value[key], f"{path}.{key}", errors)


def validate_file(config_name: str, schema_name: str) -> tuple[bool, list[str]]:
    config_path = CONFIG_DIR / config_name
    schema_path = CONFIG_DIR / "schemas" / schema_name

    if not config_path.exists():
        return False, [f"Config file missing: {config_path}"]
    if not schema_path.exists():
        return False, [f"Schema file missing: {schema_path}"]

    config_data = _load_json(config_path)
    schema_data = _load_json(schema_path)

    errors: list[str] = []
    _validate_node(schema_data, config_data, config_name, errors)
    return len(errors) == 0, errors


def _print_failure_details(report: dict[str, Any]) -> None:
    report_errors = cast(list[dict[str, Any]], report.get("errors", []))
    if not report_errors:
        print("[schema] Validation failed, but no error details were captured.")
        return

    print("[schema] Detailed validation errors:")
    for config_error in report_errors:
        config_name = str(config_error.get("config", "unknown config"))
        print(f"  - {config_name}")
        for err in cast(list[str], config_error.get("errors", [])):
            print(f"      * {err}")


def main() -> int:
    checks_list = [
        ("project_config.json", "project_config.schema.json"),
        ("paths_config.json", "paths_config.schema.json"),
        ("lyric_style_presets.json", "lyric_style_presets.schema.json"),
        ("reactive_presets.json", "reactive_presets.schema.json"),
        ("export_presets.json", "export_presets.schema.json"),
    ]

    report: dict[str, Any] = {
        "status": "PASS",
        "checks": [],
        "errors": [],
    }

    for config_name, schema_name in checks_list:
        ok, errors = validate_file(config_name, schema_name)
        report_checks = cast(list[dict[str, Any]], report["checks"])
        report_checks.append(
            {
                "config": config_name,
                "schema": schema_name,
                "status": "PASS" if ok else "FAIL",
            }
        )
        if not ok:
            report["status"] = "FAIL"
            report_errors = cast(list[dict[str, Any]], report["errors"])
            report_errors.append(
                {
                    "config": config_name,
                    "errors": errors,
                }
            )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")

    if report["status"] == "FAIL":
        print("Schema validation failed.")
        _print_failure_details(report)
        return 2

    print("Schema validation complete: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
