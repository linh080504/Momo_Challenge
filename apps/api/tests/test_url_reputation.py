import httpx
from fastapi.testclient import TestClient

from app.auth.security import Limits
from app.config import Settings
from app.evidence import reputation
from app.evidence.url_gateway import inspect_url
from app.main import create_app


def test_reputation_only_sends_registration_root_to_virustotal(monkeypatch, tmp_path):
    url = "https://news.example.org/notice?token=private-test-value"
    urlhaus = tmp_path / "urlhaus.txt"
    urlhaus.write_text("# sample\n" + url + "\n", encoding="utf-8")
    phishtank = tmp_path / "phishing.csv"
    phishtank.write_text("url,verified,online\n" + url + ",no,yes\n"
                        "https://www.example.com/test,yes,yes\n", encoding="utf-8")
    settings = Settings(_env_file=None, virustotal_api_key="fixture-key",
                        urlhaus_feed_path=str(urlhaus), phishtank_feed_path=str(phishtank))

    def lookup(endpoint, **kwargs):
        assert endpoint == "https://www.virustotal.com/api/v3/domains/example.org"
        assert kwargs["follow_redirects"] is False
        return httpx.Response(200, request=httpx.Request("GET", endpoint), json={
            "data": {"attributes": {"last_analysis_stats": {"malicious": 1}}},
        })

    monkeypatch.setattr(reputation.httpx, "get", lookup)
    result = reputation.check_reputation(url, inspect_url(url), settings, Limits())
    assert {key: row["status"] for key, row in result.items()} == {
        "virustotal": "checked", "urlhaus": "match", "phishtank": "clear",
    }


def test_website_reports_exact_feed_hit_without_marking_other_paths(tmp_path):
    url = "https://example.org/test"
    feed = tmp_path / "phishing.csv"
    feed.write_text("url,verified,online\n" + url + ",yes,yes\n", encoding="utf-8")
    database = (tmp_path / "reputation.sqlite3").as_posix()
    settings = Settings(_env_file=None, database_url=f"sqlite:///{database}", phishtank_feed_path=str(feed))

    with TestClient(create_app(settings)) as client:
        result = client.post("/v1/analyze", json={"url": url, "website_preview": True}).json()
        assert result["risk_level"] == "high"
        assert result["website_report"]["reputation"]["phishtank"]["status"] == "match"
        diff = client.post("/v1/analyze", json={"url": url + "-other", "website_preview": True}).json()
        assert diff["website_report"]["reputation"]["phishtank"]["status"] == "clear"
        assert diff["risk_level"] != "high"
