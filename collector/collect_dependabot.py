import requests
import json
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

DEPENDENCY_FILES = [
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "go.mod",
    "Cargo.toml",
    "pubspec.yaml",
    "composer.json",
    "Gemfile",
    "pom.xml",
    "build.gradle"
]

def get_pull_requests(repo):

    url = f"https://api.github.com/repos/{repo}/pulls?state=open"

    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        return []

    return r.json()

def get_repo_files(repo):

    url = f"https://api.github.com/repos/{repo}/contents"

    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        return []

    return [f["name"] for f in r.json()]

def get_dependabot_updates(repo):

    url = f"https://api.github.com/repos/{repo}/pulls?state=open"

    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        return 0

    pulls = r.json()

    count = 0

    for pr in pulls:

        user = pr["user"]["login"]

        if user == "dependabot[bot]":
            count += 1

    return count

def get_action_updates(repo):

    url = f"https://api.github.com/repos/{repo}/pulls?state=open"

    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        return 0

    pulls = r.json()

    count = 0

    for pr in pulls:

        if pr["user"]["login"] == "dependabot[bot]":

            title = pr["title"].lower()

            if "github-actions" in title or ".github/workflows" in title:
                count += 1

    return count


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


def get_alerts(repo):

    url = f"https://api.github.com/repos/{repo}/dependabot/alerts"

    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        return []

    return r.json()


def repo_has_dependencies(files):

    for dep in DEPENDENCY_FILES:

        if dep in files:
            return True

    for f in files:

        if f.endswith(".csproj"):
            return True

    return False


def detect_stack(files):

    if "pubspec.yaml" in files:
        return "Flutter"

    if "package.json" in files:
        return "Node"

    if "requirements.txt" in files or "pyproject.toml" in files:
        return "Python"

    if "composer.json" in files:
        return "PHP"

    if any(f.endswith(".csproj") for f in files):
        return "C#"

    return "Unknown"

def main():

    repos = get_repos()

    results = []

    with ThreadPoolExecutor(max_workers=10) as executor:

        futures = [executor.submit(scan_repo, repo) for repo in repos]

        for future in as_completed(futures):

            try:
                result = future.result()

                if result:
                    results.append(result)

            except Exception as e:
                print(f"Error scanning repo: {e}")

    # Ensure docs directory exists
    os.makedirs("docs", exist_ok=True)

    output = {
        "generated": datetime.utcnow().isoformat(),
        "repos": results
    }

    with open("docs/dashboard.json", "w") as f:
        json.dump(output, f, indent=2)

def scan_repo(repo):

    name = repo["full_name"]

    if repo["name"] == ".github":
        return None

    print(f"Scanning {name}")

    alerts = get_alerts(name)

    files = get_repo_files(name)

    has_deps = repo_has_dependencies(files)

    stack = detect_stack(files)

    prs = get_pull_requests(name)

    updates = sum(1 for pr in prs if pr["user"]["login"] == "dependabot[bot]")

    actions = sum(
        1
        for pr in prs
        if pr["user"]["login"] == "dependabot[bot]"
        and (
            "github-actions" in pr["title"].lower()
            or ".github/workflows" in pr["title"].lower()
        )
    )

    return {
        "repo": name,
        "org": repo["owner"]["login"],
        "stack": stack,
        "dependencies": has_deps,
        "alert_count": len(alerts),
        "updates": updates,
        "actions": actions
    }

if __name__ == "__main__":
    main()