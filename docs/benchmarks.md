https://github.com/notypecheck/aioinject/tree/main/benchmark

Benchmark tries to resolve this set of dependencies 100k times:
```
UseCase
  ServiceA
    RepositoryA
      Session
  ServiceB
    RepositoryB
      Session
```
all of these are just simple classes, `Session` is resolved as a contextmanager/generator if framework supports this.


## Results
Best of 5 rounds  
CPU: Ryzen 9 7950x3d  
OS: Windows 10  
Python 3.12.7  

| Name                                                                          | iterations | total                      | mean      | median   |
|-------------------------------------------------------------------------------|------------|----------------------------|-----------|----------|
| [dependency-injector](https://github.com/ets-labs/python-dependency-injector) | 100000     | 155.024ms                  | 1.550μs   | 1.500μs  |
| python                                                                        | 100000     | 191.183ms                  | 1.912μs   | 1.900μs  |
| [rodi](https://github.com/Neoteroi/rodi)                                      | 100000     | 204.169ms                  | 2.042μs   | 2.000μs  |
| [dishka](https://github.com/reagento/dishka)                                  | 100000     | 529.615ms                  | 5.296μs   | 4.600μs  |
| aioinject                                                                     | 100000     | 531.493ms                  | 5.315μs   | 4.600μs  |
| [adriangb/di](https://github.com/adriangb/di)                                 | 100000     | 641.726ms                  | 6.417μs   | 6.100μs  |
| [lagom](https://github.com/meadsteve/lagom)                                   | 100000     | 985.291ms                  | 9.853μs   | 9.600μs  |
| [wireup](https://github.com/maldoinc/wireup)                                  | 100000     | 1446.966ms                 | 14.470μs  | 13.800μs |
| [punq](https://github.com/bobthemighty/punq)                                  | 5000       | 11184.062ms (extrapolated) | 111.841μs | 98.000μs |
