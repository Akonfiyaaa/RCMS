import math
import os
import torch
import torch.nn.functional as F
from datetime import datetime, timezone
from torch_geometric.data import Data
from torch_geometric.nn import GCNConv
import numpy as np

MODEL_PATH = r"D:\Ahad\Final_year_project\gnn_model\gnn_model.pth"

# =========================
# ⏱️ Timestamp / age helper
# =========================
def complaint_age_hours(complaint):
    ts = complaint.get("timestamp")

    if ts is None:
        return 0.0

    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts)
        except Exception:
            return 0.0

    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    else:
        return 0.0

    now = datetime.now(timezone.utc)
    age = now - ts
    return max(age.total_seconds() / 3600.0, 0.0)


# =========================
# 📏 Distance (Haversine in meters)
# =========================
def distance_m(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# =========================
# 🔗 Build Graph
# =========================
def build_graph(complaints):
    x = []
    edge_index = []

    for c in complaints:
        x.append([
            float(c.get("severity", 0)),
            float(c.get("traffic", 0)),
            float(c.get("priority", 0)),
            float(complaint_age_hours(c)),
        ])

    for i, c1 in enumerate(complaints):
        for j, c2 in enumerate(complaints):
            if i == j:
                continue

            d = distance_m(
                c1["latitude"], c1["longitude"],
                c2["latitude"], c2["longitude"]
            )

            if d <= 150:  # 🔥 Slightly relaxed (better connectivity)
                edge_index.append([i, j])

    x_tensor = torch.tensor(x, dtype=torch.float)

    if len(edge_index) == 0:
        edge_tensor = torch.empty((2, 0), dtype=torch.long)
    else:
        edge_tensor = torch.tensor(edge_index, dtype=torch.long).t().contiguous()

    return Data(x=x_tensor, edge_index=edge_tensor)


# =========================
# 🧠 GNN Model
# =========================
class GNN(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = GCNConv(4, 32)
        self.conv2 = GCNConv(32, 16)
        self.conv3 = GCNConv(16, 1)

    def forward(self, data):
        x, edge_index = data.x, data.edge_index

        x = self.conv1(x, edge_index)
        x = F.relu(x)

        x = self.conv2(x, edge_index)
        x = F.relu(x)

        x = self.conv3(x, edge_index)

        return x.view(-1)  

def load_pretrained_gnn_model(path=MODEL_PATH):
    model = GNN()
    if not os.path.exists(path):
        raise FileNotFoundError(f"Pretrained GNN model not found at {path}")

    state = torch.load(path, map_location=torch.device("cpu"))
    model.load_state_dict(state)
    model.eval()
    return model


# =========================
# 📊 Density fallback
# =========================
def compute_density(complaints):
    densities = []

    for i, c in enumerate(complaints):
        count = 0

        for j, other in enumerate(complaints):
            if i == j:
                continue

            d = distance_m(
                c["latitude"], c["longitude"],
                other["latitude"], other["longitude"]
            )

            if d <= 150:
                count += 1

        densities.append(count)

    return densities


# =========================
# 🔥 FIXED CLUSTERING (ROBUST)
# =========================
def cluster_complaints(complaints, threshold=250):
    if not complaints:
        return []

    clusters = []
    visited = set()

    for i, c in enumerate(complaints):
        if i in visited:
            continue

        cluster = [c]
        visited.add(i)

        for j, other in enumerate(complaints):
            if j in visited:
                continue

            d = distance_m(
                c["latitude"], c["longitude"],
                other["latitude"], other["longitude"]
            )

            if d <= threshold:
                cluster.append(other)
                visited.add(j)
        print("\n🧩 STEP 3: CLUSTER CONTENT")
        for c in cluster:
            print("CLUSTER MEMBER:", {
                "id": c.get("id"),
                "username": c.get("username"),
                "gnn_score": c.get("gnn_score")
                })

        clusters.append(cluster)

    # 🔥 SAFETY: if clustering fails, return each as its own cluster
    if len(clusters) == 0:
        return [[c] for c in complaints]

    return clusters


# =========================
# 🎨 Zone classification
# =========================
def get_zone(score):
    if score >= 8:
        return "red"
    elif score >= 4:
        return "yellow"
    else:
        return "green"


# =========================
# 🚀 MAIN GNN
# =========================
def run_gnn(complaints):
    if not complaints:
        return complaints

    data = build_graph(complaints)

    try:
        model = load_pretrained_gnn_model()
        with torch.no_grad():
            output = model(data).view(-1).tolist()
        output = np.array(output)
        # normalize to 0–1 using min-max
        min_val = output.min()
        max_val = output.max()
        if max_val - min_val == 0:
            scores = [5.0] * len(output)
        else:
            scores = ((output - min_val) / (max_val - min_val)) * 10
            scores = scores.tolist()

    except Exception as e:
        print("⚠️ Pretrained GNN unavailable, using density fallback:", e)

        densities = compute_density(complaints)
        max_d = max(densities) if max(densities) != 0 else 1
        scores = [(d / max_d) * 10 for d in densities]

    densities = compute_density(complaints)

    for i, c in enumerate(complaints):
        c["density"] = densities[i]
        c["gnn_score"] = round(scores[i], 2)
        c["zone"] = get_zone(c["gnn_score"])

    return complaints


# =========================
# 📦 FORMAT OUTPUT
# =========================
def format_clusters(clusters):
    def cluster_score(c):
        return (
            c.get("avg_priority", 0) * 0.4 +
            c.get("avg_severity", 0) * 0.4 +
            c.get("count", 0) * 0.2
        )
    result = []

    cluster_scores = [
        sum(c.get("gnn_score", 5) for c in cluster) / len(cluster)
        for cluster in clusters
    ]

    max_cluster_score = max(cluster_scores) if max(cluster_scores) != 0 else 1

    for cluster in clusters:
        size = len(cluster)

        avg_lat = sum(c["latitude"] for c in cluster) / size
        avg_lng = sum(c["longitude"] for c in cluster) / size

        avg_severity = sum(c.get("severity", 0) for c in cluster) / size
        max_severity = max(c.get("severity", 0) for c in cluster)

        avg_priority = sum(c.get("priority", 0) for c in cluster) / size

        status_counts = {"to-do": 0, "in progress": 0, "done": 0}
        for c in cluster:
            s = str(c.get("status", "to-do")).lower()
            if s in status_counts:
                status_counts[s] += 1

        raw_avg = sum(c.get("gnn_score", 5) for c in cluster) / size
        avg_score = (raw_avg / max_cluster_score) * 10

        members = []
        for c in cluster:
            members.append({
                
                "id": c.get("id"),
                "username": c.get("username", "unknown"),
                "latitude": c.get("latitude"),
                "longitude": c.get("longitude"),
                "severity": c.get("severity", 0),
                "priority": c.get("priority", 0),
                "status": c.get("status", "to-do"),
                "image": c.get("image"),
                "timestamp": c.get("timestamp"),
                "gnn_score": c.get("gnn_score", 0),
                "density": c.get("density", 0),
            })

        max_priority = max(c.get("priority", 0) for c in cluster)
        max_gnn = max(c.get("gnn_score", 0) for c in cluster)

        result.append({
            "latitude": avg_lat,
            "longitude": avg_lng,
            "count": size,
            "avg_severity": round(avg_severity, 2),
            "max_severity": max_severity,
            "avg_priority": round(avg_priority, 2),
            "highest_priority": round(max_priority, 2),
            "max_gnn_score": round(max_gnn, 2),
            "urgency_score": round(avg_score, 2),
            "status_summary": status_counts,
            "zone": get_zone(avg_score),
            "avg_score": round(avg_score, 2),
            "members": members,
        })
        
    # ensure safe values (NO None)
    # safety cleanup
    for c in result:
        c["avg_priority"] = c.get("avg_priority") 
        c["avg_severity"] = c.get("avg_severity") 
        c["count"] = c.get("count")

    # FINAL SORT
    result.sort(key=cluster_score, reverse=True)

    return result
# =========================
# 🔥 FINAL PIPELINE
# =========================


def run_gnn_and_cluster(complaints):
    if not complaints:
        return []

    complaints = run_gnn(complaints)

    clusters = cluster_complaints(complaints)

    # 🔥 DEBUG (optional, remove later)
    print("📊 TOTAL COMPLAINTS:", len(complaints))
    print("📊 TOTAL CLUSTERS:", len(clusters))

    formatted = format_clusters(clusters)
    
    return formatted