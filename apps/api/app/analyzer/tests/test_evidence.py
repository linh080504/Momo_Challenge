import asyncio
import importlib.util

import pytest
from conftest import REPO_ROOT

from app.analyzer.evidence import blacklist, domain_check, extract_urls, gather_evidence

KIT = REPO_ROOT / ".claude" / "skills" / "evidence-tools" / "scripts" / "domain_check.py"


def _kit():
    spec = importlib.util.spec_from_file_location("kit_domain_check", KIT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.skipif(not KIT.exists(), reason="kit script not present")
@pytest.mark.parametrize("url", ["https://vietcombank-xacminh.top/login", "bit.ly/abc", "http://192.168.1.1/x",
                                 "https://vietconbank.com", "shopee.vn/sale", "xn--vietcmbank-abc.com",
                                 "https://congan-hanoi.online", "https://vneid.gov.vn", "congan.hanoi.gov.vn",
                                 "http://dichvucong.gov.vn.verify-id.top"])
def test_port_matches_kit(url):
    assert domain_check.check(url) == _kit().check(url)


def test_gov_vn_is_official_in_port():
    for host in ("https://vneid.gov.vn", "congan.hanoi.gov.vn"):
        r = domain_check.check(host)
        assert r["level"] == "low" and r["signals"][0]["signal"] == "official"


def test_extract_urls_variants():
    text = ("Truy cập https://vietcombank-xacminh.top/login?id=1, hoặc www.shopee.vn, hoặc bit.ly/3abc. "
            "Email a@b.com không phải link. Số 5.000.000đ và tp.hcm cũng không.")
    hosts = [u.host for u in extract_urls(text)]
    assert hosts == ["vietcombank-xacminh.top", "www.shopee.vn", "bit.ly"]
    assert [u.official for u in extract_urls(text)] == [False, True, False]


def test_blacklist_snapshot_loaded_and_suffix_match():
    assert blacklist.snapshot_info()["size"] > 10000
    listed = next(iter(blacklist._domains()))
    assert blacklist.lookup(listed) == listed
    assert blacklist.lookup("abc." + listed) == listed
    assert blacklist.lookup("vietcombank.com.vn") is None
    assert blacklist.lookup("google.com") is None


def test_gather_evidence_parallel_and_findings():
    listed = sorted(blacklist._domains())[0]
    urls = extract_urls(f"Vào {listed} hoặc https://vietcombank-xacminh.top và https://momo.vn")
    items = asyncio.run(gather_evidence(urls))
    sigs = {(i.host, i.signal) for i in items}
    assert (listed, "community_blacklist") in sigs
    assert next(i for i in items if i.signal == "community_blacklist").source == "external_blacklist"
    assert ("vietcombank-xacminh.top", "domain_high") in sigs
    assert ("momo.vn", "official_domain") in sigs
    assert all(i.source in {"domain_check", "external_blacklist"} for i in items)


def test_tool_failure_is_skipped_not_safe(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("x")
    monkeypatch.setattr(domain_check, "check", boom)
    items = asyncio.run(gather_evidence(extract_urls("https://abc.xyz")))
    assert all(i.signal != "domain_low" for i in items)
