from .dwell import get_average_dwell_per_zone
from .metrics import get_metrics


async def get_recommendations(store_id: str) -> list[dict]:
    metrics = await get_metrics(store_id)
    dwell_by_zone = await get_average_dwell_per_zone(store_id)
    recommendations = []

    if metrics.queue_depth > 3:
        recommendations.append({
            "title": "Open an additional billing counter",
            "reason": f"Queue depth reached {metrics.queue_depth}",
        })

    if metrics.abandonment_rate > 0.15:
        recommendations.append({
            "title": "Reduce checkout friction",
            "reason": f"Queue abandonment increased to {metrics.abandonment_rate * 100:.1f}%",
        })

    if dwell_by_zone:
        zone_id, dwell_ms = max(dwell_by_zone.items(), key=lambda item: item[1])
        recommendations.append({
            "title": f"Deploy staff near {zone_id.replace('_', ' ').title()}",
            "reason": f"Highest average dwell time observed at {format_duration(dwell_ms)}",
        })

    if metrics.conversion_rate < 0.30 and metrics.unique_visitors > 0:
        recommendations.append({
            "title": "Review product placement in high-traffic areas",
            "reason": f"Conversion rate is {metrics.conversion_rate * 100:.1f}%",
        })

    if metrics.unique_visitors >= 20:
        recommendations.append({
            "title": "Increase staffing during peak period",
            "reason": f"Traffic spike detected with {metrics.unique_visitors} visitors",
        })

    return recommendations


def format_duration(ms: float) -> str:
    seconds = int(ms // 1000)
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes}m {seconds}s"
