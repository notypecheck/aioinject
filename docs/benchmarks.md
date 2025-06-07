https://github.com/notypecheck/aioinject/tree/main/benchmark

Benchmark tries to resolve this set of dependencies:
```
UseCase
  ServiceA
    RepositoryA
      Session
  ServiceB
    RepositoryB
      Session
```

## Async
Async API is used, `Session` dependency ran as a context manager, equivalent to
```python
async with create_session_cm() as session:
    repo_a = RepositoryA(session=session)
    repo_b = RepositoryB(session=session)
    svc_a = ServiceA(repository=repo_a)
    svc_b = ServiceB(repository=repo_b)
    UseCase(service_a=svc_a, service_b=svc_b)
```

| Name                                          | iterations | total      | mean     | median   |
|-----------------------------------------------|------------|------------|----------|----------|
| python                                        | 100000     | 194.520ms  | 1.945μs  | 1.900μs  |
| [dishka](https://github.com/reagento/dishka)  | 100000     | 600.378ms  | 6.004μs  | 4.600μs  |
| aioinject                                     | 100000     | 611.180ms  | 6.112μs  | 5.100μs  |
| [adriangb/di](https://github.com/adriangb/di) | 100000     | 623.968ms  | 6.240μs  | 6.200μs  |
| [wireup](https://github.com/maldoinc/wireup)  | 100000     | 1394.453ms | 13.945μs | 13.900μs |
!!! note 
    This set of benchmarks is smaller, since not all libraries support scopes or context manager dependencies



## Sync
All libraries use synchronous API with no context managers, equivalent to
```python
session = Session()
repo_a = RepositoryA(session=session)
repo_b = RepositoryB(session=session)
svc_a = ServiceA(repository=repo_a)
svc_b = ServiceB(repository=repo_b)
UseCase(service_a=svc_a, service_b=svc_b)
```

| Name                                                                          | iterations | total                     | mean     | median   |
|-------------------------------------------------------------------------------|------------|---------------------------|----------|----------|
| python                                                                        | 100000     | 73.443ms                  | 0.734μs  | 0.700μs  |
| [dependency-injector](https://github.com/ets-labs/python-dependency-injector) | 100000     | 154.265ms                 | 1.543μs  | 1.500μs  |
| [rodi](https://github.com/Neoteroi/rodi)                                      | 100000     | 208.062ms                 | 2.081μs  | 2.000μs  |
| aioinject                                                                     | 100000     | 343.069ms                 | 3.431μs  | 2.700μs  |
| [dishka](https://github.com/reagento/dishka)                                  | 100000     | 359.610ms                 | 3.596μs  | 3.000μs  |
| [adriangb/di](https://github.com/adriangb/di)                                 | 100000     | 426.652ms                 | 4.267μs  | 4.200μs  |
| [lagom](https://github.com/meadsteve/lagom)                                   | 100000     | 1101.359ms                | 11.014μs | 10.400μs |
| [wireup](https://github.com/maldoinc/wireup)                                  | 100000     | 1436.985ms                | 14.370μs | 13.500μs |
| [punq](https://github.com/bobthemighty/punq)                                  | 5000       | 9771.656ms (extrapolated) | 97.717μs | 91.000μs |
