from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main
from app.api.routes import studies
from app.config import Settings


class FakeRepository:
    """测试用内存仓库，避免测试真正修改 MongoDB。"""

    def __init__(self):
        self.records = {}

    def save(self, collection, key, value):
        self.records[(collection, key)] = dict(value)

    def get(self, collection, key):
        value = self.records.get((collection, key))
        return dict(value) if value else None

    def list(self, collection, *, limit=50, offset=0):
        values = [
            value
            for (name, _), value in self.records.items()
            if name == collection
        ]
        values.sort(
            key=lambda value: value.get("created_at", datetime.min),
            reverse=True,
        )
        return values[offset : offset + limit]

    def count(self, collection):
        return sum(
            1 for name, _ in self.records if name == collection
        )

    def delete(self, collection, key):
        return self.records.pop((collection, key), None) is not None


@pytest.fixture
def client(tmp_path, monkeypatch):
    settings = Settings(
        data_dir=tmp_path / "data",
        model_dir=tmp_path / "models",
        allowed_file_extensions=".png",
        max_upload_mb=1,
    )

    settings.upload_dir.mkdir(parents=True)
    settings.processed_dir.mkdir(parents=True)

    repository = FakeRepository()

    monkeypatch.setattr(
        studies,
        "get_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        studies,
        "get_repository",
        lambda: repository,
    )

    # 测试时不连接真实 MongoDB、ChromaDB
    monkeypatch.setattr(
        main,
        "run_startup_checks",
        lambda _: {"storage": {"status": "ready"}},
    )
    monkeypatch.setattr(main, "close_repository", lambda: None)

    with TestClient(main.create_app(settings)) as test_client:
        yield test_client, settings


def test_study_file_lifecycle(client):
    test_client, settings = client
    content = b"fake-mri-image-data"

    # 1. 上传
    response = test_client.post(
        "/api/v1/studies",
        files={
            "file": (
                "scan.png",
                content,
                "image/png",
            )
        },
    )

    assert response.status_code == 201
    study = response.json()
    study_id = study["id"]

    # 2. 查询列表
    response = test_client.get("/api/v1/studies")
    assert response.status_code == 200
    assert response.json()["total"] == 1

    # 3. 查询详情
    response = test_client.get(f"/api/v1/studies/{study_id}")
    assert response.status_code == 200
    assert response.json()["filename"] == "scan.png"

    # 4. 下载文件
    response = test_client.get(
        f"/api/v1/studies/{study_id}/file"
    )
    assert response.status_code == 200
    assert response.content == content

    # 5. 确认本地文件存在
    stored_files = list(
        settings.upload_dir.glob(f"{study_id}.*")
    )
    assert len(stored_files) == 1
    assert stored_files[0].read_bytes() == content

    # 6. 删除
    response = test_client.delete(
        f"/api/v1/studies/{study_id}"
    )
    assert response.status_code == 204

    # 7. 确认详情不存在
    response = test_client.get(
        f"/api/v1/studies/{study_id}"
    )
    assert response.status_code == 404

    # 8. 确认本地文件也被删除
    assert not stored_files[0].exists()