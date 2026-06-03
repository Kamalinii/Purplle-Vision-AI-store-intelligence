from .metrics import get_metrics


async def get_alerts(store_id: str) -> list[dict]:
    metrics = await get_metrics(store_id)
    alerts = []

    if metrics.queue_depth > 5:
        alerts.append({
            "severity": "high",
            "message": "Queue congestion detected near billing area",
        })

    if metrics.abandonment_rate > 0.20:
        alerts.append({
            "severity": "high",
            "message": "Customers are leaving before checkout",
        })

    if metrics.conversion_rate < 0.30 and metrics.unique_visitors > 0:
        alerts.append({
            "severity": "medium",
            "message": "Low conversion rate observed",
        })

    if metrics.unique_visitors >= 20:
        alerts.append({
            "severity": "low",
            "message": "Traffic surge detected",
        })

    return alerts
