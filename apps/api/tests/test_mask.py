"""Bảo vệ PII: bản port trong app/privacy phải cho kết quả GIỐNG skill pii-guard; hash thực thể ổn định."""
import importlib.util
import sys

import pytest

import hashlib
import hmac

from app.core.config import REPO_ROOT
from app.privacy.entities import MIN_KEY_CHARS, EntityHasher, display_value, normalize
from app.privacy.mask import Masker
from conftest import TEST_HASH_KEY

hasher = EntityHasher(TEST_HASH_KEY)

SKILL = REPO_ROOT / ".claude" / "skills" / "pii-guard" / "scripts" / "pii_mask.py"

SAMPLES = [
    "Chuyển 5.000.000đ vào STK 0123456789 Vietcombank, gọi 0912 345 678",
    "Mã OTP của bạn là 482913, CCCD 012345678901, email nguyen.van@gmail.com",
    "Thẻ 4111 1111 1111 1111 hết hạn 12/28; số tiền 200k và 5 triệu; 0912345678 và +84 912 345 678 là một",
    "Không có thông tin cá nhân nào ở đây.",
    "tk 1234567 (7 số, quá ngắn) và 12345678 (8 số)",
]


@pytest.mark.skipif(not SKILL.exists(), reason="không có skill pii-guard trong checkout này")
@pytest.mark.parametrize("sample", SAMPLES)
def test_port_matches_skill(sample):
    spec = importlib.util.spec_from_file_location("pii_mask_skill", SKILL)
    skill = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = skill
    spec.loader.exec_module(skill)
    expected = skill.mask_text(sample)
    masker = Masker()
    assert masker.mask(sample) == expected["masked"]
    assert masker.mapping == expected["mapping"]


def test_same_value_same_token_and_amounts_kept():
    masker = Masker()
    masked = masker.mask("STK 0123456789; lần nữa 0123456789; chuyển 50.000.000đ")
    assert masked.count("[ACCOUNT_1]") == 2 and "50.000.000đ" in masked and "0123456789" not in masked


def test_phone_variants_share_one_hash():
    variants = ["0912345678", "0912 345 678", "+84 912 345 678", "84912345678", "0912.345.678"]
    assert len({hasher.hash("PHONE", v) for v in variants}) == 1


def test_hash_is_hmac_sha256_over_type_and_normalized_value():
    expected = hmac.new(TEST_HASH_KEY.encode(), b"ACCOUNT:0123456789", hashlib.sha256).hexdigest()
    assert hasher.hash("ACCOUNT", "0123 456 789") == expected and len(expected) == 64


def test_hash_is_not_plain_sha256_and_depends_on_key():
    """Không dò ngược được bằng cách băm thử mọi số (SHA-256 trần) nếu không có khóa."""
    plain = hashlib.sha256(b"0123456789").hexdigest()
    keyed = hasher.hash("ACCOUNT", "0123456789")
    assert keyed != plain and plain[:12] not in keyed
    other = EntityHasher("another-key-another-key-another-key-xx")
    assert other.hash("ACCOUNT", "0123456789") != keyed


def test_same_digits_different_type_never_collide():
    assert hasher.hash("ACCOUNT", "0912345678") != hasher.hash("PHONE", "0912345678")


@pytest.mark.parametrize("key", ["", "ngan", "x" * (MIN_KEY_CHARS - 1)])
def test_short_or_empty_key_is_rejected(key):
    with pytest.raises(ValueError, match="ENTITY_HASH_KEY"):
        EntityHasher(key)


def test_key_never_appears_in_settings_repr(settings):
    assert TEST_HASH_KEY not in repr(settings) and TEST_HASH_KEY not in str(settings)


def test_url_normalized_to_host():
    assert normalize("URL", "https://WWW.Vcb-XacMinh.top/login?x=1") == "vcb-xacminh.top"
    assert hasher.hash("URL", "http://vcb-xacminh.top/a") == hasher.hash("URL", "https://www.vcb-xacminh.top/b")


def test_display_masks_phone_account_but_keeps_domain_in_full():
    assert display_value("ACCOUNT", "0123456789") == "0123****89"
    assert display_value("PHONE", "+84 912 345 678") == "0912****78"
    assert display_value("EMAIL", "Nguyen.Van@Gmail.com") == "n***@gmail.com"
    assert display_value("URL", "https://www.vcb-xacminh.top/x") == "vcb-xacminh.top"
    assert display_value("URL", "https://vcb-xacminh.top/login?token=abc123&uid=9") == "vcb-xacminh.top"  # bỏ tham số


def test_extract_entities_skips_otp_and_id_and_amounts():
    text = ("OTP 482913, CCCD 012345678901, chuyển 5.000.000đ vào 0123456789, gọi 0912345678, "
            "vào https://vcb-xacminh.top/login. hoặc www.vcb-xacminh.top, mail a@b.vn")
    masker = Masker()
    masker.mask(text)
    found = {(e.type, e.display) for e in hasher.extract(text, masker)}
    assert found == {("ACCOUNT", "0123****89"), ("PHONE", "0912****78"), ("URL", "vcb-xacminh.top"),
                     ("EMAIL", "a***@b.vn")}
