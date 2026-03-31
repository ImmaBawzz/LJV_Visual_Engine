"""
Repository Statistics Collection

Collects and stores repository metrics for tracking growth and engagement.
Stores results in 03_WORK/reports/repo_stats.json
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime


def fetch_github_stats(repo_owner: str, repo_name: str) -> dict:
    """Fetch repository statistics from GitHub API."""
    repo_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
    
    try:
        response = requests.get(repo_url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching GitHub stats: {e}")
    
    return {}


def fetch_issue_stats(repo_owner: str, repo_name: str) -> dict:
    """Fetch issue and PR statistics."""
    base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
    
    stats = {
        'open_issues': 0,
        'open_prs': 0,
        'total_issues': 0,
        'total_prs': 0,
        'good_first_issues': 0
    }
    
    try:
        # Get open issues
        issues_url = f"{base_url}/issues?state=open"
        response = requests.get(issues_url, timeout=10)
        if response.status_code == 200:
            issues = response.json()
            stats['open_issues'] = len(issues)
            stats['good_first_issues'] = sum(
                1 for issue in issues 
                if 'good first issue' in [label['name'].lower() for label in issue.get('labels', [])]
            )
        
        # Get PRs
        prs_url = f"{base_url}/pulls?state=open"
        response = requests.get(prs_url, timeout=10)
        if response.status_code == 200:
            stats['open_prs'] = len(response.json())
            
    except Exception as e:
        print(f"Error fetching issue stats: {e}")
    
    return stats


def collect_stats() -> dict:
    """Collect all repository statistics."""
    repo_owner = "ImmaBawzz"
    repo_name = "LJV_Visual_Engine"
    
    stats = {
        'collected_at': datetime.utcnow().isoformat(),
        'repository': f"{repo_owner}/{repo_name}",
    }
    
    # GitHub API stats
    github_stats = fetch_github_stats(repo_owner, repo_name)
    if github_stats:
        stats.update({
            'stars': github_stats.get('stargazers_count', 0),
            'forks': github_stats.get('forks_count', 0),
            'watchers': github_stats.get('watchers_count', 0),
            'size': github_stats.get('size', 0),
            'language': github_stats.get('language', ''),
            'license': github_stats.get('license', {}).get('spdx_id', ''),
            'created_at': github_stats.get('created_at', ''),
            'updated_at': github_stats.get('updated_at', ''),
            'pushed_at': github_stats.get('pushed_at', ''),
            'topics': github_stats.get('topics', []),
            'open_issues_count': github_stats.get('open_issues_count', 0),
        })
    
    # Issue-specific stats
    issue_stats = fetch_issue_stats(repo_owner, repo_name)
    stats.update(issue_stats)
    
    return stats


def save_stats(stats: dict, output_path: str):
    """Save statistics to JSON file."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
        print(f"Statistics saved to {output_path}")
    except Exception as e:
        print(f"Error saving stats: {e}")


def main():
    """Main execution function."""
    # Determine output path
    base_path = Path(__file__).parent.parent.parent
    output_path = base_path / '03_WORK' / 'reports' / 'repo_stats.json'
    
    # Collect statistics
    print("Collecting repository statistics...")
    stats = collect_stats()
    
    if not stats:
        print("Failed to collect statistics")
        return
    
    # Save statistics
    save_stats(stats, str(output_path))
    
    # Print summary
    print("\nRepository Statistics Summary:")
    print(f"  Stars: {stats.get('stars', 'N/A')}")
    print(f"  Forks: {stats.get('forks', 'N/A')}")
    print(f"  Open Issues: {stats.get('open_issues', 'N/A')}")
    print(f"  Good First Issues: {stats.get('good_first_issues', 'N/A')}")
    print(f"  Open PRs: {stats.get('open_prs', 'N/A')}")
    print(f"  Language: {stats.get('language', 'N/A')}")
    print(f"  Topics: {', '.join(stats.get('topics', []))}")


if __name__ == '__main__':
    main()