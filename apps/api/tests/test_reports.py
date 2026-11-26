import copy
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.models import Entity, Report, ReportEntity
from app.privacy.entities import EntityHasher
from app.services.reports import purge_expired_content
from conftest import SAMPLE_RESULT, TEST_HASH_KEY, assert_error

entity_hash = EntityHasher(TEST_HASH_KEY).hash

ACCOUNT, PHONE = "0123456789", "0912345678"
TEXT = (f"Tôi là cán bộ công an, chuyển 50.000.000đ vào STK {ACCOUNT} Vietcombank, "
        f"gọi 0912 345 678 hoặc vào http://vcb-xacminh.top/login ngay.")


def analysis_with_pii():
    result = copy.deepcopy(SAMPLE_RESULT)
    result["summary"] = f"Yêu cầu chuyển tiền vào tài khoản {ACCOUNT} của người lạ."
    result["red_flags"] = [{"quote": f"gọi 0912 345 678 hoặc vào STK {ACCOUNT}", "reason": "Giục chuyển tiền gấp.",
                            "tactic": "urgency"}]
    return result


def db_rows(app, model):
    with app.state.session_factory() as session:
        return session.scalars(select(model)).all()


# ---------- tạo báo cáo ----------

def test_report_without_consent_stores_hashes_but_no_content(client, app, settings):
    response = client.post("/v1/reports", json={"text": TEXT, "analysis": analysis_with_pii()})
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "new" and body["entities_linked"] == 3 and body["content_stored"] is False

    (report,) = db_rows(app, Report)
    assert report.consent_contribute is False
    assert report.content_masked is None and report.red_flags_masked is None and report.content_expires_at is None
    assert (report.risk_level, report.risk_score, report.scenario_group, report.scenario_id) == ("high", 92, "G1", "G1.2")
    assert ACCOUNT not in report.summary and "[ACCOUNT_1]" in report.summary

    raw = open(settings.database_url.removeprefix("sqlite:///"), "rb").read()
    # STK, SĐT và văn bản người dùng không nằm trong file DB (tên miền thì có — quyết định PM).
    for secret in (ACCOUNT.encode(), PHONE.encode(), "công an".encode(), b"/login", b"http://"):
        assert secret not in raw, secret
    assert TEST_HASH_KEY.encode() not in raw  # khóa HMAC không bao giờ vào DB


def test_entities_are_hashed_masked_and_pending(client, app):
    client.post("/v1/reports", json={"text": TEXT})
    entities = {(e.type, e.value_hash): e for e in db_rows(app, Entity)}
    assert set(entities) == {("ACCOUNT", entity_hash("ACCOUNT", ACCOUNT)), ("PHONE", entity_hash("PHONE", PHONE)),
                             ("URL", entity_hash("URL", "vcb-xacminh.top"))}
    assert entities[("ACCOUNT", entity_hash("ACCOUNT", ACCOUNT))].display == "0123****89"
    assert entities[("URL", entity_hash("URL", "vcb-xacminh.top"))].display == "vcb-xacminh.top"  # tên miền đầy đủ
    assert all(len(e.value_hash) == 64 for e in entities.values())  # HMAC-SHA256 đủ 64 hex
    # AI/endpoint báo cáo không được tự đưa thực thể vào danh sách đen: tất cả phải ở `pending`.
    assert {e.status for e in entities.values()} == {"pending"}
    assert all(e.report_count == 1 for e in entities.values())


def test_report_with_consent_stores_masked_content_with_expiry(client, app):
    response = client.post("/v1/reports", json={"text": TEXT, "analysis": analysis_with_pii(),
                                                "consent_contribute": True})
    assert response.status_code == 201 and response.json()["content_stored"] is True
    (report,) = db_rows(app, Report)
    assert report.consent_contribute is True
    assert "[ACCOUNT_1]" in report.content_masked and "[PHONE_1]" in report.content_masked
    assert ACCOUNT not in report.content_masked and PHONE not in report.content_masked
    assert "vcb-xacminh.top" in report.content_masked  # tên miền không phải PII, vận hành cần thấy
    flag = report.red_flags_masked[0]
    assert ACCOUNT not in flag["quote"] and "[ACCOUNT_1]" in flag["quote"] and "[PHONE_1]" in flag["quote"]
    expires = report.content_expires_at.replace(tzinfo=timezone.utc)
    assert abs((expires - datetime.now(timezone.utc)) - timedelta(days=30)) < timedelta(minutes=1)


def test_same_entity_in_two_reports_is_one_row_with_count_2(client, app):
    client.post("/v1/reports", json={"text": f"Chuyển vào STK {ACCOUNT} ngay"})
    client.post("/v1/reports", json={"text": f"Anh ơi gửi tiền vào {ACCOUNT} nhé, gọi 0912345678"})
    entities = {e.type: e for e in db_rows(app, Entity)}
    assert set(entities) == {"ACCOUNT", "PHONE"}
    assert entities["ACCOUNT"].report_count == 2 and entities["PHONE"].report_count == 1
    assert len(db_rows(app, ReportEntity)) == 3


def test_same_entity_twice_in_one_report_counts_once(client, app):
    client.post("/v1/reports", json={"text": f"STK {ACCOUNT}. Nhắc lại: STK {ACCOUNT}"})
    (entity,) = db_rows(app, Entity)
    assert entity.report_count == 1


def test_report_without_entities_is_ok(client, app):
    response = client.post("/v1/reports", json={"text": "Mẹ ơi con sắp về."})
    assert response.status_code == 201 and response.json()["entities_linked"] == 0
    assert db_rows(app, Entity) == []


# ---------- đầu vào sai ----------

def test_missing_text_is_422(client):
    assert_error(client.post("/v1/reports", json={}), 422, "validation_error")


def test_blank_text_is_422(client):
    assert_error(client.post("/v1/reports", json={"text": "  \n"}), 422, "missing_input")


def test_text_too_long_is_422(client):
    assert_error(client.post("/v1/reports", json={"text": "a" * 10_001}), 422, "text_too_long")


def test_analysis_not_matching_schema_is_422_and_nothing_stored(client, app):
    bad = copy.deepcopy(SAMPLE_RESULT)
    bad["risk_level"] = "safe"
    assert_error(client.post("/v1/reports", json={"text": TEXT, "analysis": bad}), 422, "invalid_analysis")
    assert db_rows(app, Report) == [] and db_rows(app, Entity) == []


# ---------- hết hạn nội dung ----------

def test_purge_expired_content_keeps_hashes_and_risk(client, app):
    client.post("/v1/reports", json={"text": TEXT, "analysis": analysis_with_pii(), "consent_contribute": True})
    with app.state.session_factory() as session:
        assert purge_expired_content(session) == 0  # chưa hết hạn
        assert purge_expired_content(session, now=datetime.now(timezone.utc) + timedelta(days=31)) == 1
        assert purge_expired_content(session, now=datetime.now(timezone.utc) + timedelta(days=31)) == 0
    (report,) = db_rows(app, Report)
    assert report.content_masked is None and report.red_flags_masked is None and report.risk_level == "high"
    assert len(db_rows(app, Entity)) == 3
