import jwt
import pytest
from auth import issue_token, refresh_token, validate_token


def test_refresh_accepts_refresh_token():
    assert refresh_token(issue_token("refresh"))["refreshed"] is True


def test_refresh_rejects_access_token():
    with pytest.raises(ValueError, match="token kind mismatch"):
        refresh_token(issue_token("access"))


def test_invalid_signature_stays_rejected():
    forged = jwt.encode({"sub": "synthetic-user", "kind": "refresh"}, "another-synthetic-key-000000000000000", algorithm="HS256")
    with pytest.raises(jwt.InvalidSignatureError):
        refresh_token(forged)


@pytest.mark.parametrize("case_id", range(80))
def test_access_diagnostic(case_id):
    assert validate_token(issue_token("access"), "access")["sub"] == "synthetic-user"
    print(f"diagnostic={case_id:03d} token_kind=access signature=valid subject=synthetic-user route=access status=accepted")
