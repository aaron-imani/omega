import os
import re
from getpass import getpass

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from github import Github
from github.GithubException import GithubException
from requests import get

load_dotenv("./.env", verbose=True)

github_token = os.getenv("GITHUB_API_TOKEN")

if github_token is None:
    github_token = getpass("Enter your github token: ")

g = Github(github_token)


def _get_commit_info(commit_url):
    match = re.search(
        r"https?://github\.com/([^/]+/[^/]+)/commit/([a-f0-9]+)", commit_url
    )
    if not match:
        raise ValueError(f"Invalid commit URL: {commit_url}")

    repo_name = match.group(1)
    commit_id = match.group(2)
    return repo_name, commit_id


def _extract_url(commit_url):
    match = re.search(
        r"(https?://github\.com/[^/]+/[^/]+/commit/[a-f0-9]+)", commit_url
    )
    if not match:
        raise ValueError(f"Invalid commit URL: {commit_url}")

    return match.group(1)


def _get_content_before_hr(content):
    # This regex matches any content before a horizontal line of dashes
    match = re.search(r"^(.*?)(?=\n-{4,})", content, re.DOTALL)
    if match:
        return match.group(1)
    return content


def get_pr_content(commit_url):
    # commit_sha = commit_url.split("/")[-1]
    # repo_name = "/".join(commit_url.split("github.com")[1].split('/')[1:3])
    repo_name, commit_sha = _get_commit_info(commit_url)
    repo = g.get_repo(repo_name)
    try:
        commit = repo.get_commit(commit_sha)
    except GithubException:
        return "Invalid commit URL. Please use the original commit URL provided by the user."
    pr = commit.get_pulls()
    pr = list(pr)
    if not pr:
        return None

    pr = pr[0]
    content = []
    body = _get_content_before_hr(pr.body)
    content.append(f"Title: {pr.title}")
    content.append(f"Body: {body}")

    return "\n".join(content).strip()


def get_github_issue_content(commit_url):
    # commit_sha = commit_url.split("/")[-1]
    # repo_name = "/".join(commit_url.split("github.com")[1].split('/')[1:3])
    repo_name, commit_sha = _get_commit_info(commit_url)
    repo = g.get_repo(repo_name)
    try:
        commit = repo.get_commit(commit_sha)
    except GithubException as ge:
        print(ge.status)
        return "Invalid commit URL. Please use the original commit URL provided by the user."

    commit_message = commit.commit.message
    issue_numbers = re.findall(r" #(\d+)", commit_message)
    if not issue_numbers:
        return None

    content = []
    for issue_number in issue_numbers:
        try:
            issue = repo.get_issue(int(issue_number))
            content.append(f"Issue ID: {issue.number}")
            content.append(f"Title: {issue.title}")
            body = _get_content_before_hr(issue.body)
            content.append(f"Body: {body.strip()}")
            content.append("\n")
        except Exception:
            continue
    if not content:
        return None

    return "\n".join(content).strip()


def get_jira_issue_content(commit_url):
    commit_url = _extract_url(commit_url)
    commit_page = get(commit_url)
    soup = BeautifulSoup(commit_page.content, "html.parser")
    jira_issue_links = soup.find_all("a", class_="issue-link js-issue-link notranslate")
    jira_issue_links = [link for link in jira_issue_links if "jira" in link["href"]]
    if not jira_issue_links:
        return None

    content = []
    for link in jira_issue_links:
        jira_issue_page = get(link["href"])
        jira_soup = BeautifulSoup(jira_issue_page.content, "html.parser")
        issue_title = jira_soup.find("h1", id="summary-val").text
        description = jira_soup.find("div", id="description-val").text
        issue_id = link.text
        content.append("Issue ID: " + issue_id)
        content.append(f"Title: {issue_title}")
        content.append(f"Body: {description.strip()}")
        content.append("\n")

    if content:
        response = "Here are the Jira issues linked to this commit:\n"
        response += "\n".join(content).strip()
        response += "\nPlease consider them when writing the commit message."
        return response
    else:
        return None


if __name__ == "__main__":
    commit_url = (
        "https://github.com/apache/beam/commit/f1c6846f1bcc15207927aa704a8091b768003c1a"
    )
    print(get_pr_content(commit_url))
