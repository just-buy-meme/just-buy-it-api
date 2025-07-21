import uuid

from fastapi.testclient import TestClient

from app.core.config import settings


def test_create_item(client: TestClient) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/utils/health-check/"
    )
    assert response.status_code == 200
