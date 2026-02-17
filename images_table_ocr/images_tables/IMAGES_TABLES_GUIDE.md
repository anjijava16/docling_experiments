# Images AND Tables Description Guide

## Overview

This solution handles **both images and tables** by sending them to OpenAI for descriptions:
- **Images** → OpenAI Vision API → Get visual descriptions
- **Tables** → OpenAI LLM → Get data analysis descriptions

Both get UUIDs during processing, then UUIDs are removed before ChromaDB storage.

## How It Works

### For Images

**1. Extraction:**
```markdown
![chart](data:image/png;base64,iVBORw0KGgo...)
```

**2. Add UUID and Description:**
```markdown
<!-- IMAGE_UUID: 550e8400-e29b-41d4-a716-446655440000 -->
![chart](data:image/png;base64,iVBORw0KGgo...)
**Image UUID: `550e8400-e29b-41d4-a716-446655440000`**
**Description:** This is a bar chart showing quarterly revenue trends from 2020-2024, with peak performance in Q3 2023.
<!-- END_IMAGE -->
```

**3. Clean for ChromaDB (UUIDs removed):**
```markdown
![chart](data:image/png;base64,iVBORw0KGgo...)
This is a bar chart showing quarterly revenue trends from 2020-2024, with peak performance in Q3 2023.
```

### For Tables

**1. Extraction (Docling extracts as Markdown):**
```markdown
| Quarter | Revenue | Growth |
|---------|---------|--------|
| Q1 2024 | $2.1M   | 15%    |
| Q2 2024 | $2.4M   | 14%    |
| Q3 2024 | $2.8M   | 17%    |
```

**2. Add UUID and Description:**
```markdown
<!-- TABLE_UUID: 7d3f2e1a-9c8b-4f5d-a3e2-1b6c8d9e0f4a -->
| Quarter | Revenue | Growth |
|---------|---------|--------|
| Q1 2024 | $2.1M   | 15%    |
| Q2 2024 | $2.4M   | 14%    |
| Q3 2024 | $2.8M   | 17%    |
**Table UUID: `7d3f2e1a-9c8b-4f5d-a3e2-1b6c8d9e0f4a`**
**Table Description:** This table shows quarterly revenue performance for 2024. The columns represent quarter, revenue in millions, and percentage growth. Key insight: consistent double-digit growth with Q3 showing the strongest performance at 17% growth.
<!-- END_TABLE -->
```

**3. Clean for ChromaDB (UUIDs removed):**
```markdown
| Quarter | Revenue | Growth |
|---------|---------|--------|
| Q1 2024 | $2.1M   | 15%    |
| Q2 2024 | $2.4M   | 14%    |
| Q3 2024 | $2.8M   | 17%    |
This table shows quarterly revenue performance for 2024. The columns represent quarter, revenue in millions, and percentage growth. Key insight: consistent double-digit growth with Q3 showing the strongest performance at 17% growth.
```

## What Gets Removed Before ChromaDB

### Image Markers (Removed):
- `<!-- IMAGE_UUID: xxx -->`
- `**Image UUID: `xxx`**`
- `**Description:**` (label only)

### Table Markers (Removed):
- `<!-- TABLE_UUID: xxx -->`
- `**Table UUID: `xxx`**`
- `**Table Description:**` (label only)

### What Stays (Kept):
- ✅ Actual image descriptions
- ✅ Actual table descriptions
- ✅ Images (base64 data)
- ✅ Tables (markdown format)
- ✅ All other content

## Configuration

### Image Description Prompt
```python
IMAGE_DESCRIPTION_PROMPT = """Describe this image in detail. Focus on:
- Type of visualization (chart, diagram, photo, etc.)
- Key visual elements
- Main information conveyed
Keep it concise (2-3 sentences)."""
```

### Table Description Prompt
```python
TABLE_DESCRIPTION_PROMPT = """Analyze this table and provide a concise description. Include:
- What the table shows (main topic/subject)
- Key columns and what they represent
- Important data points or trends
- Main insights or takeaways
Keep it concise (2-4 sentences)."""
```

You can customize these prompts for your domain (e.g., scientific data, financial reports, etc.)

## Example Output

### Before Cleaning (with UUIDs):
```markdown
# Document Title

Some text content here.

<!-- IMAGE_UUID: abc-123 -->
![chart](data:image/png;base64,...)
**Image UUID: `abc-123`**
**Description:** Bar chart showing sales growth
<!-- END_IMAGE -->

More content.

<!-- TABLE_UUID: def-456 -->
| Product | Sales |
|---------|-------|
| A       | 100   |
| B       | 150   |
**Table UUID: `def-456`**
**Table Description:** Product sales comparison with B outperforming A
<!-- END_TABLE -->
```

### After Cleaning (stored in ChromaDB):
```markdown
# Document Title

Some text content here.

![chart](data:image/png;base64,...)
Bar chart showing sales growth

More content.

| Product | Sales |
|---------|-------|
| A       | 100   |
| B       | 150   |
Product sales comparison with B outperforming A
```

Clean, readable, searchable! 🎉

## Usage

### Basic Usage
```python
from pdf_chromadb_images_tables import ingest_pdf, search_similar

# 1. Ingest PDF (handles images AND tables automatically)
stats = ingest_pdf("document.pdf")

print(f"Processed:")
print(f"  - {stats['images_found']} images")
print(f"  - {stats['tables_found']} tables")
print(f"  - {stats['chunks_created']} chunks stored")

# 2. Search
results = search_similar("What do the tables show?", k=3)

for doc, score in results:
    print(f"Score: {score:.4f}")
    print(doc.page_content)
```

### Check What Was Found
```python
# Ingest and get statistics
stats = ingest_pdf("document.pdf", save_intermediate=True)

# Check the UUID mapping file
import json
with open("2_uuid_mapping.json") as f:
    items = json.load(f)

# Count images vs tables
images = [item for item in items if item['type'] == 'image']
tables = [item for item in items if item['type'] == 'table']

print(f"Images: {len(images)}")
print(f"Tables: {len(tables)}")

# View table descriptions
for table in tables:
    print(f"\nTable UUID: {table['uuid']}")
    print(f"Caption: {table.get('caption', 'No caption')}")
    print(f"Description: {table['description']}")
```

## Intermediate Files

When `save_intermediate=True`, you get:

**1. `1_original.md`** - Raw Docling extraction
```markdown
Just the tables and images, no descriptions yet
```

**2. `2_uuid_mapping.json`** - All UUIDs with descriptions
```json
[
  {
    "uuid": "abc-123",
    "type": "image",
    "description": "Bar chart showing..."
  },
  {
    "uuid": "def-456",
    "type": "table",
    "description": "Product sales comparison...",
    "caption": "Table 1: Sales Data"
  }
]
```

**3. `3_with_descriptions.md`** - Markdown with UUIDs and descriptions
```markdown
All UUIDs visible, before cleaning
```

**4. `4_cleaned.md`** - Final version (what goes in ChromaDB)
```markdown
Clean markdown, UUIDs removed
```

## Table Extraction Details

### What Docling Extracts

Docling extracts tables as:
1. **Markdown tables** - Text format
2. **Table captions** - If available
3. **Table structure** - Rows and columns

### What Gets Sent to OpenAI

For each table, we send:
```
Table Caption: [caption if available]

Table Data (Markdown format):
| Column1 | Column2 | Column3 |
|---------|---------|---------|
| Data1   | Data2   | Data3   |

Analyze this table and provide a description.
```

### What OpenAI Returns

Example table description:
```
This table presents quarterly financial results for fiscal year 2024. 
The columns show quarter identifier, total revenue in millions, and 
year-over-year growth percentage. Notable trend: revenue increased 
consistently each quarter with Q4 showing the highest growth at 23%.
```

## Advanced: Custom Table Analysis

### Financial Tables
```python
TABLE_DESCRIPTION_PROMPT = """Analyze this financial table:
- Identify key financial metrics
- Note any significant trends or changes
- Highlight critical data points
- Comment on overall financial health
Keep it concise (3-4 sentences)."""
```

### Scientific Tables
```python
TABLE_DESCRIPTION_PROMPT = """Analyze this scientific data table:
- Describe the experimental variables
- Identify key measurements and units
- Note significant results or patterns
- Mention any outliers or anomalies
Keep it concise (3-4 sentences)."""
```

### Statistical Tables
```python
TABLE_DESCRIPTION_PROMPT = """Analyze this statistical table:
- Identify the statistical measures shown
- Note sample sizes if present
- Highlight significant values or p-values
- Interpret the main statistical findings
Keep it concise (3-4 sentences)."""
```

## Cost Estimates

### Images (OpenAI Vision)
- Per image: ~$0.001-0.005 (depends on size)
- 10 images: ~$0.01-0.05

### Tables (OpenAI LLM)
- Per table: ~$0.0005-0.001
- 10 tables: ~$0.005-0.01

### Example Document
- 100-page PDF
- 20 images
- 15 tables
- **Total: ~$0.03-0.08**

## Troubleshooting

### No Tables Extracted
**Problem:** Tables not detected  
**Solution:** 
- Check if PDF has actual tables (not images of tables)
- Ensure `generate_table_images=True` in pipeline options
- Some complex tables may not extract cleanly

### Table Format Issues
**Problem:** Table looks messy in markdown  
**Solution:**
- Tables are exported as markdown by Docling
- Complex tables with merged cells may not format perfectly
- The LLM description helps capture the meaning even if format isn't perfect

### Table Descriptions Not Added
**Problem:** Tables extracted but no descriptions  
**Solution:**
- Check OpenAI API key is valid
- Check rate limits (add delay between requests)
- Check intermediate files to see if extraction worked

## Best Practices

1. **Custom Prompts** - Adjust table description prompts for your domain
2. **Check Intermediate Files** - Use `save_intermediate=True` for debugging
3. **Review Descriptions** - Check `2_uuid_mapping.json` to see all descriptions
4. **Tune Chunk Size** - Adjust if tables are being split across chunks
5. **Test Small First** - Start with 1-2 pages to test extraction quality

## Comparison: Images vs Tables

| Aspect | Images | Tables |
|--------|--------|--------|
| Extraction | Base64 encoded | Markdown format |
| API Used | OpenAI Vision | OpenAI Chat (text) |
| Description Length | 2-3 sentences | 2-4 sentences |
| Cost per item | ~$0.001-0.005 | ~$0.0005-0.001 |
| UUID Format | IMAGE_UUID | TABLE_UUID |
| Label | "Description:" | "Table Description:" |

Both are cleaned the same way before ChromaDB storage!

## Next Steps

1. Run the script on a PDF with tables
2. Check `2_uuid_mapping.json` to see extracted tables
3. Review `3_with_descriptions.md` to see descriptions with UUIDs
4. Check `4_cleaned.md` to verify UUIDs are removed
5. Search ChromaDB to test retrieval

Your tables are now searchable with AI-generated descriptions! 🎉
