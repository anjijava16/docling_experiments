# Quick Reference: Images + Tables

## 🎯 One Script Does Both

**File:** `pdf_chromadb_images_tables.py`

Automatically handles:
- ✅ Images → OpenAI Vision → Descriptions
- ✅ Tables → OpenAI LLM → Descriptions
- ✅ Both get UUIDs during processing
- ✅ Both cleaned before ChromaDB

## 🚀 Quick Start

```bash
# Install
pip install docling openai langchain langchain-openai langchain-chroma chromadb

# Run
python pdf_chromadb_images_tables.py
```

## 📝 Two Methods

### Method 1: Ingest (handles both images and tables)
```python
from pdf_chromadb_images_tables import ingest_pdf

stats = ingest_pdf("document.pdf")

print(f"Images: {stats['images_found']}")
print(f"Tables: {stats['tables_found']}")
```

### Method 2: Search
```python
from pdf_chromadb_images_tables import search_similar

# Search works on both image and table descriptions
results = search_similar("What do the tables show?", k=3)
```

## 🔄 Processing Flow

```
PDF
 ↓
Extract with Docling
 ↓
┌─────────────┬─────────────┐
│   Images    │   Tables    │
├─────────────┼─────────────┤
│ → Vision AI │ → LLM       │
│ → Get desc  │ → Get desc  │
│ → Add UUID  │ → Add UUID  │
└─────────────┴─────────────┘
 ↓
Add descriptions to markdown
 ↓
Clean (remove UUIDs)
 ↓
Store in ChromaDB
```

## 📊 What Gets Processed

### Images
```markdown
BEFORE: ![chart](data:image/png;base64,...)

WITH UUID:
<!-- IMAGE_UUID: abc-123 -->
![chart](data:image/png;base64,...)
**Image UUID: `abc-123`**
**Description:** Bar chart showing sales
<!-- END_IMAGE -->

AFTER CLEANING:
![chart](data:image/png;base64,...)
Bar chart showing sales
```

### Tables
```markdown
BEFORE:
| Q1 | Q2 |
|----|-----|
| 10 | 15  |

WITH UUID:
<!-- TABLE_UUID: def-456 -->
| Q1 | Q2 |
|----|-----|
| 10 | 15  |
**Table UUID: `def-456`**
**Table Description:** Quarterly data comparison
<!-- END_TABLE -->

AFTER CLEANING:
| Q1 | Q2 |
|----|-----|
| 10 | 15  |
Quarterly data comparison
```

## 🧹 What Gets Removed

| Type | Removed | Kept |
|------|---------|------|
| Images | `<!-- IMAGE_UUID: ... -->` | Description text |
| Images | `**Image UUID: `...`**` | Image data |
| Images | `**Description:**` label | - |
| Tables | `<!-- TABLE_UUID: ... -->` | Description text |
| Tables | `**Table UUID: `...`**` | Table data |
| Tables | `**Table Description:**` label | - |

## 📂 Output Files

When `save_intermediate=True`:

```
1_original.md          → Raw extraction
2_uuid_mapping.json    → All UUIDs + descriptions
3_with_descriptions.md → With UUIDs (before clean)
4_cleaned.md          → Clean (in ChromaDB)
chroma_db/            → Vector database
```

## 🔍 Check What Was Found

```python
import json

# Load UUID mapping
with open("2_uuid_mapping.json") as f:
    items = json.load(f)

# Separate by type
images = [i for i in items if i['type'] == 'image']
tables = [i for i in items if i['type'] == 'table']

print(f"Images found: {len(images)}")
print(f"Tables found: {len(tables)}")

# View descriptions
for table in tables:
    print(f"\nTable: {table['caption']}")
    print(f"Description: {table['description']}")
```

## ⚙️ Configuration

```python
# At top of script
OPENAI_API_KEY = "your-key"
OPENAI_MODEL = "gpt-4o-mini"

# Custom prompts
IMAGE_DESCRIPTION_PROMPT = """Your image prompt..."""
TABLE_DESCRIPTION_PROMPT = """Your table prompt..."""
```

## 💰 Cost Estimates

| Item | Cost per Item | 10 Items |
|------|---------------|----------|
| Images (Vision) | ~$0.001-0.005 | ~$0.01-0.05 |
| Tables (LLM) | ~$0.0005-0.001 | ~$0.005-0.01 |

**Example:** 100-page PDF with 20 images + 15 tables ≈ $0.03-0.08

## 🎨 Custom Prompts

### For Financial Tables
```python
TABLE_DESCRIPTION_PROMPT = """Analyze this financial table:
- Key metrics and their values
- Trends or patterns
- Notable changes
Keep it brief (2-3 sentences)."""
```

### For Scientific Tables
```python
TABLE_DESCRIPTION_PROMPT = """Analyze this data table:
- Variables measured
- Key results
- Significant findings
Keep it brief (2-3 sentences)."""
```

## 🔎 Search Examples

```python
# Search for table content
results = search_similar("What are the revenue figures?", k=3)

# Search for image content
results = search_similar("Show me the chart data", k=3)

# General search (finds both)
results = search_similar("What are the main findings?", k=5)
```

## 🐛 Common Issues

| Problem | Solution |
|---------|----------|
| No tables found | Check if PDF has real tables (not images) |
| Table format messy | LLM description captures meaning |
| Tables not described | Check API key, rate limits |
| Out of memory | Reduce `CHUNK_SIZE` to 500 |

## 🎯 Typical Workflow

```python
# 1. Ingest PDF
stats = ingest_pdf("research_paper.pdf", save_intermediate=True)

# 2. Check what was found
print(f"Found {stats['images_found']} images")
print(f"Found {stats['tables_found']} tables")

# 3. Review intermediate files
# Open 2_uuid_mapping.json to see all descriptions

# 4. Search
results = search_similar("Explain the data tables", k=3)

# 5. Use results
for doc, score in results:
    print(doc.page_content)
```

## ✅ Benefits

✅ **Automatic** - Handles both images and tables  
✅ **AI Descriptions** - Smart descriptions from OpenAI  
✅ **Clean Storage** - No UUIDs clutter in ChromaDB  
✅ **Searchable** - Both images and tables are searchable  
✅ **Traceable** - UUID mapping saved for debugging  

## 📚 Full Documentation

See `IMAGES_TABLES_GUIDE.md` for complete details!

## 🚀 Next Steps

1. Edit script: Add your OpenAI API key
2. Run: `python pdf_chromadb_images_tables.py`
3. Check: `2_uuid_mapping.json` for all items
4. Search: Test queries on your data
5. Integrate: Use in your application

**That's it!** Both images and tables are now handled automatically! 🎉
