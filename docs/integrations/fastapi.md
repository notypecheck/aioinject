To integrate with FastAPI you need to add a `AioinjectMiddleware` and
optionally a lifespan if you use context manager dependencies:
```python hl_lines="11 18-19 24"
--8<-- "docs/code/integrations/fastapi_.py"
```

1. (Optionally) if you want to inject `Request` and `BackgroundTasks` through aioinject - add a `FastAPIExtension`
2. Manage container lifespan inside an ASGI lifespan
3. Add middleware to your app
