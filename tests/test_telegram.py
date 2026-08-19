def test_telegram_status(client):
    """Verifies Telegram status endpoint."""
    res = client.get("/api/telegram/status")
    assert res.status_code == 200
    data = res.get_json()
    assert "bot_username" in data
    assert data["bot_username"] == "jarvis_prime_remote_bot"
    assert "has_token" in data

def test_telegram_save_config(client):
    """Verifies saving Telegram bot token and chat ID."""
    res = client.post("/api/telegram/save-config", json={
        "bot_token": "8206363312:AAH7sjVsT4nj7YtDUceWPRoOCa9d1cM6X6U",
        "chat_id": "123456789"
    })
    assert res.status_code == 200
    assert res.get_json()["success"] is True

    # Check updated status
    status_res = client.get("/api/telegram/status")
    assert status_res.get_json()["chat_id"] == "123456789"
    assert status_res.get_json()["configured"] is True
