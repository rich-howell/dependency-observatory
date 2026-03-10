import json

with open("data/alerts.json") as f:
    data = json.load(f)

lines = []

lines.append("# Dependency Dashboard")
lines.append("")
lines.append("| Repository | Dependabot Alerts |")
lines.append("|------------|-------------------|")

for repo in sorted(data, key=lambda x: x["repo"].lower()):

    alerts = repo["alert_count"]

    emoji = "🟢"

    if alerts > 0:
        emoji = "🔴"

    lines.append(f"| {repo['repo']} | {emoji} {alerts} |")

lines.append("")
lines.append("_Generated automatically by GitHub Actions_")

with open("dashboard.md", "w") as f:
    f.write("\n".join(lines))