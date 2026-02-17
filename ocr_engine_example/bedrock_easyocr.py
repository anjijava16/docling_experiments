"""
Complete Pipeline: Docling + EasyOCR → Claude (Bedrock) → Titan → ChromaDB
===========================================================================

AWS Native Version — No OpenAI
"""

import json
import logging
import time
import re
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import boto3

# Docling imports
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableStructureOptions,
    EasyOcrOptions
)
from docling_core.types.doc import ImageRefMode, TableItem

# LangChain + Chroma
#from langchain_community.embeddings import BedrockEmbeddings
from langchain_aws import BedrockEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import MarkdownTextSplitter
from langchain_core.documents import Document

logging.basicConfig(level=logging.INFO)
_log = logging.getLogger(__name__)

# ================= CONFIG =================

class Config:
    INPUT_PDF = "2408.09869v5.pdf"
    OUTPUT_DIR = Path("scratch")

    # EasyOCR
    EASYOCR_LANGUAGES = ["en"]
    EASYOCR_LOCAL_MODEL_PATH = "../model/"
    EASYOCR_DOWNLOAD_ENABLED = False
    EASYOCR_USE_GPU = False

    # Bedrock Models
    CLAUDE_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
    TITAN_EMBED_MODEL = "amazon.titan-embed-text-v1"

    # Chroma
    CHROMA_DB_DIR = "./chroma_db_bedrock"
    COLLECTION_NAME = "documents_bedrock"

    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200

    IMAGE_DESCRIPTION_PROMPT = """Describe this image in detail. Focus on:
- Type of visualization
- Key visual elements
- Main information conveyed
Keep it concise."""

    TABLE_DESCRIPTION_PROMPT = """Analyze this table and describe:
- What the table shows
- Key columns
- Important insights
Keep concise."""


# ======== BEDROCK CLIENT ========

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")


# ================= STEP 1 =================

def extract_pdf_with_easyocr(pdf_path: str) -> Tuple:
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options = TableStructureOptions(
        do_cell_matching=True
    )

    pipeline_options.ocr_options = EasyOcrOptions(
        lang=Config.EASYOCR_LANGUAGES,
        model_storage_directory=Config.EASYOCR_LOCAL_MODEL_PATH,
        download_enabled=Config.EASYOCR_DOWNLOAD_ENABLED,
        use_gpu=Config.EASYOCR_USE_GPU
    )

    pipeline_options.generate_picture_images = True

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    result = converter.convert(pdf_path)
    markdown = result.document.export_to_markdown(
        image_mode=ImageRefMode.EMBEDDED
    )

    return result, markdown


# ================= STEP 2 =================

def extract_images_with_uuids(markdown: str) -> List[Dict]:
    pattern = r'!\[([^\]]*)\]\(data:image/([^;]+);base64,([^)]+)\)'
    images = []

    for match in re.finditer(pattern, markdown):
        images.append({
            "uuid": str(uuid.uuid4()),
            "format": match.group(2),
            "base64": match.group(3),
            "original": match.group(0),
            "description": None
        })

    return images


def extract_tables_with_uuids(result) -> List[Dict]:
    tables = []

    for element, _ in result.document.iterate_items():
        if isinstance(element, TableItem):
            tables.append({
                "uuid": str(uuid.uuid4()),
                "markdown": element.export_to_markdown(result.document),
                "description": None
            })

    return tables


# ================= STEP 3A =================
# IMAGE DESCRIPTIONS (Claude Vision)

def get_image_descriptions(images: List[Dict]) -> List[Dict]:
    for img in images:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300,
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": f"image/{img['format']}",
                            "data": img["base64"]
                        }
                    },
                    {
                        "type": "text",
                        "text": Config.IMAGE_DESCRIPTION_PROMPT
                    }
                ]
            }]
        }

        response = bedrock.invoke_model(
            modelId=Config.CLAUDE_MODEL_ID,
            body=json.dumps(body)
        )

        result = json.loads(response["body"].read())
        img["description"] = result["content"][0]["text"]

    return images


# ================= STEP 3B =================
# TABLE DESCRIPTIONS (Claude Text)

def get_table_descriptions(tables: List[Dict]) -> List[Dict]:
    for table in tables:

        prompt = f"""
{Config.TABLE_DESCRIPTION_PROMPT}

Table:
{table['markdown']}
"""

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 400,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        response = bedrock.invoke_model(
            modelId=Config.CLAUDE_MODEL_ID,
            body=json.dumps(body)
        )

        result = json.loads(response["body"].read())
        table["description"] = result["content"][0]["text"]

    return tables


# ================= STEP 4 =================

def add_descriptions(markdown, images, tables):
    for img in images:
        markdown = markdown.replace(
            img["original"],
            img["original"] + "\n\n" + img["description"],
            1
        )

    for table in tables:
        markdown = markdown.replace(
            table["markdown"],
            table["markdown"] + "\n\n" + table["description"],
            1
        )

    return markdown


# ================= STEP 5 =================
# CHUNKING + TITAN EMBEDDINGS

def store_in_chromadb(text):
    splitter = MarkdownTextSplitter(
        chunk_size=Config.CHUNK_SIZE,
        chunk_overlap=Config.CHUNK_OVERLAP
    )

    chunks = splitter.split_text(text)

    embeddings = BedrockEmbeddings(
        client=boto3.client("bedrock-runtime"),
        model_id=Config.TITAN_EMBED_MODEL
    )

    docs = [
        Document(page_content=c, metadata={"source": Config.INPUT_PDF})
        for c in chunks
    ]

    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=Config.COLLECTION_NAME,
        persist_directory=Config.CHROMA_DB_DIR
    )

    return vectorstore


# ================= MAIN =================

def main():
    result, markdown = extract_pdf_with_easyocr(Config.INPUT_PDF)

    images = extract_images_with_uuids(markdown)
    tables = extract_tables_with_uuids(result)

    if images:
        images = get_image_descriptions(images)

    if tables:
        tables = get_table_descriptions(tables)

    markdown = add_descriptions(markdown, images, tables)

    store_in_chromadb(markdown)

    print("PIPELINE COMPLETE")


if __name__ == "__main__":
    main()
