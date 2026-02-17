"""
Complete Pipeline: Docling + EasyOCR → LLM Descriptions → ChromaDB
===================================================================

Features:
- Uses EasyOCR with local models (no downloads)
- Extracts images and tables
- Adds UUIDs during processing
- Gets LLM descriptions for images and tables
- Cleans markdown (removes UUIDs)
- Stores in ChromaDB

Based on your example code with EasyOCR configuration.
"""

import json
import logging
import time
import re
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Docling imports
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableStructureOptions,
    EasyOcrOptions
)
from docling_core.types.doc import ImageRefMode, TableItem

# OpenAI

# LangChain and ChromaDB
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from openai import OpenAI
from langchain_text_splitters import MarkdownTextSplitter
#from langchain.schema import Document
from langchain_core.documents import Document

# Logging
logging.basicConfig(level=logging.INFO)
_log = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Configuration settings"""
    
    # Input/Output
    INPUT_PDF = "2408.09869v5.pdf"
    OUTPUT_DIR = Path("scratch")
    
    # EasyOCR Settings (like your example)
    EASYOCR_LANGUAGES = ["en"]  # Change to ["es"] for Spanish, or ["en", "ch_sim"] for multi-language
    EASYOCR_LOCAL_MODEL_PATH = "../model/"  # Path to local EasyOCR models
    EASYOCR_DOWNLOAD_ENABLED = False  # Set True if you want to download models
    EASYOCR_USE_GPU = False  # Set True if you have GPU
    
    # OpenAI Settings
    OPENAI_MODEL = "gpt-4o-mini"
    
    # ChromaDB Settings
    CHROMA_DB_DIR = "./chroma_db_easyocr"
    COLLECTION_NAME = "documents_easyocr"
    
    # Text Splitting
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    
    # Processing
    BATCH_DELAY = 1  # Seconds between OpenAI requests
    
    # Prompts
    IMAGE_DESCRIPTION_PROMPT = """Describe this image in detail. Focus on:
- Type of visualization (chart, diagram, photo, etc.)
- Key visual elements
- Main information conveyed
Keep it concise (2-3 sentences)."""
    
    TABLE_DESCRIPTION_PROMPT = """Analyze this table and provide a concise description. Include:
- What the table shows (main topic/subject)
- Key columns and what they represent
- Important data points or trends
- Main insights or takeaways
Keep it concise (2-4 sentences)."""

# ============================================================================
# STEP 1: EXTRACT PDF WITH EASYOCR (Your Configuration)
# ============================================================================

def extract_pdf_with_easyocr(pdf_path: str) -> Tuple:
    """
    Extract PDF using Docling with EasyOCR
    Uses your exact configuration pattern
    """
    _log.info("="*80)
    _log.info("STEP 1: EXTRACTING PDF WITH DOCLING + EASYOCR")
    _log.info("="*80)
    _log.info(f"PDF: {pdf_path}")
    _log.info(f"Languages: {Config.EASYOCR_LANGUAGES}")
    _log.info(f"GPU: {Config.EASYOCR_USE_GPU}")
    _log.info(f"Local models: {Config.EASYOCR_LOCAL_MODEL_PATH}")
    
    # Configure pipeline options (like your example)
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options = TableStructureOptions(
        do_cell_matching=True
    )
    
    # Configure EasyOCR with local models (like your example)
    pipeline_options.ocr_options = EasyOcrOptions(
        lang=Config.EASYOCR_LANGUAGES,
        model_storage_directory=Config.EASYOCR_LOCAL_MODEL_PATH,
        download_enabled=Config.EASYOCR_DOWNLOAD_ENABLED,
        use_gpu=Config.EASYOCR_USE_GPU
    )
    
    # Enable image extraction
    pipeline_options.generate_picture_images = True
    pipeline_options.images_scale = 2.0
    
    # Create converter
    doc_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    
    # Convert
    _log.info("Converting PDF with EasyOCR...")
    start_time = time.time()
    conv_result = doc_converter.convert(pdf_path)
    end_time = time.time() - start_time
    
    _log.info(f"✓ Document converted in {end_time:.2f} seconds")
    
    # Export to markdown with embedded images
    markdown = conv_result.document.export_to_markdown(image_mode=ImageRefMode.EMBEDDED)
    
    image_count = markdown.count("data:image")
    _log.info(f"✓ Extracted {len(markdown):,} characters")
    _log.info(f"✓ Found {image_count} images")
    
    return conv_result, markdown

# ============================================================================
# STEP 2: EXTRACT IMAGES AND TABLES WITH UUIDS
# ============================================================================

def extract_images_with_uuids(markdown: str) -> List[Dict]:
    """Extract base64 images and assign UUIDs"""
    _log.info("="*80)
    _log.info("STEP 2A: EXTRACTING IMAGES AND ASSIGNING UUIDS")
    _log.info("="*80)
    
    pattern = r'!\[([^\]]*)\]\(data:image/([^;]+);base64,([^)]+)\)'
    images = []
    
    for match in re.finditer(pattern, markdown):
        image_uuid = str(uuid.uuid4())
        images.append({
            'uuid': image_uuid,
            'type': 'image',
            'format': match.group(2),
            'base64': match.group(3),
            'alt_text': match.group(1),
            'original': match.group(0),
            'description': None
        })
    
    _log.info(f"✓ Found {len(images)} images")
    return images


def extract_tables_with_uuids(result) -> List[Dict]:
    """Extract tables from Docling result with UUIDs"""
    _log.info("="*80)
    _log.info("STEP 2B: EXTRACTING TABLES AND ASSIGNING UUIDS")
    _log.info("="*80)
    
    tables = []
    
    for element, _level in result.document.iterate_items():
        if isinstance(element, TableItem):
            table_uuid = str(uuid.uuid4())
            
            # Export table to markdown
            table_markdown = element.export_to_markdown(result.document)
            table_text = element.text if hasattr(element, 'text') else table_markdown
            
            # Handle captions (plural)
            caption = ''
            if hasattr(element, 'captions') and element.captions:
                if isinstance(element.captions, list) and len(element.captions) > 0:
                    caption = element.captions[0].text if hasattr(element.captions[0], 'text') else str(element.captions[0])
                else:
                    caption = str(element.captions)
            
            tables.append({
                'uuid': table_uuid,
                'type': 'table',
                'markdown': table_markdown,
                'text': table_text,
                'caption': caption,
                'original': table_markdown,
                'description': None
            })
    
    _log.info(f"✓ Found {len(tables)} tables")
    
    # Show preview
    for i, table in enumerate(tables[:3], 1):
        _log.info(f"  Table {i}: UUID={table['uuid'][:8]}..., Size={len(table['markdown'])} chars")
    
    return tables

# ============================================================================
# STEP 3: GET LLM DESCRIPTIONS
# ============================================================================

def get_image_descriptions(images: List[Dict]) -> List[Dict]:
    """Get descriptions for images using OpenAI Vision"""
    _log.info("="*80)
    _log.info("STEP 3A: GETTING IMAGE DESCRIPTIONS FROM OPENAI VISION")
    _log.info("="*80)
    
    if not images:
        _log.info("No images to process")
        return images
    
    client = OpenAI()
    
    for i, img in enumerate(images, 1):
        _log.info(f"[{i}/{len(images)}] Processing image {img['uuid'][:8]}...")
        
        try:
            response = client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": Config.IMAGE_DESCRIPTION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{img['format']};base64,{img['base64']}"
                            }
                        }
                    ]
                }],
                max_tokens=300
            )
            
            img['description'] = response.choices[0].message.content
            _log.info(f"  ✓ {img['description'][:80]}...")
            
        except Exception as e:
            img['description'] = f"Error: {str(e)}"
            _log.error(f"  ✗ Error: {str(e)}")
        
        if i < len(images):
            time.sleep(Config.BATCH_DELAY)
    
    _log.info(f"✓ Completed {len(images)} image descriptions")
    return images


def get_table_descriptions(tables: List[Dict]) -> List[Dict]:
    """Get descriptions for tables using OpenAI LLM"""
    _log.info("="*80)
    _log.info("STEP 3B: GETTING TABLE DESCRIPTIONS FROM OPENAI")
    _log.info("="*80)
    
    if not tables:
        _log.info("No tables to process")
        return tables
    
    client = OpenAI()
    
    for i, table in enumerate(tables, 1):
        _log.info(f"[{i}/{len(tables)}] Processing table {table['uuid'][:8]}...")
        
        table_content = f"""
Table Caption: {table['caption'] if table['caption'] else 'No caption'}

Table Data (Markdown format):
{table['markdown']}

Analyze this table and provide a description.
"""
        
        try:
            response = client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a data analyst expert at describing tables."},
                    {"role": "user", "content": Config.TABLE_DESCRIPTION_PROMPT + "\n\n" + table_content}
                ],
                max_tokens=400
            )
            
            table['description'] = response.choices[0].message.content
            _log.info(f"  ✓ {table['description'][:80]}...")
            
        except Exception as e:
            table['description'] = f"Error: {str(e)}"
            _log.error(f"  ✗ Error: {str(e)}")
        
        if i < len(tables):
            time.sleep(Config.BATCH_DELAY)
    
    _log.info(f"✓ Completed {len(tables)} table descriptions")
    return tables

# ============================================================================
# STEP 4: ADD DESCRIPTIONS TO MARKDOWN (WITH UUIDS)
# ============================================================================

def add_descriptions_to_markdown(markdown: str, images: List[Dict], tables: List[Dict]) -> str:
    """Add image and table descriptions to markdown with UUID markers"""
    _log.info("="*80)
    _log.info("STEP 4: ADDING DESCRIPTIONS TO MARKDOWN (WITH UUIDS)")
    _log.info("="*80)
    
    updated_markdown = markdown
    
    # Add image descriptions with UUID markers
    for img in images:
        if img['description']:
            new_markdown = f"""
<!-- IMAGE_UUID: {img['uuid']} -->
{img['original']}
**Image UUID: `{img['uuid']}`**
**Description:** {img['description']}
<!-- END_IMAGE -->
"""
            updated_markdown = updated_markdown.replace(img['original'], new_markdown, 1)
    
    _log.info(f"✓ Added {len(images)} image descriptions")
    
    # Add table descriptions with UUID markers
    for table in tables:
        if table['description']:
            new_markdown = f"""
<!-- TABLE_UUID: {table['uuid']} -->
{table['original']}
**Table UUID: `{table['uuid']}`**
**Table Description:** {table['description']}
<!-- END_TABLE -->
"""
            updated_markdown = updated_markdown.replace(table['original'], new_markdown, 1)
    
    _log.info(f"✓ Added {len(tables)} table descriptions")
    
    return updated_markdown

# ============================================================================
# STEP 5: CLEAN MARKDOWN (REMOVE UUIDS)
# ============================================================================

def clean_markdown(markdown: str) -> str:
    """Remove UUID markers and 'Description:' labels for clean storage"""
    _log.info("="*80)
    _log.info("STEP 5: CLEANING MARKDOWN (REMOVING UUIDS)")
    _log.info("="*80)
    
    original_length = len(markdown)
    
    # Remove IMAGE UUID markers
    cleaned = re.sub(r'<!-- IMAGE_UUID: [a-f0-9\-]+ -->\n?', '', markdown)
    cleaned = re.sub(r'<!-- END_IMAGE -->\n?', '', cleaned)
    cleaned = re.sub(r'\*\*Image UUID: `[a-f0-9\-]+`\*\*\s*\n?', '', cleaned)
    cleaned = re.sub(r'\*\*Description:\*\*\s*', '', cleaned)
    
    # Remove TABLE UUID markers
    cleaned = re.sub(r'<!-- TABLE_UUID: [a-f0-9\-]+ -->\n?', '', cleaned)
    cleaned = re.sub(r'<!-- END_TABLE -->\n?', '', cleaned)
    cleaned = re.sub(r'\*\*Table UUID: `[a-f0-9\-]+`\*\*\s*\n?', '', cleaned)
    cleaned = re.sub(r'\*\*Table Description:\*\*\s*', '', cleaned)
    
    # Clean up whitespace
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = re.sub(r' +\n', '\n', cleaned)
    cleaned = cleaned.strip()
    
    _log.info(f"✓ Cleaned markdown")
    _log.info(f"  Original: {original_length:,} characters")
    _log.info(f"  Cleaned: {len(cleaned):,} characters")
    _log.info(f"  Removed: {original_length - len(cleaned):,} characters")
    
    return cleaned

# ============================================================================
# STEP 6: STORE IN CHROMADB
# ============================================================================

def store_in_chromadb(chunks: List[str], metadata: Optional[Dict] = None) -> Chroma:
    """Store text chunks in ChromaDB"""
    _log.info("="*80)
    _log.info("STEP 6: STORING IN CHROMADB")
    _log.info("="*80)
    
    embeddings = OpenAIEmbeddings()
    
    documents = []
    for i, chunk in enumerate(chunks):
        doc_metadata = {"chunk_id": i, "ocr_engine": "easyocr"}
        if metadata:
            doc_metadata.update(metadata)
        documents.append(Document(page_content=chunk, metadata=doc_metadata))
    
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=Config.COLLECTION_NAME,
        persist_directory=Config.CHROMA_DB_DIR
    )
    
    _log.info(f"✓ Stored {len(documents)} documents in ChromaDB")
    _log.info(f"✓ Location: {Config.CHROMA_DB_DIR}")
    
    return vectorstore

# ============================================================================
# STEP 7: RETRIEVAL (SEARCH)
# ============================================================================

def search_similar(query: str, k: int = 3) -> List[Tuple]:
    """Search ChromaDB for similar content"""
    _log.info("="*80)
    _log.info(f"SEARCHING: '{query}'")
    _log.info("="*80)
    
    try:
        embeddings = OpenAIEmbeddings()
        vectorstore = Chroma(
            collection_name=Config.COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=Config.CHROMA_DB_DIR
        )
        
        results = vectorstore.similarity_search_with_score(query, k=k)
        
        _log.info(f"Found {len(results)} results:")
        for i, (doc, score) in enumerate(results, 1):
            _log.info(f"\n[{i}] Score: {score:.4f}")
            _log.info(f"Content preview: {doc.page_content[:200]}...")
        
        return results
        
    except Exception as e:
        _log.error(f"Search failed: {str(e)}")
        raise

# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main():
    """Complete pipeline: PDF → EasyOCR → LLM → ChromaDB"""
    
    _log.info("\n" + "="*80)
    _log.info("COMPLETE PIPELINE: DOCLING + EASYOCR → LLM → CHROMADB")
    _log.info("="*80)
    _log.info(f"Input PDF: {Config.INPUT_PDF}")
    _log.info(f"OCR Engine: EasyOCR")
    _log.info(f"Languages: {Config.EASYOCR_LANGUAGES}")
    _log.info(f"Output: {Config.CHROMA_DB_DIR}")
    
    # Create output directory
    Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        # STEP 1: Extract PDF with EasyOCR
        result, markdown_original = extract_pdf_with_easyocr(Config.INPUT_PDF)
        
        # Save original markdown
        doc_filename = Path(Config.INPUT_PDF).stem
        with (Config.OUTPUT_DIR / f"{doc_filename}_1_original.md").open("w", encoding="utf-8") as fp:
            fp.write(markdown_original)
        _log.info(f"✓ Saved: {doc_filename}_1_original.md")
        
        # STEP 2: Extract images and tables with UUIDs
        images = extract_images_with_uuids(markdown_original)
        tables = extract_tables_with_uuids(result)
        
        # STEP 3: Get LLM descriptions
        if images:
            images = get_image_descriptions(images)
        
        if tables:
            tables = get_table_descriptions(tables)
        
        # Save UUID mapping
        all_items = []
        for img in images:
            all_items.append({
                'uuid': img['uuid'],
                'type': 'image',
                'description': img['description']
            })
        for table in tables:
            all_items.append({
                'uuid': table['uuid'],
                'type': 'table',
                'description': table['description'],
                'caption': table['caption']
            })
        
        with (Config.OUTPUT_DIR / f"{doc_filename}_2_uuid_mapping.json").open("w", encoding="utf-8") as fp:
            json.dump(all_items, fp, indent=2)
        _log.info(f"✓ Saved: {doc_filename}_2_uuid_mapping.json")
        
        # STEP 4: Add descriptions to markdown (with UUIDs)
        if images or tables:
            markdown_with_descriptions = add_descriptions_to_markdown(
                markdown_original, images, tables
            )
        else:
            markdown_with_descriptions = markdown_original
        
        with (Config.OUTPUT_DIR / f"{doc_filename}_3_with_descriptions.md").open("w", encoding="utf-8") as fp:
            fp.write(markdown_with_descriptions)
        _log.info(f"✓ Saved: {doc_filename}_3_with_descriptions.md")
        
        # STEP 5: Clean markdown (remove UUIDs)
        markdown_cleaned = clean_markdown(markdown_with_descriptions)
        
        with (Config.OUTPUT_DIR / f"{doc_filename}_4_cleaned.md").open("w", encoding="utf-8") as fp:
            fp.write(markdown_cleaned)
        _log.info(f"✓ Saved: {doc_filename}_4_cleaned.md")
        
        # STEP 6: Split into chunks
        _log.info("="*80)
        _log.info("SPLITTING TEXT INTO CHUNKS")
        _log.info("="*80)
        
        splitter = MarkdownTextSplitter(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP
        )
        chunks = splitter.split_text(markdown_cleaned)
        _log.info(f"✓ Split into {len(chunks)} chunks")
        
        # STEP 7: Store in ChromaDB
        vectorstore = store_in_chromadb(
            chunks,
            metadata={
                'source': Config.INPUT_PDF,
                'ocr_engine': 'easyocr',
                'languages': ','.join(Config.EASYOCR_LANGUAGES)
            }
        )
        
        # STEP 8: Test search
        _log.info("\n" + "="*80)
        _log.info("TESTING SIMILARITY SEARCH")
        _log.info("="*80)
        
        test_queries = [
            "What are the main findings?",
            "What do the tables show?"
        ]
        
        for query in test_queries[:1]:  # Test first query
            results = search_similar(query, k=2)
        
        # Summary
        _log.info("\n" + "="*80)
        _log.info("PIPELINE COMPLETE!")
        _log.info("="*80)
        _log.info(f"Images processed: {len(images)}")
        _log.info(f"Tables processed: {len(tables)}")
        _log.info(f"Chunks stored: {len(chunks)}")
        _log.info(f"ChromaDB location: {Config.CHROMA_DB_DIR}")
        _log.info(f"\nOutput files in: {Config.OUTPUT_DIR}")
        _log.info(f"  - {doc_filename}_1_original.md")
        _log.info(f"  - {doc_filename}_2_uuid_mapping.json")
        _log.info(f"  - {doc_filename}_3_with_descriptions.md")
        _log.info(f"  - {doc_filename}_4_cleaned.md")
        
        return {
            'images': len(images),
            'tables': len(tables),
            'chunks': len(chunks),
            'success': True
        }
        
    except Exception as e:
        _log.error(f"\n✗ PIPELINE FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


if __name__ == "__main__":
    main()