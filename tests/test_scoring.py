import pytest
from src.scoring import score_career_link, score_job_link


def test_score_career_link_matches_keywords():
    score, evidence = score_career_link("https://stripe.com/careers", "Careers at Stripe")
    assert score >= 5
    assert any("career" in e.lower() for e in evidence)


def test_score_career_link_no_match():
    score, _ = score_career_link("https://stripe.com/about", "About us")
    assert score == 0


def test_score_job_link_matches_keywords():
    score, evidence = score_job_link("https://stripe.com/jobs/backend", "Backend Engineer")
    assert score >= 3
    assert any("engineer" in e.lower() for e in evidence)


def test_score_job_link_no_match():
    score, _ = score_job_link("https://stripe.com/about", "About Stripe")
    assert score == 0
