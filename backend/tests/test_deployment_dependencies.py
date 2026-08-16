"""The deployed image installs from requirements.txt, not from pyproject.toml.

Keeping the two in step was a comment asking to be remembered, and it was not: adding
olefile for .hwp support passed every test locally and then crashed on boot in
production. A drift between them cannot be caught by any other test here, because the
local environment is built from the file that was updated.
"""

import re
import tomllib
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
REQUIREMENT = re.compile(r"^\s*([A-Za-z0-9._-]+(?:\[[^\]]+\])?)\s*==\s*([^\s#]+)")


def _declared() -> dict[str, str]:
    project = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))
    found = {}
    for entry in project["project"]["dependencies"]:
        match = REQUIREMENT.match(entry)
        assert match, f"{entry} is not pinned; deployment cannot mirror a floating version"
        found[match.group(1).casefold()] = match.group(2)
    return found


def _deployed() -> dict[str, str]:
    lines = (BACKEND / "requirements.txt").read_text(encoding="utf-8").splitlines()
    matches = (REQUIREMENT.match(line) for line in lines if line.strip() and not line.lstrip().startswith("#"))
    return {match.group(1).casefold(): match.group(2) for match in matches if match}


def test_every_dependency_is_installed_in_the_deployed_image() -> None:
    missing = set(_declared()) - set(_deployed())

    assert not missing, f"requirements.txt is missing {sorted(missing)}; the service will fail to import them on boot"


def test_the_deployed_image_installs_nothing_extra() -> None:
    extra = set(_deployed()) - set(_declared())

    assert not extra, f"requirements.txt pins {sorted(extra)} that pyproject.toml does not declare"


def test_the_two_files_agree_on_every_version() -> None:
    declared, deployed = _declared(), _deployed()
    mismatched = {name: (declared[name], deployed[name]) for name in declared.keys() & deployed.keys() if declared[name] != deployed[name]}

    assert not mismatched, f"version drift between pyproject.toml and requirements.txt: {mismatched}"
