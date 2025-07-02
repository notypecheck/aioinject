## 1.4.3 (2025-07-03)

### Fix

- exclude functools.partial args from dependencies
- fix resolving Object provider types if they have interface

## 1.4.2 (2025-06-29)

### Fix

- bind Object node type to provided interface

## 1.4.1 (2025-06-26)

## 1.4.0 (2025-06-26)

### Feat

- add OnResolveContextExtension

### Fix

- allow sort_nodes more attempts to resolve postponed nodes
- OnResolveContextExtension should not be included if compiled function is not async

## 1.3.0 (2025-06-23)

### Feat

- raise human-readable error if dependency requires scope that isn't yet available/active
- add compiled function source into `linecache.cache` so it's shown in the traceback

## 1.2.3 (2025-06-20)

### Fix

- generate valid variable name with unions

## 1.2.2 (2025-06-20)

### Fix

- TypeError when applying `inject` decorator

## 1.2.1 (2025-06-20)

### Feat

- Add dependency validation

### Fix

- **inject**: fix issue with decorating functions that have **kwargs parameters in them

## 1.2.0 (2025-06-06)

### Feat

- add DRF support

## 1.1.0 (2025-06-03)

### Feat

- add sync django integration

## 1.0.1 (2025-06-02)

### Fix

- correctly name FromContext nodes

## 1.0.0 (2025-06-02)

### Feat

- add support for dependencies that use `functools.partial`
- **fastapi**: add websocket support
- add ability to request context dependencies from current scope, automatically add Context/SyncContext to current scope
- add aiogram integration
- transient providers
- add TestContainer class
- support injecting dependency collections (iterables)
- support using unbound generics
- acquire context lock when resolving singletons
- add fastapi and strawberry-graphql integrations

### Fix

- python3.10 compatibility
- clear root context cache before and after override
- correctly resolve interfaces
- **strawberry-graphql**: except TypeError when checking if argument is a subclass of strawberry.Info
- import Inject and Injected in aioinject.__init__
- preserve lifespan order in async container
- use topological sorter to detect cycles between dependency nodes

### Refactor

- remove dead code
- wrap resolved nodes into a tuple instead of a list
- rename `ProviderInfo.actual_type` to `type`
- call `self.root` instead of `self._root` in `Container.__(a)enter__`
- move compilation related code into package
- remove empty tests
- move TypeVars to aioinject._types
- fix provider extension naming

## 0.38.1 (2025-04-10)

### Fix

- correctly resolve type context types when lazy annotations are used

## 0.38.0 (2025-03-10)

### Feat

- add ability to use providers from context

## 0.37.4 (2025-02-12)

## 0.37.3 (2025-02-12)

## 0.37.2 (2025-02-12)

## 0.37.1 (2025-02-12)

## 0.37.0 (2025-02-05)

### Fix

- update compatibility check for Python version greater than 3.11

### Refactor

- **generics**: try using Generic[args] to make generics
- enhance Python 3.11 compatibility checks and update test decorators
- improve compatibility handling and clean up generics code

## 0.36.1 (2025-01-30)

### Fix

- **container**: handle registering providers with unhashable implementations

## 0.36.0 (2025-01-09)

### Feat

- add iterable providers

### Fix

- test_partially_resolved_generic
- update get_typevars to return a list of TypeVars and enhance nested generic tests
- enhance generic type handling and add tests for nested concrete generics
- correct test to -> `test_nested_unresolved_generic`
- update resolved type handling in InjectionContext and add uv.lock for dependency management

### Refactor

- use is_iterable_generic_collection
- use Provider.__hash__ in stores

## 0.35.3 (2024-11-22)

### Fix

- avoid closing context multiple times

## 0.35.2 (2024-11-22)

### Fix

- **litestar**: exceptions weren't propagated to contextmanager dependencies

### Refactor

- **litestar**: make after_exception function private
- migrate to uv

## 0.35.1 (2024-09-24)

## 0.35.0 (2024-09-17)

### Feat

- Add `Injected[T]` annotation as a shorthand for `Annotated[T, Inject]` by @nrbnlulu

### Tests

- Add test for `strawberry.subscription` by @nrbnlulu
