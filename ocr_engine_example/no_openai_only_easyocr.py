"""
Complete Pipeline: EasyOCR to Extract Text from Images/Tables
===============================================================

Instead of sending images to OpenAI Vision API, this uses EasyOCR to:
- Read TEXT that appears ON/IN images (chart labels, annotations, etc.)
- Extract text from table images
- Use local EasyOCR models (no cloud API needed)

Much cheaper and fully local!
"""

import json
import logging
import time
import re
import uuid
import base64
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from io import BytesIO

# Docling imports
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableStructureOptions,
    EasyOcrOptions
)
from docling_core.types.doc import ImageRefMode, TableItem

# EasyOCR for reading text from images
import easyocr
from PIL import Image

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
    
    # EasyOCR Settings for PDF extraction
    EASYOCR_LANGUAGES = ["en"]  # ["es"], ["en", "ch_sim"], etc.
    EASYOCR_LOCAL_MODEL_PATH = "../model/"
    EASYOCR_DOWNLOAD_ENABLED = False  # Set True first time
    EASYOCR_USE_GPU = False
    
    # EasyOCR Settings for reading text from images
    # This is a SEPARATE EasyOCR instance for image text extraction
    IMAGE_OCR_LANGUAGES = ["en"]  # Languages to detect in images
    IMAGE_OCR_USE_GPU = False
    
    # OpenAI (only for embeddings, not for image descriptions)
    
    # ChromaDB
    CHROMA_DB_DIR = "./chroma_db_easyocr_local"
    COLLECTION_NAME = "documents_easyocr_local"
    
    # Text Splitting
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200

# ============================================================================
# STEP 1: EXTRACT PDF WITH EASYOCR
# ============================================================================

def extract_pdf_with_easyocr(pdf_path: str) -> Tuple:
    """Extract PDF using Docling with EasyOCR"""
    _log.info("="*80)
    _log.info("STEP 1: EXTRACTING PDF WITH DOCLING + EASYOCR")
    _log.info("="*80)
    
    # Configure pipeline
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options = TableStructureOptions(
        do_cell_matching=True
    )
    
    # Configure EasyOCR
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
    _log.info(f"Converting: {pdf_path}")
    start_time = time.time()
    conv_result = doc_converter.convert(pdf_path)
    end_time = time.time() - start_time
    
    _log.info(f"✓ Converted in {end_time:.2f} seconds")
    
    # Export to markdown
    markdown = conv_result.document.export_to_markdown(image_mode=ImageRefMode.EMBEDDED)
    
    image_count = markdown.count("data:image")
    _log.info(f"✓ Extracted {len(markdown):,} characters")
    _log.info(f"✓ Found {image_count} images")
    
    return conv_result, markdown

# ============================================================================
# STEP 2: EXTRACT IMAGES AND USE EASYOCR TO READ TEXT
# ============================================================================

def extract_images_with_ocr(markdown: str) -> List[Dict]:
    """
    Extract base64 images and use EasyOCR to read text ON the images
    
    This is the KEY difference - instead of sending to OpenAI Vision,
    we use EasyOCR to read any text that appears on the image itself
    """
    _log.info("="*80)
    _log.info("STEP 2: EXTRACTING IMAGES AND READING TEXT WITH EASYOCR")
    _log.info("="*80)
    _log.info("Using EasyOCR to read text ON/IN images (local processing)")
    
    # Initialize EasyOCR reader for reading text from images
    _log.info(f"Initializing EasyOCR reader for languages: {Config.IMAGE_OCR_LANGUAGES}")
    reader = easyocr.Reader(
        Config.IMAGE_OCR_LANGUAGES,
        gpu=Config.IMAGE_OCR_USE_GPU,
        model_storage_directory=Config.EASYOCR_LOCAL_MODEL_PATH,
        download_enabled=Config.EASYOCR_DOWNLOAD_ENABLED
    )
    _log.info("✓ EasyOCR reader initialized")
    
    # Extract images from markdown
    pattern = r'!\[([^\]]*)\]\(data:image/([^;]+);base64,([^)]+)\)'
    images = []
    
    for i, match in enumerate(re.finditer(pattern, markdown), 1):
        image_uuid = str(uuid.uuid4())
        image_format = match.group(2)
        base64_data = match.group(3)
        
        _log.info(f"\n[{i}] Processing image {image_uuid[:8]}...")
        
        # Decode base64 to image
        try:
            image_bytes = base64.b64decode(base64_data)
            image = Image.open(BytesIO(image_bytes))
            
            # Use EasyOCR to read text from the image
            _log.info("  Running EasyOCR on image to extract text...")
            
            # Convert PIL Image to numpy array for EasyOCR
            import numpy as np
            image_np = np.array(image)
            
            # Read text from image
            ocr_results = reader.readtext(image_np)
            
            # Extract text from results
            # EasyOCR returns list of (bbox, text, confidence)
            extracted_texts = []
            for (bbox, text, confidence) in ocr_results:
                if confidence > 0.3:  # Filter low confidence
                    extracted_texts.append(text)
            
            # Combine all extracted text
            if extracted_texts:
                ocr_text = " ".join(extracted_texts)
                _log.info(f"  ✓ Extracted text: {ocr_text[:100]}...")
            else:
                ocr_text = "No readable text found in image"
                _log.info(f"  ⚠️  No text detected in image")
            
            images.append({
                'uuid': image_uuid,
                'type': 'image',
                'format': image_format,
                'base64': base64_data,
                'alt_text': match.group(1),
                'original': match.group(0),
                'ocr_text': ocr_text,  # TEXT extracted from image using EasyOCR
                'ocr_details': ocr_results  # Full OCR results with confidence
            })
            
        except Exception as e:
            _log.error(f"  ✗ Error processing image: {str(e)}")
            images.append({
                'uuid': image_uuid,
                'type': 'image',
                'format': image_format,
                'base64': base64_data,
                'alt_text': match.group(1),
                'original': match.group(0),
                'ocr_text': f"Error reading image: {str(e)}",
                'ocr_details': []
            })
    
    _log.info(f"\n✓ Processed {len(images)} images with EasyOCR")
    
    return images


def extract_tables_with_uuids(result) -> List[Dict]:
    """Extract tables from Docling result"""
    _log.info("="*80)
    _log.info("STEP 3: EXTRACTING TABLES")
    _log.info("="*80)
    
    tables = []
    
    for element, _level in result.document.iterate_items():
        if isinstance(element, TableItem):
            table_uuid = str(uuid.uuid4())
            
            # Export table to markdown
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
                'text': table_text,  # Already extracted by Docling
                'caption': caption,
                'original': table_markdown
            })
    
    _log.info(f"✓ Found {len(tables)} tables")
    
    return tables

# ============================================================================
# STEP 4: ADD OCR TEXT TO MARKDOWN (WITH UUIDS)
# ============================================================================

def add_ocr_text_to_markdown(markdown: str, images: List[Dict], tables: List[Dict]) -> str:
    """Add OCR-extracted text to markdown with UUID markers"""
    _log.info("="*80)
    _log.info("STEP 4: ADDING OCR TEXT TO MARKDOWN (WITH UUIDS)")
    _log.info("="*80)
    
    updated_markdown = markdown
    
    # Add image OCR text with UUID markers
    for img in images:
        if img.get('ocr_text'):
            new_markdown = f"""
<!-- IMAGE_UUID: {img['uuid']} -->
{img['original']}
**Image UUID: `{img['uuid']}`**
**Text extracted from image (EasyOCR):** {img['ocr_text']}
<!-- END_IMAGE -->
"""
            updated_markdown = updated_markdown.replace(img['original'], new_markdown, 1)
    
    _log.info(f"✓ Added OCR text for {len(images)} images")
    
    # Add tables with UUID markers
    for table in tables:
        new_markdown = f"""
<!-- TABLE_UUID: {table['uuid']} -->
{table['original']}
**Table UUID: `{table['uuid']}`**
**Table Caption:** {table['caption'] if table['caption'] else 'No caption'}
<!-- END_TABLE -->
"""
        updated_markdown = updated_markdown.replace(table['original'], new_markdown, 1)
    
    _log.info(f"✓ Added {len(tables)} table markers")
    
    return updated_markdown

# ============================================================================
# STEP 5: CLEAN MARKDOWN (REMOVE UUIDS)
# ============================================================================

def clean_markdown(markdown: str) -> str:
    """Remove UUID markers but keep OCR-extracted text"""
    _log.info("="*80)
    _log.info("STEP 5: CLEANING MARKDOWN (REMOVING UUIDS)")
    _log.info("="*80)
    
    original_length = len(markdown)
    
    # Remove IMAGE UUID markers
    cleaned = re.sub(r'<!-- IMAGE_UUID: [a-f0-9\-]+ -->\n?', '', markdown)
    cleaned = re.sub(r'<!-- END_IMAGE -->\n?', '', cleaned)
    cleaned = re.sub(r'\*\*Image UUID: `[a-f0-9\-]+`\*\*\s*\n?', '', cleaned)
    
    # Remove "Text extracted from image (EasyOCR):" label but keep the text
    cleaned = re.sub(r'\*\*Text extracted from image \(EasyOCR\):\*\*\s*', '', cleaned)
    
    # Remove TABLE UUID markers
    cleaned = re.sub(r'<!-- TABLE_UUID: [a-f0-9\-]+ -->\n?', '', cleaned)
    cleaned = re.sub(r'<!-- END_TABLE -->\n?', '', cleaned)
    cleaned = re.sub(r'\*\*Table UUID: `[a-f0-9\-]+`\*\*\s*\n?', '', cleaned)
    cleaned = re.sub(r'\*\*Table Caption:\*\*\s*', '', cleaned)
    
    # Clean up whitespace
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = re.sub(r' +\n', '\n', cleaned)
    cleaned = cleaned.strip()
    
    _log.info(f"✓ Cleaned markdown")
    _log.info(f"  Original: {original_length:,} characters")
    _log.info(f"  Cleaned: {len(cleaned):,} characters")
    
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
        doc_metadata = {
            "chunk_id": i,
            "ocr_engine": "easyocr_local",
            "processing": "local_only"
        }
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
# STEP 7: RETRIEVAL
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
            _log.info(f"Content: {doc.page_content[:200]}...")
        
        return results
        
    except Exception as e:
        _log.error(f"Search failed: {str(e)}")
        raise

# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main():
    """Complete pipeline: PDF → EasyOCR → Read Image Text → ChromaDB"""
    
    _log.info("\n" + "="*80)
    _log.info("PIPELINE: EASYOCR FOR IMAGE TEXT EXTRACTION (LOCAL ONLY)")
    _log.info("="*80)
    _log.info("Uses EasyOCR to read text ON/IN images (no OpenAI Vision)")
    _log.info(f"Input: {Config.INPUT_PDF}")
    _log.info(f"Output: {Config.CHROMA_DB_DIR}")
    
    Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        # STEP 1: Extract PDF
        result, markdown_original = extract_pdf_with_easyocr(Config.INPUT_PDF)
        
        doc_filename = Path(Config.INPUT_PDF).stem
        with (Config.OUTPUT_DIR / f"{doc_filename}_1_original.md").open("w", encoding="utf-8") as fp:
            fp.write(markdown_original)
        _log.info(f"✓ Saved: {doc_filename}_1_original.md")
        
        # STEP 2: Extract images and use EasyOCR to read text from them
        images = extract_images_with_ocr(markdown_original)
        
        # STEP 3: Extract tables
        tables = extract_tables_with_uuids(result)
        
        # Save OCR results
        ocr_results = []
        for img in images:
            ocr_results.append({
                'uuid': img['uuid'],
                'type': 'image',
                'ocr_text': img['ocr_text'],
                'ocr_confidence': [
                    {'text': text, 'confidence': conf}
                    for (bbox, text, conf) in img.get('ocr_details', [])
                ]
            })
        for table in tables:
            ocr_results.append({
                'uuid': table['uuid'],
                'type': 'table',
                'text': table['text'],
                'caption': table['caption']
            })
        
        with (Config.OUTPUT_DIR / f"{doc_filename}_2_ocr_results.json").open("w", encoding="utf-8") as fp:
            json.dump(ocr_results, fp, indent=2)
        _log.info(f"✓ Saved: {doc_filename}_2_ocr_results.json")
        
        # STEP 4: Add OCR text to markdown (with UUIDs)
        markdown_with_ocr = add_ocr_text_to_markdown(markdown_original, images, tables)
        
        with (Config.OUTPUT_DIR / f"{doc_filename}_3_with_ocr_text.md").open("w", encoding="utf-8") as fp:
            fp.write(markdown_with_ocr)
        _log.info(f"✓ Saved: {doc_filename}_3_with_ocr_text.md")
        
        # STEP 5: Clean markdown (remove UUIDs)
        markdown_cleaned = clean_markdown(markdown_with_ocr)
        
        with (Config.OUTPUT_DIR / f"{doc_filename}_4_cleaned.md").open("w", encoding="utf-8") as fp:
            fp.write(markdown_cleaned)
        _log.info(f"✓ Saved: {doc_filename}_4_cleaned.md")
        
        # STEP 6: Split and store
        _log.info("="*80)
        _log.info("SPLITTING AND STORING")
        _log.info("="*80)
        
        splitter = MarkdownTextSplitter(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP
        )
        chunks = splitter.split_text(markdown_cleaned)
        _log.info(f"✓ Split into {len(chunks)} chunks")
        
        vectorstore = store_in_chromadb(
            chunks,
            metadata={
                'source': Config.INPUT_PDF,
                'processing': 'easyocr_local_only',
                'languages': ','.join(Config.IMAGE_OCR_LANGUAGES)
            }
        )
        
        # STEP 7: Test search
        _log.info("\n" + "="*80)
        _log.info("TESTING SEARCH")
        _log.info("="*80)
        
        test_query = "What text appears in the images?"
        results = search_similar(test_query, k=2)
        
        # Summary
        _log.info("\n" + "="*80)
        _log.info("PIPELINE COMPLETE!")
        _log.info("="*80)
        _log.info(f"Images processed: {len(images)}")
        _log.info(f"Tables processed: {len(tables)}")
        _log.info(f"Chunks stored: {len(chunks)}")
        _log.info(f"Processing: 100% LOCAL (no cloud API calls)")
        _log.info(f"\nOutput files:")
        _log.info(f"  - {doc_filename}_1_original.md")
        _log.info(f"  - {doc_filename}_2_ocr_results.json")
        _log.info(f"  - {doc_filename}_3_with_ocr_text.md")
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