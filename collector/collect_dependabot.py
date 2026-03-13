import requests
import json
import os
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

DEPENDENCY_FILES = [
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "bun.lockb",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "Pipfile",
    "Pipfile.lock",
    "poetry.lock",
    "uv.lock",
    "go.mod",
    "go.sum",
    "Cargo.toml",
    "Cargo.lock",
    "pubspec.yaml",
    "pubspec.lock",
    "composer.json",
    "composer.lock",
    "Gemfile",
    "Gemfile.lock",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "settings.gradle.kts",
    "Directory.Packages.props",
    "packages.config",
    "packages.lock.json"
]

LANGUAGE_TO_STACK = {
    "JavaScript": "Node",
    "TypeScript": "Node",
    "Python": "Python",
    "PHP": "PHP",
    "C#": "C#",
    "Java": "Java",
    "Kotlin": "Kotlin",
    "Go": "Go",
    "Rust": "Rust",
    "Ruby": "Ruby",
    "Dart": "Dart"
}

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

        if r.status_code != 200:
            print(f"Failed to list repos (page {page}): {r.status_code} {r.text}")
            break

        data = r.json()

        if not isinstance(data, list):
            print(f"Unexpected response while listing repos on page {page}: {type(data).__name__}")
            break

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


def repo_has_dependencies(files, stack="Unknown", updates=0, alert_count=0):

    normalized = {f.lower() for f in files}

    for dep in DEPENDENCY_FILES:

        if dep.lower() in normalized:
            return True

    for f in normalized:

        if f.endswith((".csproj", ".fsproj", ".vbproj")):
            return True

    # If Dependabot is already reporting updates/alerts, dependencies exist.
    if updates > 0 or alert_count > 0:
        return True

    # Language-based fallback helps repos where manifests are nested.
    if stack in {"Node", "Python", "PHP", "C#", "Java", "Kotlin", "Go", "Rust", "Ruby", "Flutter", "Dart"}:
        return True

    return False


def detect_stack(files, repo_language=None):

    normalized = {f.lower() for f in files}

    if "pubspec.yaml" in normalized:
        return "Flutter"

    if "package.json" in normalized:
        return "Node"

    if "requirements.txt" in normalized or "pyproject.toml" in normalized:
        return "Python"

    if "composer.json" in normalized:
        return "PHP"

    if any(f.endswith(".csproj") for f in normalized):
        return "C#"

    if repo_language in LANGUAGE_TO_STACK:
        return LANGUAGE_TO_STACK[repo_language]

    return "Unknown"

def main():

    # Always emit dashboard.json, even when auth is missing/invalid.
    os.makedirs("docs", exist_ok=True)

    if not GITHUB_TOKEN:
        print("GITHUB_TOKEN is empty. Writing empty dashboard payload.")
        output = {
            "generated": datetime.now(timezone.utc).isoformat(),
            "repos": [],
            "error": "Missing GITHUB_TOKEN"
        }
        with open("docs/dashboard.json", "w") as f:
            json.dump(output, f, indent=2)
        return

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

    output = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "repos": sorted(results, key=lambda item: item["repo"].lower())
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

    stack = detect_stack(files, repo.get("language"))

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

    has_deps = repo_has_dependencies(
        files,
        stack=stack,
        updates=updates,
        alert_count=len(alerts)
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
