"""
PDF to ChromaDB with EasyOCR Engine
====================================

This version uses EasyOCR as the OCR engine instead of the default Tesseract.

Use EasyOCR when:
- Processing scanned documents (not born-digital PDFs)
- Handwritten text
- Poor quality images
- Non-English languages (especially Asian languages)
- Complex backgrounds

Installation:
    pip install easyocr
    
Note: First run will download models (~500MB)
"""

import re
import uuid
import json
import time
from typing import List, Dict, Optional, Tuple
from docling.document_converter import DocumentConverter
from docling_core.types.doc import ImageRefMode, TableItem
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
from docling.document_converter import PdfFormatOption
from openai import OpenAI
from langchain.text_splitter import MarkdownTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document

# ============================================================================
# CONFIGURATION
# ============================================================================

OPENAI_API_KEY = "YOUR_API_KEY_HERE"
OPENAI_MODEL = "gpt-4o-mini"
CHROMA_DB_DIR = "./chroma_db_easyocr"  # Different directory
COLLECTION_NAME = "documents_easyocr"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
BATCH_DELAY = 1

# EasyOCR Configuration
EASYOCR_LANGUAGES = ['en']  # Languages: ['en', 'ch_sim', 'ja', 'ko', 'ar', etc.]
USE_GPU = False  # Set to True if you have CUDA GPU

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
# EXTRACTION WITH EASYOCR
# ============================================================================

def extract_pdf_with_easyocr(pdf_source: str):
    """
    Extract PDF using Docling with EasyOCR engine
    
    KEY DIFFERENCE: Uses EasyOCR instead of default Tesseract
    """
    print(f"\n{'='*80}")
    print("EXTRACTING PDF WITH DOCLING + EASYOCR ENGINE")
    print(f"{'='*80}")
    print(f"Source: {pdf_source}")
    print(f"OCR Engine: EasyOCR")
    print(f"Languages: {EASYOCR_LANGUAGES}")
    print(f"GPU: {'Enabled' if USE_GPU else 'Disabled (CPU)'}")
    
    # Configure EasyOCR options
    easyocr_options = EasyOcrOptions(
        lang=EASYOCR_LANGUAGES,  # List of languages
        use_gpu=USE_GPU,          # Use GPU if available
    )
    
    # Configure pipeline with EasyOCR
    pipeline_options = PdfPipelineOptions()
    pipeline_options.generate_picture_images = True
    pipeline_options.images_scale = 2.0
    pipeline_options.generate_table_images = True
    pipeline_options.ocr_options = easyocr_options  # ← KEY: Set EasyOCR
    
    # Create converter
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    
    print("\nConverting with EasyOCR...")
    print("(First run will download EasyOCR models ~500MB)")
    print("(This may take longer than default OCR)")
    
    result = converter.convert(pdf_source)
    
    # Export to markdown
    markdown = result.document.export_to_markdown(image_mode=ImageRefMode.EMBEDDED)
    
    image_count = markdown.count("data:image")
    print(f"\n✓ Extracted {len(markdown):,} characters")
    print(f"✓ Found {image_count} images")
    
    return result, markdown


def extract_images(markdown: str) -> List[Dict]:
    """Extract base64 images and assign UUIDs"""
    print(f"\n{'='*80}")
    print("EXTRACTING IMAGES")
    print(f"{'='*80}")
    
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
    
    print(f"✓ Found {len(images)} images")
    return images


def extract_tables(result) -> List[Dict]:
    """Extract tables from Docling result"""
    print(f"\n{'='*80}")
    print("EXTRACTING TABLES")
    print(f"{'='*80}")
    
    tables = []
    
    for element, _level in result.document.iterate_items():
        if isinstance(element, TableItem):
            table_uuid = str(uuid.uuid4())
            
            table_markdown = element.export_to_markdown(result.document)
            table_text = element.text if hasattr(element, 'text') else table_markdown
            
            # Handle captions
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
    
    print(f"✓ Found {len(tables)} tables")
    
    for i, table in enumerate(tables[:3], 1):
        print(f"\nTable {i}:")
        print(f"  UUID: {table['uuid'][:8]}...")
        print(f"  Caption: {table['caption'][:50] if table['caption'] else 'No caption'}")
        print(f"  Size: {len(table['markdown'])} characters")
    
    return tables


# ============================================================================
# REST OF THE CODE (SAME AS DEFAULT VERSION)
# ============================================================================

def get_image_descriptions(images: List[Dict]) -> List[Dict]:
    """Get descriptions for images using OpenAI Vision"""
    print(f"\n{'='*80}")
    print("GETTING IMAGE DESCRIPTIONS FROM OPENAI VISION")
    print(f"{'='*80}")
    
    if not images:
        print("No images to process")
        return images
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    for i, img in enumerate(images, 1):
        print(f"\n[{i}/{len(images)}] Processing image {img['uuid'][:8]}...")
        
        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": IMAGE_DESCRIPTION_PROMPT},
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
            print(f"  ✓ {img['description'][:80]}...")
            
        except Exception as e:
            img['description'] = f"Error: {str(e)}"
            print(f"  ✗ Error: {str(e)}")
        
        if i < len(images):
            time.sleep(BATCH_DELAY)
    
    print(f"\n✓ Completed {len(images)} image descriptions")
    return images


def get_table_descriptions(tables: List[Dict]) -> List[Dict]:
    """Get descriptions for tables using OpenAI LLM"""
    print(f"\n{'='*80}")
    print("GETTING TABLE DESCRIPTIONS FROM OPENAI")
    print(f"{'='*80}")
    
    if not tables:
        print("No tables to process")
        return tables
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    for i, table in enumerate(tables, 1):
        print(f"\n[{i}/{len(tables)}] Processing table {table['uuid'][:8]}...")
        
        table_content = f"""
Table Caption: {table['caption'] if table['caption'] else 'No caption'}

Table Data (Markdown format):
{table['markdown']}

Analyze this table and provide a description.
"""
        
        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a data analyst expert at describing tables."},
                    {"role": "user", "content": TABLE_DESCRIPTION_PROMPT + "\n\n" + table_content}
                ],
                max_tokens=400
            )
            
            table['description'] = response.choices[0].message.content
            print(f"  ✓ {table['description'][:80]}...")
            
        except Exception as e:
            table['description'] = f"Error: {str(e)}"
            print(f"  ✗ Error: {str(e)}")
        
        if i < len(tables):
            time.sleep(BATCH_DELAY)
    
    print(f"\n✓ Completed {len(tables)} table descriptions")
    return tables


def add_descriptions_to_markdown(markdown: str, images: List[Dict], tables: List[Dict]) -> str:
    """Add both image and table descriptions to markdown with UUID markers"""
    print(f"\n{'='*80}")
    print("ADDING DESCRIPTIONS TO MARKDOWN")
    print(f"{'='*80}")
    
    updated_markdown = markdown
    
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
    
    print(f"✓ Added {len(images)} image descriptions")
    
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
    
    print(f"✓ Added {len(tables)} table descriptions")
    
    return updated_markdown


def clean_markdown(markdown: str) -> str:
    """Remove UUID markers and 'Description:' labels for clean storage"""
    print(f"\n{'='*80}")
    print("CLEANING MARKDOWN")
    print(f"{'='*80}")
    
    original_length = len(markdown)
    
    cleaned = re.sub(r'<!-- IMAGE_UUID: [a-f0-9\-]+ -->\n?', '', markdown)
    cleaned = re.sub(r'<!-- END_IMAGE -->\n?', '', cleaned)
    cleaned = re.sub(r'\*\*Image UUID: `[a-f0-9\-]+`\*\*\s*\n?', '', cleaned)
    cleaned = re.sub(r'\*\*Description:\*\*\s*', '', cleaned)
    
    cleaned = re.sub(r'<!-- TABLE_UUID: [a-f0-9\-]+ -->\n?', '', cleaned)
    cleaned = re.sub(r'<!-- END_TABLE -->\n?', '', cleaned)
    cleaned = re.sub(r'\*\*Table UUID: `[a-f0-9\-]+`\*\*\s*\n?', '', cleaned)
    cleaned = re.sub(r'\*\*Table Description:\*\*\s*', '', cleaned)
    
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = re.sub(r' +\n', '\n', cleaned)
    cleaned = cleaned.strip()
    
    print(f"✓ Cleaned markdown")
    print(f"  Original: {original_length:,} characters")
    print(f"  Cleaned: {len(cleaned):,} characters")
    print(f"  Removed: {original_length - len(cleaned):,} characters")
    
    return cleaned


def store_in_chromadb(chunks: List[str], metadata: Optional[Dict] = None) -> Chroma:
    """Store text chunks in ChromaDB"""
    print(f"\n{'='*80}")
    print("STORING IN CHROMADB")
    print(f"{'='*80}")
    
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    
    documents = []
    for i, chunk in enumerate(chunks):
        doc_metadata = {"chunk_id": i, "ocr_engine": "easyocr"}
        if metadata:
            doc_metadata.update(metadata)
        documents.append(Document(page_content=chunk, metadata=doc_metadata))
    
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=CHROMA_DB_DIR
    )
    
    print(f"✓ Stored {len(documents)} documents in ChromaDB")
    print(f"✓ Location: {CHROMA_DB_DIR}")
    
    return vectorstore


# ============================================================================
# MAIN METHODS
# ============================================================================

def ingest_pdf(pdf_path: str, save_intermediate: bool = True) -> Dict:
    """
    INGESTION METHOD with EasyOCR
    """
    print("\n" + "="*80)
    print("PDF INGESTION WITH EASYOCR ENGINE")
    print("="*80)
    print(f"PDF: {pdf_path}")
    print(f"OCR: EasyOCR (better for scans, handwriting, multi-language)")
    
    try:
        # Step 1: Extract PDF with EasyOCR
        result, markdown_original = extract_pdf_with_easyocr(pdf_path)
        
        # Steps 2-9: Same as default version
        images = extract_images(markdown_original)
        tables = extract_tables(result)
        
        if images:
            images = get_image_descriptions(images)
        
        if tables:
            tables = get_table_descriptions(tables)
        
        if images or tables:
            markdown_with_descriptions = add_descriptions_to_markdown(
                markdown_original, images, tables
            )
        else:
            markdown_with_descriptions = markdown_original
        
        markdown_cleaned = clean_markdown(markdown_with_descriptions)
        
        splitter = MarkdownTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )
        chunks = splitter.split_text(markdown_cleaned)
        print(f"\n✓ Split into {len(chunks)} chunks")
        
        store_in_chromadb(chunks, metadata={'ocr_engine': 'easyocr'})
        
        if save_intermediate:
            print(f"\n{'='*80}")
            print("SAVING INTERMEDIATE FILES")
            print(f"{'='*80}")
            
            with open("1_original_easyocr.md", "w", encoding="utf-8") as f:
                f.write(markdown_original)
            print("  ✓ 1_original_easyocr.md")
            
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
            
            with open("2_uuid_mapping_easyocr.json", "w", encoding="utf-8") as f:
                json.dump(all_items, f, indent=2)
            print("  ✓ 2_uuid_mapping_easyocr.json")
            
            with open("3_with_descriptions_easyocr.md", "w", encoding="utf-8") as f:
                f.write(markdown_with_descriptions)
            print("  ✓ 3_with_descriptions_easyocr.md")
            
            with open("4_cleaned_easyocr.md", "w", encoding="utf-8") as f:
                f.write(markdown_cleaned)
            print("  ✓ 4_cleaned_easyocr.md")
        
        stats = {
            'pdf_source': pdf_path,
            'ocr_engine': 'easyocr',
            'languages': EASYOCR_LANGUAGES,
            'images_found': len(images),
            'images_described': sum(1 for img in images if img.get('description')),
            'tables_found': len(tables),
            'tables_described': sum(1 for tbl in tables if tbl.get('description')),
            'original_size': len(markdown_original),
            'cleaned_size': len(markdown_cleaned),
            'chunks_created': len(chunks)
        }
        
        print(f"\n{'='*80}")
        print("INGESTION COMPLETE!")
        print(f"{'='*80}")
        print(f"OCR Engine: EasyOCR")
        print(f"Images: {stats['images_described']}/{stats['images_found']}")
        print(f"Tables: {stats['tables_described']}/{stats['tables_found']}")
        print(f"Chunks: {stats['chunks_created']}")
        
        return stats
        
    except Exception as e:
        print(f"\n✗ INGESTION FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


def search_similar(query: str, k: int = 3) -> List[Tuple]:
    """RETRIEVAL METHOD"""
    print(f"\n{'='*80}")
    print(f"SEARCHING: '{query}'")
    print(f"{'='*80}")
    
    try:
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=CHROMA_DB_DIR
        )
        
        results = vectorstore.similarity_search_with_score(query, k=k)
        
        print(f"\nFound {len(results)} results:")
        for i, (doc, score) in enumerate(results, 1):
            print(f"\n[{i}] Score: {score:.4f}")
            print(f"OCR Engine: {doc.metadata.get('ocr_engine', 'unknown')}")
            print(doc.page_content[:200] + "...")
        
        return results
        
    except Exception as e:
        print(f"\n✗ SEARCH FAILED: {str(e)}")
        raise


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    
    print("="*80)
    print("PDF TO CHROMADB - EASYOCR ENGINE VERSION")
    print("="*80)
    print("\nEasyOCR is better for:")
    print("  • Scanned documents")
    print("  • Handwritten text")
    print("  • Poor quality images")
    print("  • Non-English languages")
    print("  • Complex backgrounds")
    
    # Test with a scanned document (use your own)
    PDF_SOURCE = "https://arxiv.org/pdf/2206.01062"
    
    print("\n⚠️  Note: First run will download EasyOCR models (~500MB)")
    print("⚠️  Processing will be slower than default OCR")
    
    # 1. INGEST
    print("\n1. INGESTION WITH EASYOCR")
    print("-"*80)
    stats = ingest_pdf(PDF_SOURCE, save_intermediate=True)
    
    # 2. SEARCH
    print("\n2. RETRIEVAL")
    print("-"*80)
    
    queries = [
        "What do the tables show?",
        "Explain the findings"
    ]
    
    for query in queries[:2]:
        results = search_similar(query, k=2)
    
    print("\n" + "="*80)
    print("DONE!")
    print("="*80)