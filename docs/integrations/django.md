

## Subclass AioinjectMiddleware
Since Django doesn't allow you to parametrize middleware (e.g. like starlette [does](https://www.starlette.io/middleware/))
we need to subclass `AioinjectMiddleware`:

```python title="app/di.py"
--8<-- "docs/code/integrations/django_01_subclass.py"
```
alternatively you can declare a property if needed:
```python
class DIMiddleware(SyncAioinjectMiddleware):
    @property
    def container(self) -> SyncContainer:
        return create_container()

```

## Add middleware to your [`settings.MIDDLEWARE`](https://docs.djangoproject.com/en/5.2/topics/http/middleware/#activating-middleware)

```python hl_lines="9" title="app/settings.py"
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "app.di.DIMiddleware",
]
```


## Mark your view with `@inject`

```python title="views.py"
--8<-- "docs/code/integrations/django_02_view.py"
```
!!! warning
    Since django and rest_framework pass request as a positional argument your request parameter should always
    be declared first.

# Integration with Rest Framework
`@inject` decorator should work with any function/method that accepts 
[`django.http.HttpRequest`](https://docs.djangoproject.com/en/5.2/ref/request-response/#httprequest-objects) 
or [`rest_framework.request.Request`](https://www.django-rest-framework.org/api-guide/requests/):
```python

--8<-- "docs/code/integrations/django_03_drf.py"
```
