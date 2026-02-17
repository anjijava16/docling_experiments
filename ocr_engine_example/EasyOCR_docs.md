# Configuration Guide: Complete EasyOCR Pipeline

## Quick Start

### 1. Basic Configuration (English)

```python
# In complete_pipeline_easyocr.py, edit the Config class:

class Config:
    # Input
    INPUT_PDF = "your_document.pdf"  # ← Your PDF file
    OUTPUT_DIR = Path("scratch")
    
    # EasyOCR
    EASYOCR_LANGUAGES = ["en"]  # ← English only
    EASYOCR_LOCAL_MODEL_PATH = "../model/"  # ← Local models folder
    EASYOCR_DOWNLOAD_ENABLED = True  # ← Set True first time to download
    EASYOCR_USE_GPU = False  # ← Set True if you have GPU
    
    # OpenAI
    OPENAI_API_KEY = "sk-your-key-here"  # ← Your API key
```

### 2. Run the Pipeline

```bash
python complete_pipeline_easyocr.py
```

## Configuration Options

### Language Configurations

#### English Only
```python
EASYOCR_LANGUAGES = ["en"]
```

#### Spanish (like your example)
```python
EASYOCR_LANGUAGES = ["es"]
```

#### Chinese + English
```python
EASYOCR_LANGUAGES = ["en", "ch_sim"]  # Simplified Chinese
# or
EASYOCR_LANGUAGES = ["en", "ch_tra"]  # Traditional Chinese
```

#### Japanese + English
```python
EASYOCR_LANGUAGES = ["en", "ja"]
```

#### Korean + English
```python
EASYOCR_LANGUAGES = ["en", "ko"]
```

#### Multi-Language European
```python
EASYOCR_LANGUAGES = ["en", "fr", "de", "es", "it"]
```

### Local Models Configuration

#### First Time Setup (Download Models)
```python
EASYOCR_LOCAL_MODEL_PATH = "../model/"  # Where to save models
EASYOCR_DOWNLOAD_ENABLED = True  # Download models first time
EASYOCR_USE_GPU = False
```

Run once to download models:
```bash
python complete_pipeline_easyocr.py
```

Models will be saved to `../model/` directory.

#### After Models Are Downloaded (Use Local Only)
```python
EASYOCR_LOCAL_MODEL_PATH = "../model/"  # Where models are saved
EASYOCR_DOWNLOAD_ENABLED = False  # Don't download, use local
EASYOCR_USE_GPU = False
```

This prevents re-downloading models every time!

### GPU Configuration

#### CPU Only (Default)
```python
EASYOCR_USE_GPU = False
```

#### GPU Enabled (Faster)
```python
EASYOCR_USE_GPU = True
```

**Requirements for GPU:**
- NVIDIA GPU with CUDA support
- CUDA Toolkit installed
- cuDNN installed
- PyTorch with CUDA support

**Speed Comparison:**
- CPU: ~18-30 seconds per page
- GPU: ~5-9 seconds per page

### ChromaDB Configuration

```python
# Where to store vector database
CHROMA_DB_DIR = "./chroma_db_easyocr"

# Collection name (can have multiple collections)
COLLECTION_NAME = "documents_easyocr"
```

**Multiple Collections Example:**
```python
# For different document types
COLLECTION_NAME = "medical_documents"  # For medical docs
COLLECTION_NAME = "legal_documents"    # For legal docs
COLLECTION_NAME = "research_papers"    # For research
```

### Text Chunking Configuration

```python
# Size of each chunk in characters
CHUNK_SIZE = 1000  # Default

# Overlap between chunks
CHUNK_OVERLAP = 200  # Default
```

**Guidelines:**
- **Small chunks (500-800):** More precise search, more results
- **Medium chunks (1000-1500):** Balanced (recommended)
- **Large chunks (1500-2000):** More context, fewer results

**Overlap:**
- **Small (100):** Less redundancy, might miss context
- **Medium (200):** Balanced (recommended)
- **Large (300):** More redundancy, preserves context better

### OpenAI Configuration

```python
# Your API key
OPENAI_API_KEY = "sk-your-key-here"

# Model to use
OPENAI_MODEL = "gpt-4o-mini"  # Fast and cheap
# OPENAI_MODEL = "gpt-4o"     # Higher quality

# Delay between requests (rate limiting)
BATCH_DELAY = 1  # 1 second (safe for most users)
```

### Custom Prompts

#### For Scientific Documents
```python
IMAGE_DESCRIPTION_PROMPT = """Analyze this scientific figure:
- Type of visualization (plot, diagram, microscopy, etc.)
- Variables and axes
- Key findings or patterns
- Statistical significance if visible
Keep it concise (2-3 sentences)."""

TABLE_DESCRIPTION_PROMPT = """Analyze this scientific data table:
- Experimental variables
- Measurements and units
- Sample sizes
- Significant results or trends
Keep it concise (2-4 sentences)."""
```

#### For Financial Documents
```python
IMAGE_DESCRIPTION_PROMPT = """Analyze this financial chart:
- Type of chart (line, bar, pie, etc.)
- Financial metrics shown
- Time period
- Key trends or changes
Keep it concise (2-3 sentences)."""

TABLE_DESCRIPTION_PROMPT = """Analyze this financial table:
- Financial metrics or KPIs
- Time periods covered
- Important values or changes
- Notable trends
Keep it concise (2-4 sentences)."""
```

#### For Medical Documents
```python
IMAGE_DESCRIPTION_PROMPT = """Analyze this medical image:
- Type of image (X-ray, MRI, diagram, etc.)
- Anatomical structures visible
- Notable features or findings
- Clinical relevance if evident
Keep it concise (2-3 sentences)."""

TABLE_DESCRIPTION_PROMPT = """Analyze this medical data table:
- Type of medical data (lab results, patient info, etc.)
- Relevant parameters
- Normal vs abnormal ranges if shown
- Clinical significance
Keep it concise (2-4 sentences)."""
```

## Complete Configuration Examples

### Example 1: English Documents with GPU

```python
class Config:
    # Input/Output
    INPUT_PDF = "research_paper.pdf"
    OUTPUT_DIR = Path("scratch")
    
    # EasyOCR - English with GPU
    EASYOCR_LANGUAGES = ["en"]
    EASYOCR_LOCAL_MODEL_PATH = "../model/"
    EASYOCR_DOWNLOAD_ENABLED = False  # Already downloaded
    EASYOCR_USE_GPU = True  # Fast processing
    
    # OpenAI
    OPENAI_API_KEY = "sk-your-key"
    OPENAI_MODEL = "gpt-4o-mini"
    
    # ChromaDB
    CHROMA_DB_DIR = "./chroma_db"
    COLLECTION_NAME = "research_papers"
    
    # Chunking
    CHUNK_SIZE = 1500  # Larger chunks for research
    CHUNK_OVERLAP = 300
```

### Example 2: Chinese + English Documents

```python
class Config:
    # Input/Output
    INPUT_PDF = "business_doc.pdf"
    OUTPUT_DIR = Path("scratch")
    
    # EasyOCR - Chinese + English
    EASYOCR_LANGUAGES = ["en", "ch_sim"]
    EASYOCR_LOCAL_MODEL_PATH = "../model/"
    EASYOCR_DOWNLOAD_ENABLED = False
    EASYOCR_USE_GPU = True  # Recommended for Chinese
    
    # OpenAI
    OPENAI_API_KEY = "sk-your-key"
    OPENAI_MODEL = "gpt-4o"  # Better for multi-language
    
    # ChromaDB
    CHROMA_DB_DIR = "./chroma_db"
    COLLECTION_NAME = "business_documents"
    
    # Chunking
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
```

### Example 3: Medical Documents with High Quality

```python
class Config:
    # Input/Output
    INPUT_PDF = "medical_record.pdf"
    OUTPUT_DIR = Path("scratch")
    
    # EasyOCR - Medical (English)
    EASYOCR_LANGUAGES = ["en"]
    EASYOCR_LOCAL_MODEL_PATH = "../model/"
    EASYOCR_DOWNLOAD_ENABLED = False
    EASYOCR_USE_GPU = True
    
    # OpenAI - High quality for medical
    OPENAI_API_KEY = "sk-your-key"
    OPENAI_MODEL = "gpt-4o"  # Higher quality
    
    # ChromaDB
    CHROMA_DB_DIR = "./chroma_db"
    COLLECTION_NAME = "medical_records"
    
    # Chunking - Smaller for precise search
    CHUNK_SIZE = 800
    CHUNK_OVERLAP = 200
    
    # Custom medical prompts
    IMAGE_DESCRIPTION_PROMPT = """Analyze this medical image..."""
    TABLE_DESCRIPTION_PROMPT = """Analyze this medical data..."""
```

## Pipeline Stages Explained

### Stage 1: PDF Extraction
```
Input: PDF file
Process: Docling + EasyOCR extract text, images, tables
Output: Markdown with embedded base64 images
File: {filename}_1_original.md
```

### Stage 2: UUID Assignment
```
Input: Original markdown
Process: Assign UUID to each image and table
Output: List of images and tables with UUIDs
```

### Stage 3: LLM Descriptions
```
Input: Images and tables with UUIDs
Process: Send to OpenAI for descriptions
Output: Images and tables with descriptions
```

### Stage 4: Add Descriptions with UUIDs
```
Input: Original markdown + descriptions
Process: Add UUID markers and descriptions
Output: Markdown with UUID markers
File: {filename}_3_with_descriptions.md

Example:
<!-- IMAGE_UUID: abc-123 -->
![chart](data:image/png;base64,...)
**Image UUID: `abc-123`**
**Description:** Bar chart showing revenue growth
<!-- END_IMAGE -->
```

### Stage 5: Clean Markdown
```
Input: Markdown with UUID markers
Process: Remove all UUID markers and labels
Output: Clean markdown with just descriptions
File: {filename}_4_cleaned.md

Example:
![chart](data:image/png;base64,...)
Bar chart showing revenue growth
```

### Stage 6: Chunk and Store
```
Input: Clean markdown
Process: Split into chunks, create embeddings
Output: Stored in ChromaDB
Location: {CHROMA_DB_DIR}/
```

## Output Files

After running the pipeline, you'll have:

```
scratch/
├── 2408.09869v5_1_original.md          # Raw extraction
├── 2408.09869v5_2_uuid_mapping.json    # UUID → description mapping
├── 2408.09869v5_3_with_descriptions.md # With UUIDs (intermediate)
└── 2408.09869v5_4_cleaned.md           # Final cleaned (in ChromaDB)

chroma_db_easyocr/
└── (ChromaDB vector database files)
```

## Searching the Database

After ingestion, search the database:

```python
from complete_pipeline_easyocr import search_similar

# Search
results = search_similar("What are the main findings?", k=3)

# Use results
for doc, score in results:
    print(f"Score: {score:.4f}")
    print(doc.page_content)
```

Or directly:

```python
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

embeddings = OpenAIEmbeddings(openai_api_key="YOUR_KEY")
vectorstore = Chroma(
    collection_name="documents_easyocr",
    embedding_function=embeddings,
    persist_directory="./chroma_db_easyocr"
)

results = vectorstore.similarity_search("your query", k=3)
```

## Troubleshooting

### "Models not found"
```python
# Set download enabled for first run
EASYOCR_DOWNLOAD_ENABLED = True
```

### "CUDA not available"
```python
# Use CPU instead
EASYOCR_USE_GPU = False
```

### "Out of memory"
```python
# Reduce chunk size
CHUNK_SIZE = 500
```

### Slow processing
```python
# Use GPU if available
EASYOCR_USE_GPU = True

# Or reduce image scale in pipeline_options
pipeline_options.images_scale = 1.0
```

## Performance Tips

1. **First run:** Set `EASYOCR_DOWNLOAD_ENABLED = True` to download models
2. **Subsequent runs:** Set `EASYOCR_DOWNLOAD_ENABLED = False` to use local models
3. **Use GPU:** 3-5x faster than CPU
4. **Batch processing:** Process multiple PDFs in a loop
5. **Adjust chunk size:** Test different sizes for your use case

## Cost Estimates

```
100-page PDF with 20 images and 10 tables:

OpenAI Costs:
- Image descriptions (20 images × $0.001): $0.02
- Table descriptions (10 tables × $0.0005): $0.005
- Embeddings (100 pages × $0.00001): $0.001
Total: ~$0.026 per document

EasyOCR: Free (self-hosted)
ChromaDB: Free (self-hosted)
```

## Next Steps

1. Edit configuration in `complete_pipeline_easyocr.py`
2. Set your OpenAI API key
3. Configure EasyOCR languages and settings
4. Run the pipeline
5. Search your documents!

That's it! 🚀