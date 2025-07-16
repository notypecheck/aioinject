Aioinject integrates with `strawberry-graphql` using a
[custom extension](https://strawberry.rocks/docs/guides/custom-extensions):

```python hl_lines="10 28"
--8<-- "docs/code/integrations/strawberry-graphql.py"
```

1. Note that `inject` is imported from `aioinject.ext.strawberry`


## Usage with custom Context class
Default integration relies on strawberry-graphql context being a dictionary, you have to set 
`inject.context_getter` and `AioinjectExtension.context_setter` if you want to use a custom class.

```python hl_lines="18 35 46 52 73"
--8<-- "docs/code/integrations/strawberry-graphql-custom-context.py"
```
