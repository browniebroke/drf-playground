# DRF Playground

A fake **library lending system** built to exercise the main features of
[Django REST Framework](https://www.django-rest-framework.org/). No front-end; the API is the product.

## Running

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py seed_data      # sample data + users admin/password and reader/password
uv run python manage.py runserver
```

- API root: <http://localhost:8000/api/v1/> (browsable API, log in via `/api-auth/login/`)
- Swagger UI: <http://localhost:8000/api/v1/docs/>, Redoc: `/api/v1/redoc/`, raw schema: `/api/v1/schema/`
- Token: `POST /api/v1/auth/token/ {"username": "reader", "password": "password"}` then `Authorization: Token <key>`

Tests: `uv run pytest`. Lint: `uv run ruff check . && uv run ruff format .`

## Layout

```
manage.py
drf_playground/
  settings.py, urls.py        # project config; API mounted at /api/<version>/
  api.py                      # combines every app router into one DefaultRouter + hand-wired routes
  apps/
    core/                     # shared DRF plumbing + tiny endpoints (ping, whoami, stats)
    catalog/                  # publishers, authors, genres, books, physical copies
    library/                  # loans, reviews, user shelves
```

## Domain

`Publisher` 1-n `Book` n-m `Author`, `Book` n-m `Genre`, `Book` 1-n `Copy` (physical item).
`Loan` is made against a `Copy` by a user (one open loan per copy). `Review` is one per user per book.
`Shelf` is a user's curated list of books, private unless `is_public`.

## DRF feature map

| Feature                                                                                            | Where                                                                                        |
| -------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `@api_view` function view                                                                          | `core/views.py` `ping`                                                                       |
| `APIView`                                                                                          | `core/views.py` `WhoAmIView`, `StatsView`                                                    |
| `GenericAPIView` + mixins, custom `lookup_field`                                                   | `catalog/views.py` `GenreListView`, `GenreDetailView` (slug lookup)                          |
| Concrete generics (`ListCreateAPIView`, `RetrieveUpdateDestroyAPIView`)                            | `catalog/views.py` `Publisher*View`                                                          |
| `ModelViewSet`, per-action serializer (`get_serializer_class`)                                     | `catalog/views.py` `BookViewSet`                                                             |
| `GenericViewSet` + chosen mixins (no update/delete)                                                | `library/views.py` `LoanViewSet`                                                             |
| `@action` detail/list, custom `url_path`, per-action `serializer_class` / `permission_classes`     | `BookViewSet.copies`, `.recently_added`, `LoanViewSet.return_loan`, `ShelfViewSet.add_books` |
| Routers: `SimpleRouter` per app merged into a `DefaultRouter`, `basename`, `lookup_field` in URLs  | `catalog/urls.py`, `library/urls.py`, `drf_playground/api.py`, `CopyViewSet` (barcode)       |
| `format_suffix_patterns` (`/ping.json`)                                                            | `core/urls.py`                                                                               |
| `ModelSerializer`, `read_only_fields`, `extra_kwargs`, `source=`                                   | everywhere; `library/serializers.py` `LoanSerializer`                                        |
| `HyperlinkedModelSerializer`, `HyperlinkedRelatedField`                                            | `catalog/serializers.py` `AuthorSerializer`                                                  |
| Plain `Serializer` (non-model, input-only / output-only)                                           | `core/serializers.py` `StatsSerializer`, `library/serializers.py` `ShelfBooksSerializer`     |
| Nested read serializers, `SerializerMethodField`, annotated read-only fields                       | `BookDetailSerializer`                                                                       |
| Nested **writable** serializer (`create()` override)                                               | `BookWriteSerializer.copies`                                                                 |
| `PrimaryKeyRelatedField`, `SlugRelatedField`, `StringRelatedField`                                 | `BookWriteSerializer`, `BookListSerializer`                                                  |
| `HiddenField` + `CurrentUserDefault`                                                               | `ReviewSerializer.author`, `ShelfSerializer.owner`                                           |
| Field-level `validate_<field>`, object-level `validate()`, custom validator shared with model      | `BookWriteSerializer`, `catalog/validators.py`                                               |
| `UniqueTogetherValidator`                                                                          | `ReviewSerializer`, `ShelfSerializer`                                                        |
| Pagination: custom `PageNumberPagination` (`page_size` param)                                      | `core/pagination.py` (project default)                                                       |
| `LimitOffsetPagination`                                                                            | `PublisherListCreateView`                                                                    |
| `CursorPagination`                                                                                 | `library/pagination.py`, `LoanViewSet`                                                       |
| Paginating inside an `@action`                                                                     | `AuthorViewSet.books`, `ShelfViewSet.books`, `LoanViewSet.overdue`                           |
| django-filter `FilterSet` (range, M2M by slug, method filters, filtering on annotations)           | `catalog/filters.py`, `library/filters.py`                                                   |
| `SearchFilter`, `OrderingFilter`                                                                   | most list views                                                                              |
| Custom filter backend (row-level visibility)                                                       | `library/filters.py` `OwnerOrPublicFilterBackend`                                            |
| Auth: Token (`authtoken`), Session, Basic; 401 vs 403 ordering                                     | `settings.py`, `api.py` `auth/token/`                                                        |
| Permissions: `IsAuthenticatedOrReadOnly`, `IsAuthenticated`, custom request-level and object-level | `core/permissions.py`, `ReviewViewSet`, `ShelfViewSet`                                       |
| Queryset scoping by user (`get_queryset`), `perform_create`                                        | `LoanViewSet`                                                                                |
| Throttling: anon/user defaults + `ScopedRateThrottle` on a single action                           | `settings.py`, `LoanViewSet.get_throttles`                                                   |
| Versioning: `URLPathVersioning` (`/api/v1/`), version-aware `reverse`                              | `urls.py`, `settings.py`                                                                     |
| Custom `APIException` (409) and custom `EXCEPTION_HANDLER`                                         | `core/exceptions.py`, `LoanViewSet.return_loan`                                              |
| OpenAPI schema + Swagger/Redoc (drf-spectacular), `extend_schema`, `inline_serializer`             | `api.py`, `core/views.py`                                                                    |
| Testing: `APIClient`, `force_authenticate`, `credentials()`, pytest fixtures                       | `conftest.py`, `apps/*/tests/`                                                               |

## Things to try

```bash
curl -s localhost:8000/api/v1/books/?genre=fantasy&available=true
curl -s "localhost:8000/api/v1/books/?search=asimov&ordering=-published_on&page_size=2"
curl -s localhost:8000/api/v1/publishers/?ordering=-book_count&limit=2
curl -s localhost:8000/api/v1/copies/?available=false
curl -s -u reader:password -X POST localhost:8000/api/v1/loans/ -H 'Content-Type: application/json' -d '{"copy": 3}'
curl -s -u reader:password -X POST localhost:8000/api/v1/loans/1/return/
curl -s localhost:8000/api/v2/ping/     # 404: version not allowed
```
