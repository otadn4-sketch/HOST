from app.services.delivery import AutomatedDeliveryService
from app.services.faran import FaranClient
from app.services.document_scrub import plan_scrub


def test_automated_delivery_is_disabled():
    service = AutomatedDeliveryService()
    assert service.enabled is False
    try:
        service.send_link()
        assert False, "automated send must raise"
    except RuntimeError as exc:
        assert "منسوخ" in str(exc)


def test_faran_client_is_offline_stub():
    client = FaranClient()
    status = client.status()
    assert status["mode"] == "stub"
    ping = client.ping()
    assert ping["ok"] is False


def test_document_scrub_plan_is_stub():
    plan = plan_scrub(["strip_recipient_details"])
    assert plan["applied"] is False
    assert plan["status"] == "stub"
