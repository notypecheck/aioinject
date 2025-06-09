from collections.abc import Sequence
from typing import Protocol

from aioinject import Container, SyncContainer
from aioinject.validation.errors import RuleViolation


class ValidationRule(Protocol):
    def validate(
        self, container: Container | SyncContainer
    ) -> Sequence[RuleViolation]: ...
