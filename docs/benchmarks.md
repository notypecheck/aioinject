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

| Name                | iterations | total                      | mean      | median   |
|---------------------|------------|----------------------------|-----------|----------|
| python              | 100000     | 194.093ms                  | 1.941μs   | 1.900μs  |
| aioinject           | 100000     | 522.858ms                  | 5.229μs   | 4.500μs  |
| dishka              | 100000     | 519.200ms                  | 5.192μs   | 4.400μs  |
| rodi                | 100000     | 197.690ms                  | 1.977μs   | 1.900μs  |
| adriangb/di         | 100000     | 634.185ms                  | 6.342μs   | 6.200μs  |
| dependency-injector | 100000     | 158.057ms                  | 1.581μs   | 1.600μs  |
| punq                | 5000       | 10276.696ms (extrapolated) | 102.767μs | 91.500μs |
| lagom               | 100000     | 1009.967ms                 | 10.100μs  | 9.500μs  |
