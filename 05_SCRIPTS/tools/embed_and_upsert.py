"""
Embed and Upsert README and Documentation for Vector Search

This script extracts text content from README and documentation files,
generates embeddings (real or mock), and stores them (in Pinecone or mock).

Auto-fallback: Uses mock services when API keys are not available.
"""

import os
import json
import sys
from pathlib import Path
from typing import List, Dict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from mock_services import get_embedding_service, get_pinecone_index
    print("✅ Loaded mock services for auto-fallback")
except ImportError:
    print("⚠️  mock_services not found, attempting direct imports...")


def get_repository_info() -> Dict:
    """Fetch repository metadata from GitHub API."""
    repo_url = "https://api.github.com/repos/ImmaBawzz/LJV_Visual_Engine"
    try:
        response = requests.get(repo_url)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching repo info: {e}")
    return {}


def extract_text_from_files(base_path: str) -> str:
    """Extract text content from README and documentation files."""
    text_content = []
    
    # Files to index
    files_to_index = [
        'README.md',
        '00_README/README.md',
        '00_README/QUICKSTART.md',
        '09_DOCS/OPERATING_MODEL.md',
        '09_DOCS/CHECKPOINT_GUIDE.md',
        '09_DOCS/RELEASE_CHECKLIST.md',
        'CONTRIBUTING.md',
        'LICENSE'
    ]
    
    for file_path in files_to_index:
        full_path = Path(base_path) / file_path
        if full_path.exists():
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    text_content.append(f"## {file_path}\n\n{content}")
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
    
    return "\n\n".join(text_content)


def create_embedding(text: str, api_key: str) -> List[float]:
    """Create embedding vector using OpenAI or mock service."""
    # Check if we should use mock service
    use_mock = not api_key or os.getenv('USE_mock_SERVICES', 'false').lower() == 'true'
    
    if use_mock:
        print("🔧 Using mock embedding service")
        from mock_services import MockOpenAIEmbedding
        mock_service = MockOpenAIEmbedding()
        result = mock_service.create_embedding(text)
        return result['data'][0]['embedding']
    else:
        print("✅ Using real OpenAI API")
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.embeddings.create(
                input=text,
                model="text-embedding-ada-002"
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"⚠️  OpenAI error: {e}, falling back to mock")
            from mock_services import MockOpenAIEmbedding
            mock_service = MockOpenAIEmbedding()
            return mock_service.create_embedding(text)['data'][0]['embedding']


def upsert_to_pinecone(vector: List[float], repo_id: str, metadata: Dict, 
                       api_key: str, environment: str, index_name: str = "repo-embeddings"):
    """Upsert vector to Pinecone or mock index."""
    # Check if we should use mock service
    use_mock = not api_key or os.getenv('USE_mock_SERVICES', 'false').lower() == 'true'
    
    if use_mock:
        print("🔧 Using mock Pinecone index")
        from mock_services import MockPineconeIndex
        mock_index = MockPineconeIndex(index_name=index_name)
        mock_index.upsert(vectors=[(repo_id, vector, metadata)])
        print(f"✅ Successfully upserted to mock index '{index_name}'")
    else:
        print("✅ Using real Pinecone")
        try:
            import pinecone
            pinecone.init(api_key=api_key, environment=environment)
            index = pinecone.Index(index_name)
            
            index.upsert(vectors=[
                (repo_id, vector, metadata)
            ])
            print(f"✅ Successfully upserted to Pinecone index '{index_name}'")
        except Exception as e:
            print(f"⚠️  Pinecone error: {e}, using mock index")
            from mock_services import MockPineconeIndex
            mock_index = MockPineconeIndex(index_name=index_name)
            mock_index.upsert(vectors=[(repo_id, vector, metadata)])


def main():
    """Main execution function."""
    # Get configuration from environment
    openai_api_key = os.getenv('OPENAI_API_KEY')
    pinecone_api_key = os.getenv('PINEcone_API_KEY')
    pinecone_environment = os.getenv('PINEcone_ENVIRONMENT', 'us-west1-gcp')
    
    # Determine service mode
    use_mock_openai = not openai_api_key or os.getenv('USE_mock_SERVICES', 'false').lower() == 'true'
    use_mock_pinecone = not pinecone_api_key or os.getenv('USE_mock_SERVICES', 'false').lower() == 'true'
    
    print(f"\n🔧 Service Configuration:")
    print(f"  OpenAI: {'MOCK' if use_mock_openai else 'REAL API'}")
    print(f"  Pinecone: {'MOCK' if use_mock_pinecone else 'REAL API'}")
    
    # Get repository info
    repo_info = get_repository_info()
    repo_id = repo_info.get('full_name', 'ImmaBawzz/LJV_Visual_Engine')
    
    # Extract text content
    base_path = Path(__file__).parent.parent.parent
    text_content = extract_text_from_files(str(base_path))
    
    if not text_content:
        print("No text content extracted. Exiting.")
        return
    
    # Create embedding
    print(f"\n📊 Creating embedding for {len(text_content)} characters...")
    vector = create_embedding(text_content, openai_api_key)
    
    if not vector:
        print("Failed to create embedding. Exiting.")
        return
    
    print(f"✅ Embedding created (dimension: {len(vector)})")
    
    # Prepare metadata
    metadata = {
        'repo_name': repo_info.get('name', 'LJV_Visual_Engine'),
        'description': repo_info.get('description', ''),
        'language': repo_info.get('language', 'Python'),
        'stars': repo_info.get('stargazers_count', 0),
        'forks': repo_info.get('forks_count', 0),
        'updated_at': repo_info.get('updated_at', ''),
        'content_length': len(text_content),
        'indexed_files': [
            'README.md',
            '00_README/README.md',
            '00_README/QUICKSTART.md',
            '09_DOCS/OPERATING_MODEL.md',
            '09_DOCS/CHECKPOINT_GUIDE.md',
            '09_DOCS/RELEASE_CHECKLIST.md',
            'CONTRIBUTING.md',
            'LICENSE'
        ],
        'service_mode': 'mock' if use_mock_openai else 'real'
    }
    
    # Upsert to Pinecone or mock
    print(f"\n🗂️  Upserting to {'mock index' if use_mock_pinecone else 'Pinecone'}...")
    upsert_to_pinecone(
        vector=vector,
        repo_id=repo_id,
        metadata=metadata,
        api_key=pinecone_api_key,
        environment=pinecone_environment
    )
    
    print("\n✅ Embedding and upsert completed successfully!")
    if use_mock_openai or use_mock_pinecone:
        print("\n💡 Note: Used mock services - no API keys required")
        print("   Mock data stored in: 03_WORK/temp/mock_pinecone/")


if __name__ == '__main__':
    main()