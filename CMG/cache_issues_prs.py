from Agent_tools import PullRequestCollectingTool, IssueCollectingTool
import cache_manager
from tqdm import tqdm

all_links = list(cache_manager.git_diff_cache.keys())
all_links = [str(link) for link in all_links]
issue_tool = IssueCollectingTool()  
pr_tool = PullRequestCollectingTool()

issues_collected = 0
prs_collected = 0

for link in tqdm(all_links, desc='Collecting issues and PRs'):
    if link in cache_manager.issues_prs_cache:
        continue

    issues = issue_tool(link)
    if issues:
        issues_collected += 1
    
    prs = pr_tool(link)
    if prs:
        prs_collected += 1

    cache_manager.store_issues(link, issues)
    cache_manager.store_prs(link, prs)

for link in cache_manager.issues_prs_cache.keys():
    issues = cache_manager.get_issues(link)
    prs = cache_manager.get_prs(link)
    if issues.startswith('There is no') and prs.startswith('There is no'):
        continue
    print(link)
    issues_collected += 1
    prs_collected += 1
    print('Issues:', cache_manager.get_issues(link))
    print('PRs:', cache_manager.get_prs(link))
    print('---'*30)

print(f'Issues collected: {issues_collected}')
print(f'PRs collected: {prs_collected}')