"""
Environment-Based Credential Manager

Provides alternative credential sources and management without
requiring direct API key configuration in GitHub secrets.
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


class CredentialManager:
    """
    Manages credentials from multiple sources.
    
    Priority order:
    1. Environment variables (highest)
    2. .env file
    3. Local credential store
    4. Mock/fallback credentials
    """
    
    def __init__(self, workspace_path: Optional[str] = None):
        """
        Initialize credential manager.
        
        Args:
            workspace_path: Base path for credential storage
        """
        if workspace_path is None:
            workspace_path = Path(__file__).parent.parent
        
        self.workspace_path = Path(workspace_path)
        self.env_file_path = self.workspace_path / '.env'
        self.credential_store_path = self.workspace_path / '03_WORK' / 'temp' / 'credentials.json'
        
        # Ensure credential store directory exists
        self.credential_store_path.parent.mkdir(parents=True, exist_ok=True)
        
    def get_credential(self, key: str, use_mock: bool = True) -> Optional[str]:
        """
        Get credential with fallback chain.
        
        Args:
            key: Credential key name
            use_mock: If True, use mock when no real credential found
            
        Returns:
            Credential value or mock/fallback
        """
        # Try environment variable
        env_value = os.getenv(key)
        if env_value:
            print(f"✅ Loaded '{key}' from environment variable")
            return env_value
        
        # Try .env file
        env_file_value = self._load_from_env_file(key)
        if env_file_value:
            print(f"✅ Loaded '{key}' from .env file")
            return env_file_value
        
        # Try credential store
        store_value = self._load_from_store(key)
        if store_value:
            print(f"✅ Loaded '{key}' from credential store")
            return store_value
        
        # Use mock/fallback
        if use_mock:
            mock_value = self._generate_mock_credential(key)
            print(f"🔧 Using mock credential for '{key}'")
            return mock_value
        
        print(f"❌ No credential found for '{key}'")
        return None
    
    def _load_from_env_file(self, key: str) -> Optional[str]:
        """Load credential from .env file."""
        if not self.env_file_path.exists():
            return None
        
        with open(self.env_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}="):
                    value = line.split('=', 1)[1].strip()
                    return value
        
        return None
    
    def _load_from_store(self, key: str) -> Optional[str]:
        """Load credential from local credential store."""
        if not self.credential_store_path.exists():
            return None
        
        with open(self.credential_store_path, 'r') as f:
            credentials = json.load(f)
            return credentials.get(key)
    
    def _generate_mock_credential(self, key: str) -> str:
        """Generate a mock credential for testing."""
        if 'OPENAI' in key:
            return "sk-mock-" + hashlib.md5(key.encode()).hexdigest()[:32]
        elif 'PINEcone' in key:
            return "mock-pinecone-key-" + hashlib.md5(key.encode()).hexdigest()[:16]
        else:
            return "mock-" + hashlib.md5(key.encode()).hexdigest()
    
    def save_to_env_file(self, credentials: Dict[str, str]):
        """
        Save credentials to .env file.
        
        Args:
            credentials: Dictionary of key-value pairs
        """
        lines = []
        
        # Read existing content
        if self.env_file_path.exists():
            with open(self.env_file_path, 'r') as f:
                lines = f.readlines()
        
        # Add/update credentials
        with open(self.env_file_path, 'w') as f:
            # Write existing lines
            f.writelines(lines)
            
            # Add new credentials
            for key, value in credentials.items():
                # Check if key already exists
                if not any(line.startswith(f"{key}=") for line in lines):
                    f.write(f"{key}={value}\n")
        
        print(f"✅ Saved {len(credentials)} credentials to .env file")
    
    def save_to_store(self, credentials: Dict[str, str]):
        """
        Save credentials to local store.
        
        Args:
            credentials: Dictionary of key-value pairs
        """
        # Load existing credentials
        if self.credential_store_path.exists():
            with open(self.credential_store_path, 'r') as f:
                stored_credentials = json.load(f)
        else:
            stored_credentials = {}
        
        # Update credentials
        stored_credentials.update(credentials)
        stored_credentials['last_updated'] = datetime.utcnow().isoformat()
        
        # Save
        with open(self.credential_store_path, 'w') as f:
            json.dump(stored_credentials, f, indent=2)
        
        print(f"✅ Saved {len(credentials)} credentials to credential store")
    
    def list_credentials(self) -> Dict[str, str]:
        """
        List all available credentials.
        
        Returns:
            Dictionary of credential status
        """
        status = {}
        
        # Check environment variables
        for key in ['OPENAI_API_KEY', 'PINEcone_API_KEY', 'GITHUB_TOKEN']:
            status[key] = {
                'source': 'environment' if os.getenv(key) else None,
                'exists': os.getenv(key) is not None
            }
        
        # Check .env file
        if self.env_file_path.exists():
            with open(self.env_file_path, 'r') as f:
                for line in f:
                    if '=' in line:
                        key = line.split('=', 1)[0].strip()
                        if key in status:
                            status[key]['source'] = '.env file'
                            status[key]['exists'] = True
        
        # Check credential store
        if self.credential_store_path.exists():
            with open(self.credential_store_path, 'r') as f:
                stored = json.load(f)
                for key in stored:
                    if key != 'last_updated' and key in status:
                        status[key]['source'] = 'credential store'
                        status[key]['exists'] = True
        
        return status


def create_sample_env_file():
    """Create a sample .env file template."""
    workspace_path = Path(__file__).parent.parent
    env_file = workspace_path / '.env.example'
    
    sample_content = """# LJV Visual Engine - Environment Configuration
# Copy this file to .env and fill in your actual values

# OpenAI API (for embedding generation)
# Get from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-api-key-here

# Pinecone (for vector storage)
# Get from: https://app.pinecone.io/
PINEcone_API_KEY=your-pinecone-key
PINEcone_ENVIRONMENT=us-west1-gcp

# GitHub Token (for API access)
# Get from: https://github.com/settings/tokens
GITHUB_TOKEN=ghp_your-token-here

# Optional: Use mock services (set to 'true' to use mocks)
USE_mock_SERVICES=true
"""
    
    with open(env_file, 'w') as f:
        f.write(sample_content)
    
    print(f"✅ Created sample .env file: {env_file}")
    return env_file


def main():
    """Demonstration of credential manager."""
    print("🔐 Credential Manager with Multiple Sources")
    print("=" * 60)
    
    # Initialize manager
    manager = CredentialManager()
    
    # List available credentials
    print("\n📋 Credential Status:")
    status = manager.list_credentials()
    for key, info in status.items():
        source = info['source'] or 'not found'
        exists = '✅' if info['exists'] else '❌'
        print(f"  {exists} {key}: {source}")
    
    # Get credentials with fallback
    print("\n🔑 Getting Credentials:")
    openai_key = manager.get_credential('OPENAI_API_KEY', use_mock=True)
    print(f"  OPENAI_API_KEY: {openai_key[:20]}..." if openai_key else "  OPENAI_API_KEY: None")
    
    pinecone_key = manager.get_credential('PINEcone_API_KEY', use_mock=True)
    print(f"  PINEcone_API_KEY: {pinecone_key[:20]}..." if pinecone_key else "  PINEcone_API_KEY: None")
    
    # Create sample .env file
    print("\n📝 Creating Sample Configuration:")
    create_sample_env_file()
    
    print("\n✅ Credential manager demonstration complete!")
    print("\n💡 Usage:")
    print("  1. Copy .env.example to .env")
    print("  2. Fill in your actual credentials")
    print("  3. Credentials automatically loaded from .env")
    print("  4. Mock credentials used when real ones unavailable")


if __name__ == '__main__':
    import hashlib
    main()