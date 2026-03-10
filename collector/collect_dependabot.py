import requests
import json
import os

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

def get_repos():
    repos = []
    page = 1

    while True:
        url = f"https://api.github.com/user/repos?per_page=100&page={page}"
        r = requests.get(url, headers=headers)

        data = r.json()

        if not data:
            break

        repos.extend(data)
        page += 1

    return repos


def get_alerts(repo_full_name):

    url = f"https://api.github.com/repos/{repo_full_name}/dependabot/alerts"

    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        return []

    return r.json()


def main():

    repos = get_repos()

    results = []

    for repo in repos:

        name = repo["full_name"]

        print(f"Scanning {name}")

        alerts = get_alerts(name)

        results.append({
            "repo": name,
            "alert_count": len(alerts)
        })

    os.makedirs("data", exist_ok=True)

    with open("data/alerts.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()