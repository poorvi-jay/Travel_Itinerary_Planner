"""
Geographic Clustering — Sprint 3.

Groups activities into `trip_request.days` day-buckets by lat/long
proximity using k-means, then rebalances cluster sizes so no day ends up
empty while another is overloaded. Kept as its own module so it can be
built/tested independently of the within-day time-window scheduling
(PRD Section 12) before the two are combined in the Scheduler Agent.
"""
from __future__ import annotations
import math

from models import Activity


def cluster_by_day(activities: list[Activity], num_days: int) -> list[list[Activity]]:
    """
    Returns a list of `num_days` lists of Activity, one per day, assigned
    by geographic proximity via k-means. If there are fewer activities
    than days, the extra days start empty (rebalancing can still fill them
    from an overloaded day).
    """
    if not activities:
        return [[] for _ in range(num_days)]

    from sklearn.cluster import KMeans
    import numpy as np

    k = min(num_days, len(activities))
    coords = np.array([[a.lat, a.long] for a in activities])
    labels = KMeans(n_clusters=k, n_init=10, random_state=0).fit_predict(coords)

    clusters: list[list[Activity]] = [[] for _ in range(num_days)]
    for activity, label in zip(activities, labels):
        clusters[label].append(activity)

    return _rebalance(clusters, num_days)


def _rebalance(clusters: list[list[Activity]], num_days: int) -> list[list[Activity]]:
    """Moves activities off overloaded days onto the least-full day until
    every day is within one of the even split, so k-means's occasional
    lopsided clusters don't leave a day empty while another is swamped."""
    total = sum(len(c) for c in clusters)
    if total == 0:
        return clusters
    max_per_day = math.ceil(total / num_days) + 1

    for cluster in clusters:
        while len(cluster) > max_per_day:
            centroid = _centroid(cluster)
            farthest = max(cluster, key=lambda a: _dist(a, centroid))
            cluster.remove(farthest)
            target = min(range(num_days), key=lambda d: len(clusters[d]))
            clusters[target].append(farthest)

    return clusters


def _centroid(activities: list[Activity]) -> tuple[float, float]:
    return (
        sum(a.lat for a in activities) / len(activities),
        sum(a.long for a in activities) / len(activities),
    )


def _dist(a: Activity, point: tuple[float, float]) -> float:
    return ((a.lat - point[0]) ** 2 + (a.long - point[1]) ** 2) ** 0.5
