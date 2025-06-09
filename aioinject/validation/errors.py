import dataclasses


@dataclasses.dataclass(slots=True, kw_only=True)
class RuleViolation:
    code: str
    message: str


class ValidationError(Exception):
    pass
