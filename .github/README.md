# .github Directory - Repository Optimization

This directory contains metadata, workflows, and configuration files for repository optimization and AI agent discoverability.

## Contents

### Metadata Files
- **`metadata.jsonld`** - JSON-LD structured metadata (Schema.org SoftwareSourceCode)
- **`seo_metadata.html`** - Open Graph and Twitter Card metadata
- **`QUICK_REFERENCE.md`** - Quick reference for repository optimization

### GitHub Actions Workflows
- **`auto-label-issues.yml`** - Automatically labels new issues based on content
- **`reindex-embeddings.yml`** - Daily re-indexing of README/docs for vector search
- **`repo-maintenance.yml`** - Weekly repository maintenance and statistics

### Purpose

This directory supports the "Repository Beacon-Worm" initiative to make the LJV Visual Engine repository:

1. **Discoverable** by human developers through SEO optimization
2. **Parseable** by AI agents through structured metadata
3. **Maintained** through automated workflows
4. **Shareable** through social media metadata

## Configuration

### Required Secrets
Add these to GitHub → Settings → Secrets → Actions:

```bash
OPENAI_API_KEY=sk-...
PINEcone_API_KEY=...
PINEcone_ENVIRONMENT=us-west1-gcp
```

### Topics
Add these topics to the repository:
```
music-visualization, lyric-video, audio-reactive, ffmpeg, python, 
video-pipeline, music-production, whisper-asr, checkpoint-recovery
```

## Workflows

### Auto-Labeling (On Issue Creation)
Automatically applies labels:
- `good first issue` - Beginner-friendly contributions
- `documentation` - Docs-related issues
- `examples` - Template and sample code issues

### Embedding Re-Index (Daily 12:00 AM UTC)
- Extracts text from README and documentation
- Generates OpenAI embeddings
- Stores in Pinecone vector database

### Repository Maintenance (Weekly Monday 9:00 AM UTC)
- Collects repository statistics
- Marks stale issues/PRs
- Generates weekly report

## Documentation

For detailed information:
- **Implementation Guide**: `09_DOCS/REPOSITORY_OPTIMIZATION_GUIDE.md`
- **Setup Checklist**: `09_DOCS/BEACON_WORM_CHECKLIST.md`
- **Quick Reference**: `QUICK_REFERENCE.md`

## API Access

Repository metadata can be accessed programmatically:

```bash
# Run API server
python 05_SCRIPTS/tools/repo_api.py

# Access endpoints
curl http://localhost:8000/repo-info
curl http://localhost:8000/features
curl http://localhost:8000/metadata/jsonld
```

## Questions?

See `CONTRIBUTING.md` for contribution guidelines or open an issue for questions.