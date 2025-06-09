import types
import typing
from collections.abc import Iterator, Sequence
from typing import Any

from aioinject._types import is_iterable_generic_collection
from aioinject.container import Container, Registry, SyncContainer
from aioinject.context import ProviderRecord
from aioinject.errors import ProviderNotFoundError
from aioinject.extensions.providers import ResolveDirective
from aioinject.scope import CurrentScope
from aioinject.validation.abc import ValidationRule
from aioinject.validation.errors import RuleViolation


def _iter_providers(registry: Registry) -> Iterator[ProviderRecord[Any]]:
    for provider_group in registry.providers.values():
        yield from provider_group


class NoAsyncDependenciesInSyncContainerRule(ValidationRule):
    def validate(
        self, container: Container | SyncContainer
    ) -> Sequence[RuleViolation]:
        if not isinstance(container, SyncContainer):
            return ()

        errors = []
        for provider in _iter_providers(container.registry):
            provide_directive = next(
                (
                    directive
                    for directive in provider.info.compilation_directives
                    if isinstance(directive, ResolveDirective)
                ),
                None,
            )
            if provide_directive is None:
                continue  # pragma: no cover

            if provide_directive.is_async:
                msg = f"Provider({provider.info.type_.__name__}) is async"
                errors.append(
                    RuleViolation(code="async-dependency", message=msg)
                )
        return errors


class ScopeMismatchRule(ValidationRule):
    def validate(  # noqa: C901
        self, container: Container | SyncContainer
    ) -> Sequence[RuleViolation]:
        errors = []
        for provider in _iter_providers(container.registry):
            for dependency in provider.info.dependencies:
                if not is_iterable_generic_collection(
                    dependency.type_
                ) and isinstance(dependency.type_, types.GenericAlias):
                    continue  # type: ignore[unreachable]

                try:
                    dependency_providers = container.registry.get_providers(
                        dependency.type_
                    )
                except ProviderNotFoundError:
                    if not is_iterable_generic_collection(dependency.type_):
                        raise  # pragma: no cover
                    dependency_providers = container.registry.get_providers(
                        typing.get_args(dependency.type_)[0]
                    )

                for dependency_provider in dependency_providers:
                    violation = self.validate_dependency(
                        container, provider, dependency_provider
                    )
                    if violation:
                        errors.append(violation)

        return errors

    def validate_dependency(
        self,
        container: Container | SyncContainer,
        provider: ProviderRecord[Any],
        dependency_provider: ProviderRecord[Any],
    ) -> RuleViolation | None:
        if isinstance(dependency_provider.info.scope, CurrentScope):
            return None

        scopes = tuple(container.scopes)
        scope_index = scopes.index(provider.info.scope)
        dependency_scope_index = scopes.index(dependency_provider.info.scope)

        if dependency_scope_index <= scope_index:
            return None

        msg = (
            f"Provider({provider.info.type_.__name__}) with scope {provider.info.scope} depends on "
            f"Provider({dependency_provider.info.type_.__name__}) with scope {dependency_provider.info.scope}, which is lower"
        )
        return RuleViolation(code="scope-mismatch", message=msg)


DEFAULT_RULES = [
    NoAsyncDependenciesInSyncContainerRule(),
    ScopeMismatchRule(),
]
