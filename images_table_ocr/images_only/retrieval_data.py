"""
PDF to ChromaDB Pipeline with Docling
======================================

This script provides two main methods:
1. ingest_pdf() - Extract PDF, get OpenAI descriptions, clean, and store in ChromaDB
2. retrieve_similar() - Query ChromaDB for similarity search

Usage:
    # Ingestion
    ingest_pdf("path/to/document.pdf")
    
    # Retrieval
    results = retrieve_similar("your search query", k=3)
"""

import re
import uuid
import json
import time
from typing import List, Dict, Optional, Tuple
from pathlib import Path

# Docling imports
from docling.document_converter import DocumentConverter
from docling_core.types.doc import ImageRefMode
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption

# OpenAI imports
from openai import OpenAI

# LangChain and ChromaDB imports
from langchain_text_splitters import MarkdownTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
#from langchain.schema import Document
from langchain_core.documents import Document

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Configuration settings"""
    
    # OpenAI Settings
   # OPENAI_API_KEY = "YOUR_API_KEY_HERE"  # Replace with your API key
    OPENAI_MODEL = "gpt-4o-mini"  # or "gpt-4o" for higher quality
    
    # ChromaDB Settings
    CHROMA_DB_DIR = "./chroma_db"  # Where to store ChromaDB
    COLLECTION_NAME = "pdf_documents"  # Collection name in ChromaDB
    
    # Description Settings
    DESCRIPTION_PROMPT = """Describe this image in detail. Focus on:
- Type of visualization (chart, diagram, photo, etc.)
- Key visual elements and their relationships
- Main information or insights conveyed
Keep it concise (2-3 sentences)."""
    
    # Text Splitting Settings
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    
    # Processing Settings
    BATCH_DELAY = 1  # Seconds between OpenAI requests
    
    # Docling Settings
    GENERATE_IMAGES = True
    IMAGE_SCALE = 2.0

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_pdf_with_docling(pdf_source: str) -> str:
    """
    Extract PDF using Docling with base64 images
    
    Args:
        pdf_source: Path or URL to PDF file
        
    Returns:
        Markdown string with embedded base64 images
    """
    print(f"\n{'='*80}")
    print("EXTRACTING PDF WITH DOCLING")
    print(f"{'='*80}")
    print(f"Source: {pdf_source}")
    
    # Configure pipeline
    pipeline_options = PdfPipelineOptions()
    pipeline_options.generate_picture_images = Config.GENERATE_IMAGES
    pipeline_options.images_scale = Config.IMAGE_SCALE
    
    # Create converter
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    
    # Convert
    print("Converting... (this may take a moment)")
    result = converter.convert(pdf_source)
    
    # Export to markdown
    markdown = result.document.export_to_markdown(image_mode=ImageRefMode.EMBEDDED)
    
    image_count = markdown.count("data:image")
    print(f"✓ Extracted {len(markdown):,} characters")
    print(f"✓ Found {image_count} images")
    
    return markdown


def extract_images_with_uuids(markdown_text: str) -> List[Dict]:
    """
    Extract base64 images from markdown and assign UUIDs
    
    Args:
        markdown_text: Markdown with embedded images
        
    Returns:
        List of image dictionaries with UUID, base64, format, etc.
    """
    print(f"\n{'='*80}")
    print("EXTRACTING IMAGES AND ASSIGNING UUIDS")
    print(f"{'='*80}")
    
    pattern = r'!\[([^\]]*)\]\(data:image/([^;]+);base64,([^)]+)\)'
    
    images = []
    for match in re.finditer(pattern, markdown_text):
        image_uuid = str(uuid.uuid4())
        
        images.append({
            'uuid': image_uuid,
            'alt_text': match.group(1),
            'format': match.group(2),
            'base64': match.group(3),
            'original_markdown': match.group(0),
            'description': None
        })
    
    print(f"✓ Found {len(images)} images")
    
    return images


def get_openai_descriptions(images: List[Dict]) -> List[Dict]:
    """
    Get descriptions for images using OpenAI Vision API
    
    Args:
        images: List of image dictionaries
        
    Returns:
        Updated images list with descriptions
    """
    print(f"\n{'='*80}")
    print("GETTING DESCRIPTIONS FROM OPENAI VISION")
    print(f"{'='*80}")
    
    if not images:
        print("No images to process")
        return images
    
    client = OpenAI()
    
    for i, img in enumerate(images, 1):
        print(f"\n[{i}/{len(images)}] Processing image {img['uuid'][:8]}...")
        
        try:
            response = client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": Config.DESCRIPTION_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{img['format']};base64,{img['base64']}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300
            )
            
            description = response.choices[0].message.content
            img['description'] = description
            print(f"  ✓ {description[:80]}...")
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            img['description'] = error_msg
            print(f"  ✗ {error_msg}")
        
        # Rate limiting
        if i < len(images):
            time.sleep(Config.BATCH_DELAY)
    
    print(f"\n✓ Completed {len(images)} descriptions")
    
    return images


def add_descriptions_to_markdown(markdown_text: str, images: List[Dict]) -> str:
    """
    Add descriptions to markdown with UUID markers
    
    Args:
        markdown_text: Original markdown
        images: List of images with descriptions
        
    Returns:
        Markdown with descriptions and UUID markers
    """
    print(f"\n{'='*80}")
    print("ADDING DESCRIPTIONS TO MARKDOWN")
    print(f"{'='*80}")
    
    updated_markdown = markdown_text
    
    for img in images:
        if img['description']:
            new_markdown = f"""
<!-- IMAGE_UUID: {img['uuid']} -->
{img['original_markdown']}
**Image UUID: `{img['uuid']}`**
**Description:** {img['description']}
<!-- END_IMAGE -->
"""
            
            updated_markdown = updated_markdown.replace(
                img['original_markdown'],
                new_markdown,
                1
            )
    
    print(f"✓ Added {len(images)} descriptions")
    
    return updated_markdown


def clean_markdown(markdown_text: str) -> str:
    """
    Remove UUID markers and 'Description:' labels for clean storage
    
    Args:
        markdown_text: Markdown with metadata
        
    Returns:
        Cleaned markdown
    """
    print(f"\n{'='*80}")
    print("CLEANING MARKDOWN")
    print(f"{'='*80}")
    
    original_length = len(markdown_text)
    
    # Remove UUID comment markers
    cleaned = re.sub(r'<!-- IMAGE_UUID: [a-f0-9\-]+ -->\n?', '', markdown_text)
    cleaned = re.sub(r'<!-- END_IMAGE -->\n?', '', cleaned)
    
    # Remove Image UUID display lines
    cleaned = re.sub(r'\*\*Image UUID: `[a-f0-9\-]+`\*\*\s*\n?', '', cleaned)
    
    # Remove "Description:" label but keep the description text
    cleaned = re.sub(r'\*\*Description:\*\*\s*', '', cleaned)
    
    # Clean up multiple consecutive newlines
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    # Clean up spaces before newlines
    cleaned = re.sub(r' +\n', '\n', cleaned)
    
    cleaned = cleaned.strip()
    
    print(f"✓ Cleaned markdown")
    print(f"  Original: {original_length:,} characters")
    print(f"  Cleaned: {len(cleaned):,} characters")
    print(f"  Removed: {original_length - len(cleaned):,} characters")
    
    return cleaned


def split_text_into_chunks(text: str) -> List[str]:
    """
    Split text into chunks for embedding
    
    Args:
        text: Text to split
        
    Returns:
        List of text chunks
    """
    print(f"\n{'='*80}")
    print("SPLITTING TEXT INTO CHUNKS")
    print(f"{'='*80}")
    
    text_splitter = MarkdownTextSplitter(
        chunk_size=Config.CHUNK_SIZE,
        chunk_overlap=Config.CHUNK_OVERLAP
    )
    
    chunks = text_splitter.split_text(text)
    
    print(f"✓ Created {len(chunks)} chunks")
    print(f"  Chunk size: {Config.CHUNK_SIZE}")
    print(f"  Overlap: {Config.CHUNK_OVERLAP}")
    
    return chunks


def store_in_chromadb(chunks: List[str], metadata: Optional[Dict] = None) -> Chroma:
    """
    Store text chunks in ChromaDB
    
    Args:
        chunks: List of text chunks
        metadata: Optional metadata to add to documents
        
    Returns:
        ChromaDB vectorstore
    """
    print(f"\n{'='*80}")
    print("STORING IN CHROMADB")
    print(f"{'='*80}")
    
    # Initialize embeddings
    embeddings = OpenAIEmbeddings()
    
    # Create documents with metadata
    documents = []
    for i, chunk in enumerate(chunks):
        doc_metadata = {"chunk_id": i}
        if metadata:
            doc_metadata.update(metadata)
        
        documents.append(
            Document(page_content=chunk, metadata=doc_metadata)
        )
    
    print(f"Creating ChromaDB collection '{Config.COLLECTION_NAME}'...")
    
    # Create or update ChromaDB
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=Config.COLLECTION_NAME,
        persist_directory=Config.CHROMA_DB_DIR
    )
    
    print(f"✓ Stored {len(documents)} documents in ChromaDB")
    print(f"✓ Database location: {Config.CHROMA_DB_DIR}")
    
    return vectorstore


def load_chromadb() -> Chroma:
    """
    Load existing ChromaDB
    
    Returns:
        ChromaDB vectorstore
    """
    embeddings = OpenAIEmbeddings()
    
    vectorstore = Chroma(
        collection_name=Config.COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=Config.CHROMA_DB_DIR
    )
    
    return vectorstore


# ============================================================================
# MAIN METHODS: INGESTION AND RETRIEVAL
# ============================================================================

def ingest_pdf(
    pdf_source: str,
    save_intermediate: bool = True,
    add_metadata: Optional[Dict] = None
) -> Dict:
    """
    INGESTION METHOD
    
    Complete pipeline to ingest a PDF into ChromaDB:
    1. Extract PDF with Docling
    2. Extract images and assign UUIDs
    3. Get OpenAI descriptions for images
    4. Add descriptions to markdown
    5. Clean markdown (remove UUIDs and labels)
    6. Split into chunks
    7. Store in ChromaDB
    
    Args:
        pdf_source: Path or URL to PDF file
        save_intermediate: Whether to save intermediate files
        add_metadata: Optional metadata to add to all chunks
        
    Returns:
        Dictionary with statistics and file paths
    """
    print("\n" + "="*80)
    print("PDF INGESTION PIPELINE")
    print("="*80)
    print(f"PDF: {pdf_source}")
    print(f"ChromaDB: {Config.CHROMA_DB_DIR}")
    print(f"Collection: {Config.COLLECTION_NAME}")
    
    try:
        # Step 1: Extract PDF
        markdown_original = extract_pdf_with_docling(pdf_source)
        
        # Step 2: Extract images with UUIDs
        images = extract_images_with_uuids(markdown_original)
        
        # Step 3: Get OpenAI descriptions
        if images:
            images = get_openai_descriptions(images)
        
        # Step 4: Add descriptions to markdown
        if images:
            markdown_with_descriptions = add_descriptions_to_markdown(
                markdown_original, 
                images
            )
        else:
            markdown_with_descriptions = markdown_original
        
        # Step 5: Clean markdown
        markdown_cleaned = clean_markdown(markdown_with_descriptions)
        
        # Step 6: Split into chunks
        chunks = split_text_into_chunks(markdown_cleaned)
        
        # Step 7: Store in ChromaDB
        vectorstore = store_in_chromadb(chunks, metadata=add_metadata)
        
        # Save intermediate files if requested
        if save_intermediate:
            print(f"\n{'='*80}")
            print("SAVING INTERMEDIATE FILES")
            print(f"{'='*80}")
            
            files_saved = []
            
            # Save original
            with open("1_original.md", "w", encoding="utf-8") as f:
                f.write(markdown_original)
            files_saved.append("1_original.md")
            
            # Save UUID mapping
            if images:
                uuid_mapping = {
                    img['uuid']: {
                        'description': img['description'],
                        'format': img['format'],
                        'alt_text': img['alt_text']
                    }
                    for img in images
                }
                with open("2_uuid_mapping.json", "w", encoding="utf-8") as f:
                    json.dump(uuid_mapping, f, indent=2)
                files_saved.append("2_uuid_mapping.json")
            
            # Save with descriptions
            with open("3_with_descriptions.md", "w", encoding="utf-8") as f:
                f.write(markdown_with_descriptions)
            files_saved.append("3_with_descriptions.md")
            
            # Save cleaned
            with open("4_cleaned.md", "w", encoding="utf-8") as f:
                f.write(markdown_cleaned)
            files_saved.append("4_cleaned.md")
            
            for file in files_saved:
                print(f"  ✓ {file}")
        
        # Statistics
        stats = {
            'pdf_source': pdf_source,
            'images_found': len(images),
            'images_described': sum(1 for img in images if img.get('description')),
            'original_size': len(markdown_original),
            'cleaned_size': len(markdown_cleaned),
            'chunks_created': len(chunks),
            'chromadb_location': Config.CHROMA_DB_DIR,
            'collection_name': Config.COLLECTION_NAME
        }
        
        # Print summary
        print(f"\n{'='*80}")
        print("INGESTION COMPLETE!")
        print(f"{'='*80}")
        print(f"Images processed: {stats['images_described']}/{stats['images_found']}")
        print(f"Original size: {stats['original_size']:,} characters")
        print(f"Cleaned size: {stats['cleaned_size']:,} characters")
        print(f"Chunks stored: {stats['chunks_created']}")
        print(f"ChromaDB: {stats['chromadb_location']}")
        print(f"Collection: {stats['collection_name']}")
        
        return stats
        
    except Exception as e:
        print(f"\n✗ INGESTION FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


def retrieve_similar(
    query: str,
    k: int = 3,
    return_scores: bool = True,
    filter_metadata: Optional[Dict] = None
) -> List[Tuple[Document, float]]:
    """
    RETRIEVAL METHOD
    
    Query ChromaDB for similar documents
    
    Args:
        query: Search query
        k: Number of results to return
        return_scores: Whether to return similarity scores
        filter_metadata: Optional metadata filter
        
    Returns:
        List of (Document, score) tuples if return_scores=True,
        otherwise list of Documents
    """
    print(f"\n{'='*80}")
    print("SIMILARITY SEARCH")
    print(f"{'='*80}")
    print(f"Query: '{query}'")
    print(f"Results: {k}")
    
    try:
        # Load ChromaDB
        vectorstore = load_chromadb()
        
        # Perform search
        if return_scores:
            results = vectorstore.similarity_search_with_score(
                query, 
                k=k,
                filter=filter_metadata
            )
        else:
            results = vectorstore.similarity_search(
                query,
                k=k,
                filter=filter_metadata
            )
        
        # Display results
        print(f"\nFound {len(results)} results:")
        print("-" * 80)
        
        if return_scores:
            for i, (doc, score) in enumerate(results, 1):
                print(f"\n[Result {i}] Similarity Score: {score:.4f}")
                print("-" * 80)
                print(doc.page_content[:300])
                if len(doc.page_content) > 300:
                    print("...")
                print(f"Metadata: {doc.metadata}")
        else:
            for i, doc in enumerate(results, 1):
                print(f"\n[Result {i}]")
                print("-" * 80)
                print(doc.page_content[:300])
                if len(doc.page_content) > 300:
                    print("...")
                print(f"Metadata: {doc.metadata}")
        
        return results
        
    except Exception as e:
        print(f"\n✗ RETRIEVAL FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    
    # Example queries
    test_queries = [
        "What is Docling ?",
    ]
    
    for query in test_queries[:2]:  # Run first 2 as examples
        results = retrieve_similar(
            query=query,
            k=3,
            return_scores=True
        )
        for i, (doc, score) in enumerate(results, 1):
                print(f"\n[Result {i}] Similarity Score: {score:.4f}")
                print(doc.page_content)
        print(f" ✓ Retrieved {len(results)} results for query: '{query}' and result is ={results}")
        print("\n")
    
    print("\n" + "="*80)
    print("USAGE EXAMPLES")
    print("="*80)