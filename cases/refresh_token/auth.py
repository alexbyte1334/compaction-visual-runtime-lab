"""Intentionally buggy learning fixture; never use as a production auth service."""
import jwt

# Public, synthetic fixture constant. This is not a credential.
DEMO_KEY = "synthetic-test-only-key-never-for-production-000000"


def issue_token(kind):
    return jwt.encode({"sub": "synthetic-user", "kind": kind}, DEMO_KEY, algorithm="HS256")


def validate_token(token, expected_kind):
    claims = jwt.decode(token, DEMO_KEY, algorithms=["HS256"])
    if claims["kind"] != expected_kind:
        raise ValueError("token kind mismatch")
    return claims


def refresh_token(token):
    # Bug: this endpoint should validate a refresh token.
    claims = validate_token(token, expected_kind="access")
    return {"sub": claims["sub"], "refreshed": True}
