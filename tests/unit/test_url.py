from __future__ import annotations

import pytest

from opportunities.utils.url import UnsafeUrlError, canonicalize_url, validate_linkedin_job_url


def test_public_url_canonicalization_removes_tracking_and_normalizes_host() -> None:
    assert (
        canonicalize_url("https://EXAMPLE.com:443/jobs/role/?utm_source=test&b=2&a=1#details")
        == "https://example.com/jobs/role?a=1&b=2"
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/jobs/role",
        "https://localhost/jobs/role",
        "https://internal.local/jobs/role",
        "https://bad_host.example/jobs/role",
        "javascript:alert(1)",
    ],
)
def test_public_url_canonicalization_rejects_unsafe_targets(url: str) -> None:
    with pytest.raises(UnsafeUrlError):
        canonicalize_url(url)


def test_linkedin_listing_url_must_match_the_canonical_job_id() -> None:
    assert (
        validate_linkedin_job_url(
            "https://www.linkedin.com/jobs/view/1111111111?trk=public_jobs",
            "1111111111",
        )
        == "https://www.linkedin.com/jobs/view/1111111111"
    )

    with pytest.raises(UnsafeUrlError, match="does not match"):
        validate_linkedin_job_url(
            "https://www.linkedin.com/jobs/view/2222222222",
            "1111111111",
        )
