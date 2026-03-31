"""
Configure GitHub Repository Topics

This script updates the GitHub repository topics to improve discoverability.
Requires GitHub token with repo permissions.
"""

import os
import requests
from typing import List


def update_repository_topics(token: str, owner: str, repo: str, topics: List[str]) -> bool:
    """
    Update GitHub repository topics.
    
    Args:
        token: GitHub personal access token
        owner: Repository owner (username or organization)
        repo: Repository name
        topics: List of topics to add
        
    Returns:
        True if successful, False otherwise
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/topics"
    
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    data = {
        'names': topics
    }
    
    try:
        response = requests.put(url, headers=headers, json=data)
        
        if response.status_code == 200:
            print(f"✅ Successfully updated topics for {owner}/{repo}")
            print(f"Topics: {', '.join(topics)}")
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.json()}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


def get_current_topics(token: str, owner: str, repo: str) -> List[str]:
    """Get current repository topics."""
    url = f"https://api.github.com/repos/{owner}/{repo}"
    
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('topics', [])
        else:
            print(f"Error fetching topics: {response.status_code}")
            return []
    except Exception as e:
        print(f"Exception: {e}")
        return []


def main():
    """Main execution function."""
    # Configuration
    owner = "ImmaBawzz"
    repo = "LJV_Visual_Engine"
    
    # Topics to add
    new_topics = [
        "music-visualization",
        "lyric-video",
        "audio-reactive",
        "ffmpeg",
        "python",
        "video-pipeline",
        "music-production",
        "whisper-asr",
        "checkpoint-recovery",
        "batch-processing",
        "quality-assurance",
        "music-tech",
        "audio-synchronization",
        "subtitle-automation",
        "video-production"
    ]
    
    # Get GitHub token
    token = os.getenv('GITHUB_TOKEN')
    
    if not token:
        print("❌ GITHUB_TOKEN not set in environment")
        print("Please set GITHUB_TOKEN environment variable or pass it as argument")
        return
    
    # Get current topics
    print(f"Fetching current topics for {owner}/{repo}...")
    current_topics = get_current_topics(token, owner, repo)
    
    if current_topics:
        print(f"Current topics: {', '.join(current_topics)}")
    
    # Update topics
    print(f"\nUpdating topics...")
    success = update_repository_topics(token, owner, repo, new_topics)
    
    if success:
        print("\n✅ Repository topics updated successfully!")
        print("\nNext steps:")
        print("1. Verify topics on GitHub: https://github.com/ImmaBawzz/LJV_Visual_Engine")
        print("2. Check repository discoverability in GitHub search")
        print("3. Monitor traffic in repository Insights tab")
    else:
        print("\n❌ Failed to update topics")
        print("Check token permissions and try again")


if __name__ == '__main__':
    main()