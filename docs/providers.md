Aioinject implements multiple different providers, 
they work similarly to [service lifetimes](https://learn.microsoft.com/en-us/dotnet/core/extensions/dependency-injection#service-lifetimes)
in other libraries, such as DI in .NET Core

### Scoped

Objects provided with `Scoped` provider would be cached within context.
```python
--8<-- "docs/code/providers/scoped.py"
```

### Transient

`Transient` provider would provide different instances even if used within same context 
```python
--8<-- "docs/code/providers/transient.py"
```

### Singleton

`Singleton` works as you expect - there would be only one instance of a singleton
object, bound to a specific container
```python
--8<-- "docs/code/providers/singleton.py"
```

### Object

`Object` provider just returns an object provided to it:
```python
from aioinject import Object

Object(42)
```
would always return 42
