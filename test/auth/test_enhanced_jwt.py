"""Test enhanced JWT validation features

Tests token fingerprinting, additional claims validation (nbf, aud, jti),
and backward compatibility with tokens that don't have enhanced features.
"""

import pytest
import jwt
from datetime import datetime, timedelta
from app.auth import AuthService, _generate_fingerprint
import hashlib


@pytest.fixture
def auth_service():
    """Create test auth service"""
    return AuthService(secret_key="test-enhanced-jwt-secret", token_store_path=":memory:")


def test_create_token_with_enhanced_claims(auth_service):
    """Test token creation includes enhanced security claims"""
    token = auth_service.create_token(
        group="test-group",
        expires_in_seconds=3600,
        fingerprint="test-fingerprint-123",
        token_id="unique-token-id-456",
    )

    # Decode without verification to inspect claims
    payload = jwt.decode(token, options={"verify_signature": False})

    assert payload["group"] == "test-group"
    assert "iat" in payload  # Issued at
    assert "exp" in payload  # Expires at
    assert "nbf" in payload  # Not before
    assert payload["aud"] == "gofr-api"  # Audience (gofr-common default)
    assert payload["jti"] == "unique-token-id-456"  # JWT ID
    assert payload["fp"] == "test-fingerprint-123"  # Fingerprint


def test_create_token_without_optional_claims(auth_service):
    """Test token creation works without optional claims"""
    token = auth_service.create_token(group="test-group", expires_in_seconds=3600)

    payload = jwt.decode(token, options={"verify_signature": False})

    assert payload["group"] == "test-group"
    assert "iat" in payload
    assert "exp" in payload
    assert "nbf" in payload
    assert payload["aud"] == "gofr-api"  # Audience (gofr-common default)
    assert "jti" not in payload  # Optional
    assert "fp" not in payload  # Optional


def test_verify_token_with_matching_fingerprint(auth_service):
    """Test token verification succeeds with matching fingerprint"""
    fingerprint = "device-fingerprint-abc123"
    token = auth_service.create_token(
        group="secure-group", expires_in_seconds=3600, fingerprint=fingerprint
    )

    # Verify with matching fingerprint
    token_info = auth_service.verify_token(token, fingerprint=fingerprint)

    assert token_info.group == "secure-group"
    assert token_info.token == token


def test_verify_token_with_mismatched_fingerprint(auth_service):
    """Test token verification fails with mismatched fingerprint"""
    original_fp = "device-fingerprint-abc123"
    token = auth_service.create_token(
        group="secure-group", expires_in_seconds=3600, fingerprint=original_fp
    )

    # Try to verify with different fingerprint
    different_fp = "different-device-xyz789"
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        auth_service.verify_token(token, fingerprint=different_fp)


def test_verify_token_without_fingerprint_claim(auth_service):
    """Test verification works for tokens without fingerprint claim"""
    token = auth_service.create_token(group="open-group", expires_in_seconds=3600)

    # Verify with fingerprint provided (should succeed - token has no fp claim)
    token_info = auth_service.verify_token(token, fingerprint="any-fingerprint")

    assert token_info.group == "open-group"


def test_verify_token_with_fingerprint_but_none_provided(auth_service):
    """Test verification succeeds when token has fingerprint but none provided"""
    fingerprint = "device-fingerprint-abc123"
    token = auth_service.create_token(
        group="secure-group", expires_in_seconds=3600, fingerprint=fingerprint
    )

    # Verify without providing fingerprint (should succeed - fingerprint optional)
    token_info = auth_service.verify_token(token, fingerprint=None)

    assert token_info.group == "secure-group"


def test_verify_token_validates_audience(auth_service):
    """Test token verification validates audience claim"""
    # Create token with correct audience
    auth_service.create_token(group="test-group", expires_in_seconds=3600)

    # Manually create token with wrong audience
    payload = {
        "group": "test-group",
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(seconds=3600)).timestamp()),
        "aud": "wrong-audience",
    }
    wrong_aud_token = jwt.encode(payload, auth_service.secret_key, algorithm="HS256")

    # Store it so it passes the store check
    auth_service.token_store[wrong_aud_token] = {
        "group": "test-group",
        "issued_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(seconds=3600)).isoformat(),
        "not_before": datetime.utcnow().isoformat(),
    }
    auth_service._save_token_store()

    # Should fail audience validation
    with pytest.raises(ValueError, match="audience mismatch"):
        auth_service.verify_token(wrong_aud_token)


def test_verify_token_backward_compatible_no_audience(auth_service):
    """Test verification works for old tokens without audience claim"""
    # Create old-style token without audience
    payload = {
        "group": "legacy-group",
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(seconds=3600)).timestamp()),
    }
    legacy_token = jwt.encode(payload, auth_service.secret_key, algorithm="HS256")

    # Store it
    auth_service.token_store[legacy_token] = {
        "group": "legacy-group",
        "issued_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(seconds=3600)).isoformat(),
    }
    auth_service._save_token_store()

    # Should succeed (backward compatible)
    token_info = auth_service.verify_token(legacy_token)
    assert token_info.group == "legacy-group"


def test_verify_token_respects_not_before(auth_service):
    """Test token verification respects not-before timestamp"""
    # Create token valid in the future
    now = datetime.utcnow()
    future = now + timedelta(seconds=3600)
    way_future = future + timedelta(seconds=7200)

    payload = {
        "group": "future-group",
        "iat": int(now.timestamp()),
        "nbf": int(future.timestamp()),  # Not valid until 1 hour from now
        "exp": int(way_future.timestamp()),
        "aud": "gofr-plot-api",
    }
    future_token = jwt.encode(payload, auth_service.secret_key, algorithm="HS256")

    # Store it
    auth_service.token_store[future_token] = {
        "group": "future-group",
        "issued_at": now.isoformat(),
        "expires_at": way_future.isoformat(),
        "not_before": future.isoformat(),
    }
    auth_service._save_token_store()

    # Should fail - not yet valid
    with pytest.raises(ValueError, match="not yet valid"):
        auth_service.verify_token(future_token)


def test_token_metadata_includes_enhanced_fields(auth_service):
    """Test token store metadata includes enhanced security fields"""
    fingerprint = "device-fp-123"
    token_id = "unique-id-456"

    token = auth_service.create_token(
        group="metadata-group",
        expires_in_seconds=3600,
        fingerprint=fingerprint,
        token_id=token_id,
    )

    # Check stored metadata
    metadata = auth_service.token_store[token]

    assert metadata["group"] == "metadata-group"
    assert "issued_at" in metadata
    assert "expires_at" in metadata
    assert "not_before" in metadata
    assert metadata["fingerprint"] == fingerprint
    assert metadata["jti"] == token_id


def test_generate_fingerprint_from_request():
    """Test fingerprint generation from request context"""

    # Create mock request
    class MockClient:
        host = "192.168.1.100"

    class MockHeaders(dict):
        def get(self, key, default=None):
            return super().get(key, default)

    class MockRequest:
        client = MockClient()
        headers = MockHeaders({"user-agent": "Mozilla/5.0 Test Browser"})

    request = MockRequest()

    # Generate fingerprint
    fp1 = _generate_fingerprint(request)  # type: ignore[arg-type]

    # Should be deterministic
    fp2 = _generate_fingerprint(request)  # type: ignore[arg-type]
    assert fp1 == fp2

    # Should be SHA256 hash (64 hex chars)
    assert len(fp1) == 64
    assert all(c in "0123456789abcdef" for c in fp1)

    # Different request should give different fingerprint
    request2 = MockRequest()
    request2.client.host = "192.168.1.101"  # Different IP
    fp3 = _generate_fingerprint(request2)  # type: ignore[arg-type]
    assert fp3 != fp1


def test_generate_fingerprint_handles_missing_data():
    """Test fingerprint generation handles missing user-agent or IP"""

    class MockRequest:
        client = None  # No client info
        headers = {}

    request = MockRequest()

    # Should not crash, use defaults
    fp = _generate_fingerprint(request)  # type: ignore[arg-type]
    assert len(fp) == 64

    # Fingerprint for "unknown:unknown"
    expected = hashlib.sha256("unknown:unknown".encode()).hexdigest()
    assert fp == expected


def test_verify_token_validates_group_consistency(auth_service):
    """Test verification checks group matches between token and store"""
    token = auth_service.create_token(group="original-group", expires_in_seconds=3600)

    # Tamper with stored metadata
    auth_service.token_store[token]["group"] = "different-group"
    auth_service._save_token_store()

    # Should fail - group mismatch
    with pytest.raises(ValueError, match="group mismatch"):
        auth_service.verify_token(token)


def test_backward_compatibility_with_old_tokens(auth_service):
    """Test that old tokens without enhanced claims still work"""
    # Create minimal old-style token
    payload = {
        "group": "old-style-group",
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(seconds=3600)).timestamp()),
    }
    old_token = jwt.encode(payload, auth_service.secret_key, algorithm="HS256")

    # Store with minimal metadata
    auth_service.token_store[old_token] = {
        "group": "old-style-group",
        "issued_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(seconds=3600)).isoformat(),
    }
    auth_service._save_token_store()

    # Should verify successfully
    token_info = auth_service.verify_token(old_token)
    assert token_info.group == "old-style-group"

    # Should also work with fingerprint provided (token has no fp claim)
    token_info2 = auth_service.verify_token(old_token, fingerprint="any-fp")
    assert token_info2.group == "old-style-group"
