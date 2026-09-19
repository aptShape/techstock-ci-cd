"""Regression tests with a mocked MongoDB client; no running database required."""
import importlib.util
import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from bson.objectid import ObjectId
from fastapi.testclient import TestClient


@pytest.fixture
def application(monkeypatch):
    monkeypatch.setenv("MONGO_INITDB_ROOT_USERNAME", "test-user")
    monkeypatch.setenv("MONGO_INITDB_ROOT_PASSWORD", "test-password")
    monkeypatch.setenv("MONGO_DB", "configured_test_db")
    mongo = MagicMock()
    collection = mongo.__getitem__.return_value.items
    collection.count_documents.return_value = 1
    monkeypatch.setattr("pymongo.MongoClient", lambda *args, **kwargs: mongo)
    spec = importlib.util.spec_from_file_location(
        "techstock_test_app", Path(__file__).resolve().parents[1] / "main.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, mongo, collection


def test_configured_database_is_selected(application):
    _, mongo, _ = application
    mongo.__getitem__.assert_called_once_with("configured_test_db")


def test_missing_credentials_are_rejected(application, monkeypatch):
    module, _, _ = application
    for key in ("MONGO_INITDB_ROOT_USERNAME", "MONGO_INITDB_ROOT_PASSWORD"):
        with monkeypatch.context() as env:
            env.delenv(key)
            with pytest.raises(RuntimeError, match="must be set"):
                module.get_mongo_uri()


def test_credentials_are_url_encoded(application, monkeypatch):
    module, _, _ = application
    monkeypatch.setenv("MONGO_INITDB_ROOT_USERNAME", "user@company")
    monkeypatch.setenv("MONGO_INITDB_ROOT_PASSWORD", "p@ss:/?#")
    assert module.get_mongo_uri() == (
        "mongodb://user%40company:p%40ss%3A%2F%3F%23@localhost:27017/"
        "configured_test_db?authSource=admin"
    )


def test_connection_logs_do_not_expose_credentials(application, caplog, monkeypatch):
    module, _, _ = application
    with caplog.at_level(logging.INFO):
        module.connect_to_mongo()
        monkeypatch.setattr(
            module, "MongoClient",
            MagicMock(side_effect=RuntimeError("mongodb://test-user:test-password@host")),
        )
        with pytest.raises(RuntimeError, match="Failed to connect"):
            module.connect_to_mongo(max_retries=1)
    assert "test-password" not in caplog.text
    assert "mongodb://" not in caplog.text


def test_it_equipment_seed_only_for_empty_collection(application):
    module, _, collection = application
    collection.count_documents.return_value = 0
    with TestClient(module.app):
        pass
    seeded = collection.insert_many.call_args.args[0]
    assert [item["name"] for item in seeded] == [
        "Dell Latitude Laptop", "24-inch Monitor", "Mechanical Keyboard"
    ]
    assert all(set(item) == {"name", "price", "quantity"} for item in seeded)
    collection.reset_mock()
    collection.count_documents.return_value = 3
    with TestClient(module.app):
        pass
    collection.insert_many.assert_not_called()


def test_crud_and_quantity_routes_are_preserved(application):
    module, _, collection = application
    item_id = ObjectId()
    item = {"name": "Network Switch", "price": 149.0, "quantity": 4}
    collection.find.return_value = [{"_id": item_id, **item}]
    collection.insert_one.return_value.inserted_id = item_id
    collection.update_one.return_value.matched_count = 1
    collection.delete_one.return_value.deleted_count = 1

    with TestClient(module.app) as client:
        assert client.get("/api/items").json() == [{"_id": str(item_id), **item}]
        assert client.post("/api/items", json=item).json() == {"id": str(item_id)}
        collection.insert_one.assert_called_once_with(item)
        assert client.put(f"/api/items/{item_id}", json=item).status_code == 200
        collection.update_one.assert_called_with({"_id": item_id}, {"$set": item})
        for action, increment in (("add", 1), ("remove", -1)):
            assert client.put(
                f"/api/items/{item_id}/quantity", params={"action": action}
            ).status_code == 200
            collection.update_one.assert_called_with(
                {"_id": item_id}, {"$inc": {"quantity": increment}}
            )
        assert client.put(
            f"/api/items/{item_id}/quantity", params={"action": "invalid"}
        ).status_code == 400
        assert client.delete(f"/api/items/{item_id}").status_code == 200
        collection.delete_one.assert_called_once_with({"_id": item_id})
