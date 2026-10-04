import heapq
from typing import Dict, List, Tuple


def dijkstra(
    graph: Dict[str, Dict[str, float]], source: str, destination: str
) -> Tuple[float, List[str]]:
    """Return (total_distance, path) for the shortest route source -> destination.

    If no route exists, returns (float("inf"), []).
    """
    if source not in graph or destination not in graph:
        return float("inf"), []

    pq: List[Tuple[float, str, List[str]]] = [(0.0, source, [source])]
    visited = set()

    while pq:
        cost, node, path = heapq.heappop(pq)

        if node in visited:
            continue
        visited.add(node)

        if node == destination:
            return cost, path

        for neighbour, weight in graph.get(node, {}).items():
            if neighbour not in visited:
                heapq.heappush(pq, (cost + weight, neighbour, path + [neighbour]))

    return float("inf"), []


def all_distances(graph: Dict[str, Dict[str, float]], source: str) -> Dict[str, float]:
    """Shortest distance from `source` to every reachable node (used for charts)."""
    dist = {node: float("inf") for node in graph}
    if source not in graph:
        return dist
    dist[source] = 0.0
    pq: List[Tuple[float, str]] = [(0.0, source)]

    while pq:
        cost, node = heapq.heappop(pq)
        if cost > dist[node]:
            continue
        for neighbour, weight in graph.get(node, {}).items():
            new_cost = cost + weight
            if new_cost < dist[neighbour]:
                dist[neighbour] = new_cost
                heapq.heappush(pq, (new_cost, neighbour))

    return dist
