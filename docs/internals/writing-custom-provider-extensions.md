`ProviderExtension` is what's responsible for extracting information from the provider - it's type, 
dependencies, and how to resolve it.

Here's an example extension that adds direct support for pydantic-settings `BaseSettings` class:
```python
--8<-- "docs/code/internals/custom_provider_extensions.py"
```
