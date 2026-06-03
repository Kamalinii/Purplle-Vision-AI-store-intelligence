from .metrics import get_metrics


def status_for_score(score: int) -> str:
    if score >= 80:
        return "Excellent"
    if score >= 60:
        return "Good"
    if score >= 40:
        return "Average"
    return "Needs Attention"


async def get_health_score(store_id: str) -> dict:
    metrics = await get_metrics(store_id)

    # Blend positive business signals with operational penalties.
    raw_score = (
        metrics.conversion_rate * 50
        + min(metrics.unique_visitors, 50)
        - metrics.queue_depth * 2
        - metrics.abandonment_rate * 20
    )
    score = int(max(0, min(100, round(raw_score))))

    return {
        "score": score,
        "status": status_for_score(score),
    }
