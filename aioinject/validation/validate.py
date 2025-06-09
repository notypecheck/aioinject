from __future__ import annotations

import collections
from collections.abc import Sequence
from typing import TYPE_CHECKING

from aioinject.validation.errors import RuleViolation, ValidationError


if TYPE_CHECKING:
    from aioinject import Container, SyncContainer
    from aioinject.validation.abc import ValidationRule


def validate_or_err(
    container: SyncContainer | Container,
    rules: Sequence[ValidationRule],
) -> None:
    errors: list[RuleViolation] = []
    for rule in rules:
        errors.extend(rule.validate(container))

    if not errors:
        return

    parts = [""]
    violations_by_group = collections.defaultdict(list)
    for violation in errors:
        violations_by_group[violation.code].append(violation)

    for code, violations in violations_by_group.items():
        parts.append(f"  {code}:")
        parts.extend(f"    {violation.message}" for violation in violations)

    error_message = "\n".join(parts)
    raise ValidationError(error_message)
