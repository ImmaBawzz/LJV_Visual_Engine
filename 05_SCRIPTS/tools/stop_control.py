#!/usr/bin/env python3
"""Create and verify signed stop.now files for pipeline halt control."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import importlib
import json
import os
import secrets
import struct
import time
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
STOP_FILE = ROOT / "stop.now"
DEFAULT_ENV_FILE = ROOT / "01_CONFIG" / "stop_control.env"


def _sign(secret: str, mode: str, timestamp: int, nonce: str) -> str:
    message = f"{mode}|{timestamp}|{nonce}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def _decode_base32_secret(raw_secret: str) -> bytes:
    normalized = raw_secret.strip().replace(" ", "").upper()
    if not normalized:
        raise ValueError("Empty TOTP secret")
    padding = "=" * ((8 - (len(normalized) % 8)) % 8)
    return base64.b32decode(normalized + padding, casefold=True)


def _totp_code(secret_b32: str, for_timestamp: int, step: int = 30, digits: int = 6) -> str:
    secret = _decode_base32_secret(secret_b32)
    counter = int(for_timestamp // step)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(secret, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    truncated = digest[offset:offset + 4]
    code_int = struct.unpack(">I", truncated)[0] & 0x7FFFFFFF
    return str(code_int % (10 ** digits)).zfill(digits)


def _totp_matches(secret_b32: str, code: str, timestamp: int, step: int = 30, digits: int = 6, skew_windows: int = 1) -> bool:
    normalized_code = code.strip()
    if not normalized_code.isdigit() or len(normalized_code) != digits:
        return False

    for delta in range(-skew_windows, skew_windows + 1):
        candidate = _totp_code(secret_b32, timestamp + (delta * step), step=step, digits=digits)
        if hmac.compare_digest(candidate, normalized_code):
            return True
    return False


def _build_otpauth_uri(secret_b32: str, account: str, issuer: str, digits: int = 6, period: int = 30, algorithm: str = "SHA1") -> str:
    label = f"{issuer}:{account}"
    return (
        f"otpauth://totp/{quote(label)}"
        f"?secret={quote(secret_b32)}"
        f"&issuer={quote(issuer)}"
        f"&algorithm={quote(algorithm)}"
        f"&digits={digits}"
        f"&period={period}"
    )


def _render_qr_ascii(otpauth_uri: str) -> str:
    try:
        qrcode = importlib.import_module("qrcode")
    except ImportError as ex:
        raise RuntimeError("qrcode package is not installed (pip install qrcode[pil])") from ex

    qr = qrcode.QRCode(border=1)
    qr.add_data(otpauth_uri)
    qr.make(fit=True)
    matrix = qr.get_matrix()

    lines: list[str] = []
    # Use full blocks for a compact terminal QR-like output.
    for row in matrix:
        lines.append("".join("##" if cell else "  " for cell in row))
    return "\n".join(lines)


def _write_qr_png(otpauth_uri: str, output: Path) -> None:
    try:
        qrcode = importlib.import_module("qrcode")
    except ImportError as ex:
        raise RuntimeError("qrcode package is not installed (pip install qrcode[pil])") from ex

    img = qrcode.make(otpauth_uri)
    img.save(str(output))


def _generate_signing_secret(byte_count: int = 32) -> str:
    return secrets.token_urlsafe(byte_count)


def _generate_totp_secret(byte_count: int = 20) -> str:
    raw = secrets.token_bytes(byte_count)
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def _write_env_file(path: Path, stop_secret: str, totp_secret: str, require_totp: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# LJV stop-control security settings",
        "# Keep this file private and out of shared logs/screenshots.",
        f"LJV_STOP_SECRET={stop_secret}",
        f"LJV_STOP_TOTP_SECRET={totp_secret}",
        f"LJV_STOP_REQUIRE_TOTP={'true' if require_totp else 'false'}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def write_stop_file(mode: str, reason: str, secret: str, output: Path, totp_code: str | None = None) -> None:
    if mode not in {"graceful", "immediate"}:
        raise ValueError("mode must be 'graceful' or 'immediate'")

    timestamp = int(time.time())
    nonce = secrets.token_hex(16)
    signature = _sign(secret, mode, timestamp, nonce)

    lines = [
        f"mode={mode}",
        f"timestamp={timestamp}",
        f"nonce={nonce}",
        f"reason={reason}",
    ]
    if totp_code:
        lines.append(f"totp={totp_code}")
    lines.append(f"signature={signature}")
    output.write_text("\n".join(lines) + "\n", encoding="ascii")


def parse_stop_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw_line in path.read_text(encoding="ascii").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip().lower()] = value.strip()
    return data


def verify_stop_file(path: Path, secret: str, max_age_sec: int, totp_secret: str | None = None, require_totp: bool = False, totp_skew_windows: int = 1) -> tuple[bool, str, dict[str, str]]:
    if not path.exists():
        return False, f"Missing file: {path}", {}

    payload = parse_stop_file(path)
    mode = payload.get("mode", "")
    if mode not in {"graceful", "immediate"}:
        return False, "Invalid or missing mode", payload

    try:
        ts = int(payload.get("timestamp", ""))
    except ValueError:
        return False, "Invalid or missing timestamp", payload

    nonce = payload.get("nonce", "")
    signature = payload.get("signature", "").lower()
    if not nonce or not signature:
        return False, "Missing nonce/signature", payload

    if abs(int(time.time()) - ts) > max_age_sec:
        return False, f"Signature expired (> {max_age_sec}s)", payload

    expected = _sign(secret, mode, ts, nonce)
    if not hmac.compare_digest(expected, signature):
        return False, "Signature mismatch", payload

    if require_totp or totp_secret:
        if not totp_secret:
            return False, "TOTP is required but LJV_STOP_TOTP_SECRET is missing", payload
        totp_code = payload.get("totp", "")
        if not totp_code:
            return False, "Missing TOTP code in stop file", payload
        try:
            if not _totp_matches(totp_secret, totp_code, ts, skew_windows=totp_skew_windows):
                return False, "Invalid TOTP code", payload
        except Exception as ex:
            return False, f"TOTP validation error: {ex}", payload

    return True, f"Valid signed stop file ({mode})", payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage signed stop.now control files.")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="Create a signed stop.now file")
    create.add_argument("--mode", choices=["graceful", "immediate"], default="graceful")
    create.add_argument("--reason", default="Operator requested stop")
    create.add_argument("--secret", default=None, help="Shared secret; defaults to LJV_STOP_SECRET")
    create.add_argument("--totp-secret", default=None, help="Base32 TOTP secret; defaults to LJV_STOP_TOTP_SECRET")
    create.add_argument("--totp-code", default=None, help="Current 6-digit authenticator code")
    create.add_argument("--output", default=str(STOP_FILE), help="Output stop file path")

    verify = sub.add_parser("verify", help="Verify a signed stop.now file")
    verify.add_argument("--secret", default=None, help="Shared secret; defaults to LJV_STOP_SECRET")
    verify.add_argument("--totp-secret", default=None, help="Base32 TOTP secret; defaults to LJV_STOP_TOTP_SECRET")
    verify.add_argument("--input", default=str(STOP_FILE), help="Input stop file path")
    verify.add_argument("--max-age-sec", type=int, default=1800)
    verify.add_argument("--require-totp", action="store_true", help="Require TOTP even if no TOTP secret is configured")
    verify.add_argument("--totp-skew-windows", type=int, default=1)
    verify.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    gen = sub.add_parser("gen-secret", help="Generate a random HMAC signing secret")
    gen.add_argument("--bytes", type=int, default=32)

    gen_totp = sub.add_parser("gen-totp-secret", help="Generate a Base32 TOTP secret")
    gen_totp.add_argument("--bytes", type=int, default=20)

    provision = sub.add_parser("provision-totp", help="Generate one-step TOTP onboarding data (secret + otpauth URI + optional QR)")
    provision.add_argument("--issuer", default="LJV Visual Engine", help="TOTP issuer label")
    provision.add_argument("--account", default="pipeline-stop", help="TOTP account label")
    provision.add_argument("--secret", default=None, help="Use an existing Base32 TOTP secret instead of generating a new one")
    provision.add_argument("--bytes", type=int, default=20, help="Secret bytes to generate when --secret is not provided")
    provision.add_argument("--digits", type=int, default=6)
    provision.add_argument("--period", type=int, default=30)
    provision.add_argument("--show-current-code", action="store_true", help="Also print the current code for validation")
    provision.add_argument("--qr-ascii", action="store_true", help="Render QR in terminal (requires qrcode package)")
    provision.add_argument("--qr-png", default=None, help="Write QR PNG to this path (requires qrcode[pil])")
    provision.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    write_env = sub.add_parser("write-env", help="Write env setup file with signing and TOTP secrets")
    write_env.add_argument("--output", default=str(DEFAULT_ENV_FILE), help="Path to env setup file")
    write_env.add_argument("--stop-secret", default=None, help="Use existing signing secret instead of generating one")
    write_env.add_argument("--totp-secret", default=None, help="Use existing TOTP secret instead of generating one")
    write_env.add_argument("--stop-secret-bytes", type=int, default=32)
    write_env.add_argument("--totp-secret-bytes", type=int, default=20)
    write_env.add_argument("--require-totp", action="store_true", help="Set LJV_STOP_REQUIRE_TOTP=true in output file")
    write_env.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    totp_cmd = sub.add_parser("totp", help="Print current TOTP code for a secret")
    totp_cmd.add_argument("--totp-secret", default=None, help="Base32 TOTP secret; defaults to LJV_STOP_TOTP_SECRET")

    args = parser.parse_args()

    if args.command == "gen-secret":
        print(_generate_signing_secret(args.bytes))
        return 0

    if args.command == "gen-totp-secret":
        print(_generate_totp_secret(args.bytes))
        return 0

    if args.command == "write-env":
        stop_secret = args.stop_secret or _generate_signing_secret(args.stop_secret_bytes)
        totp_secret = args.totp_secret or _generate_totp_secret(args.totp_secret_bytes)
        output_path = Path(args.output)

        try:
            _decode_base32_secret(totp_secret)
        except Exception as ex:
            print(f"ERROR: invalid TOTP secret: {ex}")
            return 2

        _write_env_file(output_path, stop_secret, totp_secret, require_totp=args.require_totp)

        if args.json:
            env_payload: dict[str, object] = {
                "output": str(output_path),
                "LJV_STOP_SECRET": stop_secret,
                "LJV_STOP_TOTP_SECRET": totp_secret,
                "LJV_STOP_REQUIRE_TOTP": args.require_totp,
            }
            print(json.dumps(env_payload))
            return 0

        print(f"Env setup written: {output_path}")
        print("Use in PowerShell:")
        print(f"  Get-Content '{output_path}' | ForEach-Object {{ if ($_ -match '^(?<k>[^=]+)=(?<v>.*)$') {{ Set-Item -Path Env:$($matches.k) -Value $matches.v }} }}")
        return 0

    if args.command == "provision-totp":
        if args.secret:
            secret_b32 = args.secret.strip().replace(" ", "").upper()
            try:
                _decode_base32_secret(secret_b32)
            except Exception as ex:
                print(f"ERROR: invalid provided TOTP secret: {ex}")
                return 2
        else:
            raw = secrets.token_bytes(args.bytes)
            secret_b32 = base64.b32encode(raw).decode("ascii").rstrip("=")

        otpauth_uri = _build_otpauth_uri(
            secret_b32,
            account=args.account,
            issuer=args.issuer,
            digits=args.digits,
            period=args.period,
        )

        current_code = ""
        if args.show_current_code:
            current_code = _totp_code(secret_b32, int(time.time()), step=args.period, digits=args.digits)

        if args.qr_png:
            try:
                _write_qr_png(otpauth_uri, Path(args.qr_png))
            except Exception as ex:
                print(f"ERROR: could not write QR PNG: {ex}")
                return 2

        qr_ascii = ""
        if args.qr_ascii:
            try:
                qr_ascii = _render_qr_ascii(otpauth_uri)
            except Exception as ex:
                print(f"ERROR: could not render ASCII QR: {ex}")
                return 2

        if args.json:
            provision_payload: dict[str, object] = {
                "totp_secret": secret_b32,
                "otpauth_uri": otpauth_uri,
                "issuer": args.issuer,
                "account": args.account,
                "digits": args.digits,
                "period": args.period,
            }
            if args.qr_png:
                provision_payload["qr_png"] = args.qr_png
            if current_code:
                provision_payload["current_code"] = current_code
            if qr_ascii:
                provision_payload["qr_ascii"] = qr_ascii
            print(json.dumps(provision_payload))
            return 0

        print(f"LJV_STOP_TOTP_SECRET={secret_b32}")
        print(f"otpauth_uri={otpauth_uri}")
        print(f"set LJV_STOP_TOTP_SECRET={secret_b32}")
        if current_code:
            print(f"current_code={current_code}")
        if args.qr_png:
            print(f"qr_png={args.qr_png}")
        if qr_ascii:
            print("\nASCII QR:\n")
            print(qr_ascii)
        return 0

    if args.command == "totp":
        totp_secret = args.totp_secret or os.environ.get("LJV_STOP_TOTP_SECRET")
        if not totp_secret:
            print("ERROR: missing TOTP secret (use --totp-secret or set LJV_STOP_TOTP_SECRET)")
            return 2
        try:
            print(_totp_code(totp_secret, int(time.time())))
            return 0
        except Exception as ex:
            print(f"ERROR: could not generate TOTP: {ex}")
            return 2

    secret = args.secret or os.environ.get("LJV_STOP_SECRET")
    if not secret:
        print("ERROR: missing secret (use --secret or set LJV_STOP_SECRET)")
        return 2

    if args.command == "create":
        output_path = Path(args.output)
        totp_secret = args.totp_secret or os.environ.get("LJV_STOP_TOTP_SECRET")
        totp_code = args.totp_code

        if totp_secret:
            if not totp_code:
                print("ERROR: missing TOTP code (use --totp-code) because TOTP secret is configured")
                return 2
            try:
                now_ts = int(time.time())
                if not _totp_matches(totp_secret, totp_code, now_ts):
                    print("ERROR: invalid TOTP code")
                    return 2
            except Exception as ex:
                print(f"ERROR: could not validate TOTP code: {ex}")
                return 2

        write_stop_file(args.mode, args.reason, secret, output_path, totp_code=totp_code)
        print(f"Signed stop file written: {output_path}")
        return 0

    totp_secret = args.totp_secret or os.environ.get("LJV_STOP_TOTP_SECRET")
    require_totp = args.require_totp or os.environ.get("LJV_STOP_REQUIRE_TOTP", "").lower() in {"1", "true", "yes", "on"}
    valid, message, payload = verify_stop_file(
        Path(args.input),
        secret,
        args.max_age_sec,
        totp_secret=totp_secret,
        require_totp=require_totp,
        totp_skew_windows=max(0, args.totp_skew_windows),
    )

    if args.json:
        result: dict[str, object] = {
            "valid": valid,
            "message": message,
            "mode": payload.get("mode", ""),
            "reason": payload.get("reason", ""),
        }
        print(json.dumps(result))
        return 0 if valid else 1

    if valid:
        print(message)
        return 0

    print(f"INVALID: {message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
