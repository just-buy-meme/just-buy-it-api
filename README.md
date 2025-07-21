## Development

### Docker compose for development
```bash
docker compose watch
```
Automatic interactive documentation with Swagger UI (from the OpenAPI backend):
-  http://localhost:8888/docs

for details see [backend/README.md](backend/README.md)


### Pre-commits and code linting
```bash
uv run pre-commit install
```

### Package install
```bash
uv add $PACKAGE
```

### Testing
```bash
docker compose build
docker compose up -d
docker compose exec -T backend bash scripts/tests-start.sh
```
