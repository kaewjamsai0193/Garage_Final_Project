"""เทสต์ของ app/core/security.py — แฮชรหัสผ่านและ JWT

อยู่ในกลุ่มที่ต้องมีเทสต์เพราะพังแบบเงียบ ๆ โทเคนที่ลายเซ็นผิดหรือหมดอายุแล้ว
หน้าตาเหมือนโทเคนดีทุกประการ ต้องถอดออกมาดูถึงจะรู้
"""

import jwt
import pytest

from app.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_is_not_the_password():
    """แฮชต้องไม่ใช่รหัสผ่านเดิม"""
    assert hash_password("รหัสผ่าน123") != "รหัสผ่าน123"


def test_same_password_hashes_differently():
    """bcrypt สุ่ม salt ใหม่ทุกครั้ง คนที่ขโมยฐานข้อมูลไปจึงดูไม่ออกว่าใครใช้รหัสซ้ำกัน"""
    assert hash_password("รหัสผ่าน123") != hash_password("รหัสผ่าน123")


def test_verify_accepts_correct_and_rejects_wrong_password():
    """รหัสถูกต้องผ่าน รหัสผิดไม่ผ่าน"""
    password_hash = hash_password("รหัสผ่าน123")
    assert verify_password("รหัสผ่าน123", password_hash) is True
    assert verify_password("รหัสผ่าน124", password_hash) is False


def test_thai_password_longer_than_72_bytes_still_works():
    """ตัวอักษรไทยกิน 3 ไบต์ 25 ตัวก็ชนเพดานของ bcrypt แล้ว ต้องตัดให้ตรงกันทั้งตอนแฮชและตอนตรวจ"""
    password = "ก" * 40  # 120 ไบต์
    password_hash = hash_password(password)
    assert verify_password(password, password_hash) is True


def test_token_carries_user_id_and_role():
    """โทเคนต้องเก็บ id กับบทบาทไว้ให้ dependency เอาไปตรวจสิทธิ์ต่อ"""
    payload = decode_access_token(create_access_token(7, "mechanic"))
    assert payload["sub"] == "7"
    assert payload["role"] == "mechanic"


def test_token_signed_with_another_secret_is_rejected():
    """ปลอมโทเคนด้วยกุญแจอื่นแล้วต้องถอดไม่ผ่าน ไม่งั้นใครก็อ้างเป็น admin ได้"""
    forged = jwt.encode(
        {"sub": "1", "role": "admin"}, "กุญแจปลอม", algorithm=settings.jwt_algorithm
    )
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(forged)


def test_expired_token_is_rejected(monkeypatch):
    """โทเคนหมดอายุต้องถูกปฏิเสธ ไม่ใช่ใช้ได้ตลอดชีพ"""
    monkeypatch.setattr(settings, "jwt_expire_minutes", -1)
    expired = create_access_token(1, "admin")
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired)
