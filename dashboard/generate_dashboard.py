import json
from collections import defaultdict

with open("data/alerts.json") as f:
    data = json.load(f)

stack_icons = {
    "Flutter": "🐦 Flutter",
    "Python": "🐍 Python",
    "Node": "🟢 Node",
    "C#": "⚙ C#",
    "PHP": "🐘 PHP",
    "Unknown": "—"
}

orgs = defaultdict(list)

for repo in data:
    orgs[repo["org"]].append(repo)

total_repos = len(data)
repos_with_deps = sum(1 for r in data if r["dependencies"])
total_alerts = sum(r["alert_count"] for r in data)

lines = []

lines.append("# 🛰 Dependency Observatory")
lines.append("")
lines.append(f"Repositories scanned: **{total_repos}**  ")
lines.append(f"Repositories with dependencies: **{repos_with_deps}**  ")
lines.append(f"Total alerts: **{total_alerts}**  ")
lines.append("")
lines.append("---")
lines.append("")

for org in sorted(orgs):

    lines.append(f"## {org}")
    lines.append("")
    lines.append("| Repo | Stack | Dependencies | Security | Updates | Actions |")
    lines.append("|-----|-----|-----|-----|-----|-----|")

    for repo in sorted(orgs[org], key=lambda x: x["repo"].lower()):

        repo_name = repo["repo"].split("/")[1]

        repo_url = f"https://github.com/{repo['repo']}"

        stack = stack_icons.get(repo["stack"], "—")

        deps = "📦" if repo["dependencies"] else "—"

        security = "🟢 0"
        if repo["alert_count"] > 0:
            security = f"🔴 {repo['alert_count']}"

        updates = "🟢 0"
        if repo["updates"] > 0:
            updates = f"🟡 {repo['updates']}"

        actions = "🟢 0"
        if repo["actions"] > 0:
            actions = f"🟡 {repo['actions']}"

        lines.append(
            f"| [{repo_name}]({repo_url}) | {stack} | {deps} | {security} | {updates} | {actions} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")

lines.append("_Generated automatically by GitHub Actions_")

with open("dashboard.md", "w") as f:
    f.write("\n".join(lines))