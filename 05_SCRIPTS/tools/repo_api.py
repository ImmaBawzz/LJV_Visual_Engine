"""
LJV Visual Engine - Repository Metadata API

A FastAPI application that serves repository metadata and provides
programmatic access to project information for AI agents and developers.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import json
from pathlib import Path
from datetime import datetime

app = FastAPI(
    title="LJV Visual Engine API",
    description="API for accessing LJV Visual Engine repository metadata and project information",
    version="1.0.0",
    contact={
        "name": "ImmaBawzz",
        "url": "https://github.com/ImmaBawzz/LJV_Visual_Engine",
    },
)

# Enable CORS for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "LJV Visual Engine API",
        "version": "1.0.0",
        "description": "Repository metadata and project information API",
        "endpoints": {
            "/repo-info": "GitHub repository information",
            "/project-info": "Local project configuration",
            "/features": "Project features list",
            "/health": "API health check"
        }
    }


@app.get("/repo-info")
async def repo_info():
    """
    Fetch and return GitHub repository information.
    
    Returns real-time data from GitHub API including:
    - Repository statistics (stars, forks, watchers)
    - Description and topics
    - Language and license information
    - Creation and update timestamps
    """
    try:
        repo_url = "https://api.github.com/repos/ImmaBawzz/LJV_Visual_Engine"
        response = requests.get(repo_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "data": data,
                "cached": False,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail="Repository not found")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"GitHub API error: {str(e)}")


@app.get("/project-info")
async def project_info():
    """
    Return local project configuration and metadata.
    
    Reads from local JSON-LD metadata file and project configuration.
    """
    try:
        # Read JSON-LD metadata
        metadata_path = Path(__file__).parent.parent.parent / '.github' / 'metadata.jsonld'
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                return {
                    "success": True,
                    "data": metadata,
                    "source": "local",
                    "timestamp": datetime.utcnow().isoformat()
                }
        else:
            raise HTTPException(status_code=404, detail="Metadata file not found")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading metadata: {str(e)}")


@app.get("/features")
async def features():
    """Return list of project features."""
    features = [
        {
            "name": "Audio-Aligned Timings",
            "description": "Uses OpenAI Whisper for word-level transcription and fuzzy-matching",
            "category": "core"
        },
        {
            "name": "Resumable Pipeline",
            "description": "Checkpoint recovery for resumable pipeline execution",
            "category": "core"
        },
        {
            "name": "Automated QA",
            "description": "Preflight validation and post-render quality gates",
            "category": "quality"
        },
        {
            "name": "Modular Workflow",
            "description": "Independently executable pipeline stages",
            "category": "architecture"
        },
        {
            "name": "Production Reports",
            "description": "Alignment diagnostics, quality scorecards, delivery manifests",
            "category": "output"
        },
        {
            "name": "Multiple Export Formats",
            "description": "YouTube 16x9, vertical 9x16, square 1x1 exports",
            "category": "output"
        },
        {
            "name": "Live Dashboard",
            "description": "FastAPI-based monitoring and control interface",
            "category": "monitoring"
        },
        {
            "name": "Schema Validation",
            "description": "JSON schema validation for all configuration files",
            "category": "quality"
        }
    ]
    
    return {
        "success": True,
        "data": features,
        "count": len(features)
    }


@app.get("/health")
async def health_check():
    """API health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@app.get("/metadata/jsonld")
async def jsonld_metadata():
    """Return JSON-LD structured metadata for AI agents."""
    try:
        metadata_path = Path(__file__).parent.parent.parent / '.github' / 'metadata.jsonld'
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                return {
                    "@context": metadata.get("@context"),
                    "@type": metadata.get("@type"),
                    "name": metadata.get("name"),
                    "description": metadata.get("description"),
                    "programmingLanguage": metadata.get("programmingLanguage"),
                    "featureList": metadata.get("featureList"),
                    "keywords": metadata.get("keywords")
                }
        else:
            raise HTTPException(status_code=404, detail="JSON-LD metadata not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)