#!/usr/bin/env python3
"""Apply deterministic build settings to a generated Safari Xcode project."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


SETTING_RE = re.compile(r"^(\s*)([A-Z0-9_]+)\s*=\s*(.*);$")


def pbx_value(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_.$()/]+", value):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def pbx_unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return value


def configure_pbxproj(
    path: Path,
    settings: dict[str, str],
    bundle_identifier: str | None,
) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    output: list[str] = []
    in_build_settings = False
    seen: set[str] = set()

    for line in lines:
        if not in_build_settings:
            output.append(line)
            if "buildSettings = {" in line:
                in_build_settings = True
                seen = set()
            continue

        if re.match(r"^\s*};\s*$", line):
            indent = re.match(r"^(\s*)", line).group(1) + "\t"
            for key, value in settings.items():
                if key not in seen:
                    output.append(f"{indent}{key} = {pbx_value(value)};\n")
            output.append(line)
            in_build_settings = False
            continue

        match = SETTING_RE.match(line)
        if match and match.group(2) == "PRODUCT_BUNDLE_IDENTIFIER" and bundle_identifier:
            indent, current_value = match.group(1), pbx_unquote(match.group(3))
            value = f"{bundle_identifier}.Extension" if current_value.endswith(".Extension") else bundle_identifier
            output.append(f"{indent}PRODUCT_BUNDLE_IDENTIFIER = {pbx_value(value)};\n")
        elif match and match.group(2) in settings:
            indent, key = match.group(1), match.group(2)
            output.append(f"{indent}{key} = {pbx_value(settings[key])};\n")
            seen.add(key)
        else:
            output.append(line)

    path.write_text("".join(output), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pbxproj", type=Path)
    parser.add_argument("--bundle-identifier")
    parser.add_argument("--code-sign-style", default="Automatic")
    parser.add_argument("--development-team")
    parser.add_argument("--marketing-version")
    parser.add_argument("--current-project-version")
    args = parser.parse_args()

    settings = {
        "CODE_SIGN_STYLE": args.code_sign_style,
    }
    if args.development_team:
        settings["DEVELOPMENT_TEAM"] = args.development_team
    if args.marketing_version:
        settings["MARKETING_VERSION"] = args.marketing_version
    if args.current_project_version:
        settings["CURRENT_PROJECT_VERSION"] = args.current_project_version

    configure_pbxproj(args.pbxproj, settings, args.bundle_identifier)


if __name__ == "__main__":
    main()
