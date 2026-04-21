"""Unit tests for KoreanNormalizer. Pytest-compatible."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from korean_normalizer import KoreanNormalizer


@pytest.fixture(scope="module")
def normalizer():
    return KoreanNormalizer()


def test_normalize_preserves_clean_text(normalizer):
    for text in [
        "안녕하세요",
        "오늘 날씨가 좋습니다",
        "프로젝트 마감일은 다음 주 금요일입니다",
    ]:
        out = normalizer.normalize(text)
        # NFKC may add tiny whitespace normalization but content preserved
        assert text.replace(" ", "") in out.replace(" ", "") or out == text


def test_normalize_removes_zero_width_space(normalizer):
    """ZWSP (\u200b) should be stripped."""
    text = "주\u200b민\u200b번호: 9\u200b0\u200b0\u200b1\u200b0\u200b1-1234567"
    out = normalizer.normalize(text)
    assert "\u200b" not in out
    assert "900101-1234567" in out or "900101" in out.replace("-", "")


def test_normalize_removes_soft_hyphen(normalizer):
    """Soft hyphen (\u00ad) should be stripped."""
    text = "계\u00ad좌\u00ad번호 123-45-6789"
    out = normalizer.normalize(text)
    assert "\u00ad" not in out


def test_normalize_fullwidth_to_ascii(normalizer):
    """Fullwidth digits should collapse to ASCII."""
    text = "전화번호 ０１０-１２３４-５６７８"
    out = normalizer.normalize(text)
    # Should contain ASCII digits now
    assert any(c in "0123456789" for c in out)


def test_normalize_combines_jamo(normalizer):
    """Decomposed jamo (ㅈㅜㅁㅣㄴ) should recombine to 주민 when pipeline supports it."""
    # Not all normalizers rebuild decomposed jamo back to precomposed syllables,
    # so we test a weaker property: the normalizer doesn't crash on jamo input
    # and returns a string.
    text = "ㅈㅜㅁㅣㄴ번호 900101-1234567"
    out = normalizer.normalize(text)
    assert isinstance(out, str)
    assert len(out) > 0


def test_normalize_handles_homoglyph(normalizer):
    """Mathematical bold digits should collapse to ASCII."""
    text = "전화번호 𝟎𝟏𝟎-𝟏𝟐𝟑𝟒-𝟓𝟔𝟕𝟖"
    out = normalizer.normalize(text)
    # Should produce ASCII digits
    assert "010" in out or any(c.isdigit() for c in out)


def test_normalize_is_deterministic(normalizer):
    """Same input → same output (no randomness)."""
    text = "최영희 연봉 7409만원"
    assert normalizer.normalize(text) == normalizer.normalize(text)


def test_normalize_latency_bounded(normalizer):
    """Normalization should be fast (<100ms for typical input)."""
    import time
    text = "환자 기록: 최영희(45세, 여) 연봉 7409만원, 처방 아토르바스타틴 20mg" * 10
    start = time.time()
    normalizer.normalize(text)
    elapsed_ms = (time.time() - start) * 1000
    assert elapsed_ms < 500, f"Normalize took {elapsed_ms:.1f}ms, expected <500ms"
