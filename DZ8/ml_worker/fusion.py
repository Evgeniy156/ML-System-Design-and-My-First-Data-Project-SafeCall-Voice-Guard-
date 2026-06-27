"""Fusion scoring — ported from safecall_train/fusion.py (ДЗ7 §11).

ML-only accuracy: 67% on real-world files → ML+Fusion: 100%.
Combines ML spoof_probability with context signals (codec, VoIP, IP risk).
"""
import logging

logger = logging.getLogger(__name__)


def fusion_score(
    ml_prob: float,
    codec: str = "unknown",
    is_voip: bool = False,
    ip_risk: float = 0.0,
    duration: float = 0.0,
    threshold: float = 0.37,
) -> dict:
    """Combine ML probability with rule-based signals.

    Args:
        ml_prob: Raw spoof probability from XLSR-53 model
        codec: Audio codec (e.g. 'opus', 'amr', 'pcm')
        is_voip: Whether the call is from a VoIP number
        ip_risk: IP reputation score (0.0 = clean, 1.0 = malicious)
        duration: Audio duration in seconds
        threshold: Classification threshold

    Returns:
        dict with fused verdict, adjusted probability, and signal breakdown
    """
    adjustments = {}
    adjusted_prob = ml_prob

    # Codec signal: lossy codecs common in deepfake delivery
    risky_codecs = {"opus", "amr", "silk", "speex"}
    if codec.lower() in risky_codecs:
        adjusted_prob += 0.05
        adjustments["codec_boost"] = 0.05

    # VoIP signal: deepfake calls often use VoIP
    if is_voip:
        adjusted_prob += 0.08
        adjustments["voip_boost"] = 0.08

    # IP risk signal
    if ip_risk > 0.5:
        boost = min(ip_risk * 0.1, 0.1)
        adjusted_prob += boost
        adjustments["ip_risk_boost"] = round(boost, 4)

    # Short duration signal: very short clips may be spliced
    if 0 < duration < 1.5:
        adjusted_prob += 0.03
        adjustments["short_duration_boost"] = 0.03

    adjusted_prob = min(adjusted_prob, 1.0)
    is_spoof = adjusted_prob >= threshold

    return {
        "verdict": "SPOOF" if is_spoof else "REAL",
        "ml_probability": round(ml_prob, 4),
        "fused_probability": round(adjusted_prob, 4),
        "is_spoof": is_spoof,
        "adjustments": adjustments,
        "threshold": threshold,
    }
