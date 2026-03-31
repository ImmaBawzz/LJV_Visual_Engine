"""
Mock Services for API Key Alternatives

This module provides mock/alternative implementations for services that
typically require API keys, allowing the repository to function without
external credentials.
"""

import os
import json
import hashlib
import random
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class MockOpenAIEmbedding:
    """
    Mock OpenAI embedding service for testing and development.
    
    Generates deterministic pseudo-embeddings based on input text.
    Useful when OPENAI_API_KEY is not available.
    """
    
    def __init__(self, dimension: int = 1536):
        """
        Initialize mock embedding service.
        
        Args:
            dimension: Embedding vector dimension (default: 1536 for ADA-002)
        """
        self.dimension = dimension
        self.model = "mock-text-embedding-ada-002"
        
    def create_embedding(self, text: str) -> Dict:
        """
        Create a mock embedding vector.
        
        Args:
            text: Input text to embed
            
        Returns:
            Mock embedding response
        """
        # Generate deterministic pseudo-random vector based on text hash
        text_hash = hashlib.sha256(text.encode()).digest()
        
        # Use hash to seed random generation
        import random
        seed = int.from_bytes(text_hash[:4], 'big')
        random.seed(seed)
        
        # Generate vector with realistic properties
        vector = [random.gauss(0, 0.1) for _ in range(self.dimension)]
        
        # Normalize vector (unit length)
        norm = sum(v*v for v in vector) ** 0.5
        vector = [v/norm for v in vector]
        
        return {
            'object': 'list',
            'data': [{
                'object': 'embedding',
                'index': 0,
                'embedding': vector,
                'model': self.model
            }],
            'model': self.model,
            'usage': {
                'prompt_tokens': len(text.split()),
                'total_tokens': len(text.split())
            }
        }
    
    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """
        Embed multiple documents.
        
        Args:
            documents: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        for doc in documents:
            result = self.create_embedding(doc)
            embeddings.append(result['data'][0]['embedding'])
        return embeddings


class MockPineconeIndex:
    """
    Mock Pinecone index for local development.
    
    Stores vectors in memory/disk instead of cloud.
    """
    
    def __init__(self, index_name: str = "mock-repo-embeddings", 
                 dimension: int = 1536):
        """
        Initialize mock Pinecone index.
        
        Args:
            index_name: Name of the index
            dimension: Vector dimension
        """
        self.index_name = index_name
        self.dimension = dimension
        self.vectors = {}
        self.storage_path = Path(__file__).parent.parent / '03_WORK' / 'temp' / 'mock_pinecone'
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Load existing vectors
        self._load_vectors()
        
    def _load_vectors(self):
        """Load vectors from disk storage."""
        storage_file = self.storage_path / f"{self.index_name}.json"
        if storage_file.exists():
            with open(storage_file, 'r') as f:
                self.vectors = json.load(f)
    
    def _save_vectors(self):
        """Save vectors to disk storage."""
        storage_file = self.storage_path / f"{self.index_name}.json"
        with open(storage_file, 'w') as f:
            json.dump(self.vectors, f, indent=2)
    
    def upsert(self, vectors: List[tuple]):
        """
        Upsert vectors to index.
        
        Args:
            vectors: List of (id, vector, metadata) tuples
        """
        for vector_data in vectors:
            if len(vector_data) == 2:
                vector_id, vector = vector_data
                metadata = {}
            else:
                vector_id, vector, metadata = vector_data
            
            self.vectors[vector_id] = {
                'vector': vector,
                'metadata': metadata,
                'timestamp': datetime.utcnow().isoformat()
            }
        
        self._save_vectors()
        print(f"✅ Upserted {len(vectors)} vectors to mock index '{self.index_name}'")
    
    def query(self, vector: List[float], top_k: int = 10, 
              filter: Optional[Dict] = None) -> Dict:
        """
        Query the index for similar vectors.
        
        Args:
            vector: Query vector
            top_k: Number of results to return
            filter: Metadata filter
            
        Returns:
            Query results
        """
        # Simple cosine similarity search
        def cosine_similarity(v1, v2):
            dot_product = sum(a*b for a, b in zip(v1, v2))
            norm1 = sum(a*a for a in v1) ** 0.5
            norm2 = sum(b*b for b in v2) ** 0.5
            return dot_product / (norm1 * norm2) if norm1 and norm2 else 0
        
        # Calculate similarities
        similarities = []
        for vector_id, data in self.vectors.items():
            if filter and not self._matches_filter(data['metadata'], filter):
                continue
            
            similarity = cosine_similarity(vector, data['vector'])
            similarities.append({
                'id': vector_id,
                'score': similarity,
                'metadata': data['metadata']
            })
        
        # Sort by similarity
        similarities.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            'matches': similarities[:top_k],
            'namespace': ''
        }
    
    def _matches_filter(self, metadata: Dict, filter: Dict) -> bool:
        """Check if metadata matches filter."""
        for key, value in filter.items():
            if metadata.get(key) != value:
                return False
        return True
    
    def delete(self, ids: List[str]):
        """Delete vectors by ID."""
        for id in ids:
            if id in self.vectors:
                del self.vectors[id]
        self._save_vectors()
    
    def stats(self) -> Dict:
        """Get index statistics."""
        return {
            'total_vectors': len(self.vectors),
            'index_name': self.index_name,
            'dimension': self.dimension,
            'storage_path': str(self.storage_path)
        }


class MockGitHubAPI:
    """
    Mock GitHub API for testing without credentials.
    
    Returns cached/static repository data.
    """
    
    def __init__(self, owner: str = "ImmaBawzz", repo: str = "LJV_Visual_Engine"):
        """
        Initialize mock GitHub API.
        
        Args:
            owner: Repository owner
            repo: Repository name
        """
        self.owner = owner
        self.repo = repo
        self.base_url = f"https://api.github.com/repos/{owner}/{repo}"
        
    def get_repo_info(self) -> Dict:
        """
        Get mock repository information.
        
        Returns:
            Repository data dictionary
        """
        return {
            'id': 123456789,
            'name': self.repo,
            'full_name': f"{self.owner}/{self.repo}",
            'owner': {
                'login': self.owner,
                'id': 987654321,
                'type': 'User'
            },
            'description': 'Professional-grade audio-reactive lyric visualization pipeline',
            'homepage': None,
            'language': 'Python',
            'forks_count': 5,
            'stargazers_count': 42,
            'watchers_count': 42,
            'size': 15000,
            'open_issues_count': 3,
            'license': {
                'key': 'mit',
                'name': 'MIT License',
                'spdx_id': 'MIT'
            },
            'topics': [
                'music-visualization',
                'lyric-video',
                'audio-reactive',
                'ffmpeg',
                'python'
            ],
            'created_at': '2026-01-01T00:00:00Z',
            'updated_at': '2026-04-01T00:00:00Z',
            'pushed_at': '2026-04-01T00:00:00Z'
        }
    
    def get_issues(self, state: str = 'open') -> List[Dict]:
        """
        Get mock issues.
        
        Args:
            state: Issue state ('open', 'closed', 'all')
            
        Returns:
            List of issue dictionaries
        """
        return [
            {
                'number': 1,
                'title': 'Add support for MOV export format',
                'state': state,
                'labels': [{'name': 'enhancement'}],
                'created_at': '2026-03-15T00:00:00Z'
            },
            {
                'number': 2,
                'title': 'Documentation: Add troubleshooting guide',
                'state': state,
                'labels': [{'name': 'documentation'}],
                'created_at': '2026-03-20T00:00:00Z'
            }
        ]


def get_embedding_service(use_mock: bool = True) -> MockOpenAIEmbedding:
    """
    Get embedding service (mock or real).
    
    Args:
        use_mock: If True, use mock service even if API key exists
        
    Returns:
        Embedding service instance
    """
    if use_mock or not os.getenv('OPENAI_API_KEY'):
        print("🔧 Using mock OpenAI embedding service")
        return MockOpenAIEmbedding()
    else:
        print("✅ Using real OpenAI API")
        try:
            from openai import OpenAI
            return OpenAI()
        except ImportError:
            print("⚠️  OpenAI package not installed, using mock")
            return MockOpenAIEmbedding()


def get_pinecone_index(use_mock: bool = True) -> MockPineconeIndex:
    """
    Get Pinecone index (mock or real).
    
    Args:
        use_mock: If True, use mock index even if API key exists
        
    Returns:
        Pinecone index instance
    """
    if use_mock or not os.getenv('PINEcone_API_KEY'):
        print("🔧 Using mock Pinecone index")
        return MockPineconeIndex()
    else:
        print("✅ Using real Pinecone")
        try:
            import pinecone
            pinecone.init(api_key=os.getenv('PINEcone_API_KEY'), 
                          environment=os.getenv('PINEcone_ENVIRONMENT'))
            return pinecone.Index('repo-embeddings')
        except Exception as e:
            print(f"⚠️  Pinecone error: {e}, using mock")
            return MockPineconeIndex()


def main():
    """Demonstration of mock services."""
    print("🔧 Mock Services for API Key Alternatives")
    print("=" * 60)
    
    # Mock OpenAI embeddings
    print("\n📊 Mock OpenAI Embedding:")
    mock_openai = MockOpenAIEmbedding()
    result = mock_openai.create_embedding("Test text for embedding")
    print(f"  Model: {result['model']}")
    print(f"  Vector dimension: {len(result['data'][0]['embedding'])}")
    print(f"  Tokens used: {result['usage']['total_tokens']}")
    
    # Mock Pinecone
    print("\n🗂️  Mock Pinecone Index:")
    mock_pinecone = MockPineconeIndex()
    
    # Upsert mock vectors
    vectors = [
        ("doc1", [0.1] * 1536, {'title': 'Document 1'}),
        ("doc2", [0.2] * 1536, {'title': 'Document 2'})
    ]
    mock_pinecone.upsert(vectors)
    
    print(f"  Index stats: {mock_pinecone.stats()}")
    
    # Mock GitHub API
    print("\n🐙 Mock GitHub API:")
    mock_github = MockGitHubAPI()
    repo_info = mock_github.get_repo_info()
    print(f"  Repository: {repo_info['full_name']}")
    print(f"  Stars: {repo_info['stargazers_count']}")
    print(f"  Forks: {repo_info['forks_count']}")
    print(f"  Language: {repo_info['language']}")
    
    print("\n✅ Mock services demonstration complete!")
    print("\n💡 Usage in workflows:")
    print("  - Replace OpenAI API calls with MockOpenAIEmbedding")
    print("  - Replace Pinecone calls with MockPineconeIndex")
    print("  - Use for testing without API keys")


if __name__ == '__main__':
    main()