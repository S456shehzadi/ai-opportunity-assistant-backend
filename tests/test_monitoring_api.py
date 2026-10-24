"""Integration tests for monitoring and notification REST API endpoints."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_monitoring_preferences_flow(client: AsyncClient) -> None:
    """Verify GET and PUT for notification preferences."""
    # 1. Get default preferences
    get_res = await client.get("/api/v1/notifications/preferences")
    assert get_res.status_code == 200
    pref_data = get_res.json()
    assert pref_data["enable_notifications"] is True
    assert pref_data["daily_notification_limit"] == 5

    # 2. Update preferences
    update_payload = {
        "daily_notification_limit": 10,
        "enable_push": True,
        "important_changes_only": True,
        "quiet_hours_enabled": True,
        "quiet_hours_start": "23:00",
        "quiet_hours_end": "07:00",
    }
    put_res = await client.put("/api/v1/notifications/preferences", json=update_payload)
    assert put_res.status_code == 200
    updated_data = put_res.json()
    assert updated_data["daily_notification_limit"] == 10
    assert updated_data["enable_push"] is True
    assert updated_data["important_changes_only"] is True
    assert updated_data["quiet_hours_start"] == "23:00"


@pytest.mark.asyncio
async def test_search_monitoring_endpoints(client: AsyncClient) -> None:
    """Verify creating, listing, and deleting a monitored search query."""
    # 1. Create monitored search
    sub_payload = {
        "query": "Fulbright Scholarship Pakistan",
        "monitoring_frequency": "WEEKLY",
        "filters": {"category": "Scholarship"},
    }
    create_res = await client.post("/api/v1/searches/monitor", json=sub_payload)
    assert create_res.status_code == 201
    search_sub = create_res.json()
    assert search_sub["query"] == "Fulbright Scholarship Pakistan"
    search_id = search_sub["id"]

    # 2. List monitored searches
    list_res = await client.get("/api/v1/searches/monitored")
    assert list_res.status_code == 200
    searches = list_res.json()
    assert any(s["id"] == search_id for s in searches)

    # 3. Delete monitored search
    del_res = await client.delete(f"/api/v1/searches/monitor/{search_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "unsubscribed"

    # 4. Verify 404 on deleting again (user isolation / missing)
    del_again_res = await client.delete(f"/api/v1/searches/monitor/{search_id}")
    assert del_again_res.status_code == 404


@pytest.mark.asyncio
async def test_notifications_list_and_read(client: AsyncClient) -> None:
    """Verify notification listing, unread count, and read-all."""
    # 1. Check unread count
    count_res = await client.get("/api/v1/notifications/unread-count")
    assert count_res.status_code == 200
    assert "unread_count" in count_res.json()

    # 2. List notifications
    list_res = await client.get("/api/v1/notifications")
    assert list_res.status_code == 200
    assert isinstance(list_res.json(), list)

    # 3. Mark all as read
    read_all_res = await client.post("/api/v1/notifications/read-all")
    assert read_all_res.status_code == 200
    assert "marked_read" in read_all_res.json()


@pytest.mark.asyncio
async def test_opportunity_monitor_404_on_nonexistent(client: AsyncClient) -> None:
    """Verify subscribing to a non-existent opportunity returns 404."""
    fake_id = str(uuid.uuid4())
    res = await client.post(f"/api/v1/opportunities/{fake_id}/monitor")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()
