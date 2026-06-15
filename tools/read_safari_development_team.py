#!/usr/bin/env python3
"""Read an Apple development team ID from Keychain-backed signing data."""

from __future__ import annotations

import argparse
import re
import subprocess


TEAM_ID_RE = re.compile(r"\(([A-Z0-9]{10})\)")


def read_generic_password(service: str, account: str) -> str | None:
    try:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-s",
                service,
                "-a",
                account,
                "-w",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    value = result.stdout.strip()
    return value if re.fullmatch(r"[A-Z0-9]{10}", value) else None


def read_team_from_identities(identity_filter: str) -> str | None:
    try:
        result = subprocess.run(
            ["security", "find-identity", "-v", "-p", "codesigning"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    teams: list[str] = []
    for line in result.stdout.splitlines():
        if identity_filter and identity_filter not in line:
            continue
        match = TEAM_ID_RE.search(line)
        if match:
            teams.append(match.group(1))

    unique_teams = sorted(set(teams))
    return unique_teams[0] if len(unique_teams) == 1 else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", required=True)
    parser.add_argument("--account", required=True)
    parser.add_argument("--identity-filter", default="")
    args = parser.parse_args()

    team_id = read_generic_password(args.service, args.account)
    if team_id is None:
        team_id = read_team_from_identities(args.identity_filter)
    if team_id:
        print(team_id)


if __name__ == "__main__":
    main()
