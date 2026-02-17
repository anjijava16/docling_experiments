"""
Docling + OpenAI Vision: Extract images with UUIDs and get AI descriptions
This script:
1. Extracts images from PDF with base64
2. Assigns UUID to each image
3. Sends to OpenAI Vision API for description
4. Updates markdown with descriptions
"""

import re
import uuid
import json
from docling.document_converter import DocumentConverter
from docling_core.types.doc import ImageRefMode
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI()  # Replace with your API key

def get_image_description(base64_image, image_uuid):
    """
    Send base64 image to OpenAI Vision API and get description
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # or "gpt-4o-mini" for cheaper option
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Describe this image in detail. Focus on what's shown, any text, diagrams, charts, or key visual elements."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1500
        )
        
        description = response.choices[0].message.content
        print(f"  ✓ Got description for {image_uuid}: {description[:80]}...")
        return description
        
    except Exception as e:
        print(f"  ✗ Error getting description for {image_uuid}: {e}")
        return f"Error getting description: {str(e)}"

def extract_base64_images(markdown_text):
    """
    Extract all base64 images from markdown and assign UUIDs
    Returns: List of dicts with {uuid, base64_data, original_markdown}
    """
    # Pattern to match: ![alt](data:image/png;base64,...)
    pattern = r'!\[([^\]]*)\]\(data:image/[^;]+;base64,([^)]+)\)'
    
    images = []
    for match in re.finditer(pattern, markdown_text):
        alt_text = match.group(1)
        base64_data = match.group(2)
        original_markdown = match.group(0)
        
        image_uuid = str(uuid.uuid4())
        
        images.append({
            'uuid': image_uuid,
            'base64': base64_data,
            'alt_text': alt_text,
            'original_markdown': original_markdown
        })
    
    return images

def update_markdown_with_descriptions(markdown_text, image_data_list):
    """
    Update markdown by adding descriptions and UUIDs to images
    """
    updated_markdown = markdown_text
    
    for img_data in image_data_list:
        # Create new markdown with UUID and description
        new_markdown = f"""
<!-- Image UUID: {img_data['uuid']} -->
![{img_data['description']}](data:image/png;base64,{img_data['base64']})

**Image Description (UUID: {img_data['uuid']}):**
{img_data['description']}
"""
        
        # Replace old markdown with new
        updated_markdown = updated_markdown.replace(
            img_data['original_markdown'],
            new_markdown,
            1  # Replace only first occurrence
        )
    
    return updated_markdown

# ============================================================================
# MAIN WORKFLOW
# ============================================================================

print("="*80)
print("DOCLING + OPENAI VISION: Extract Images with Descriptions")
print("="*80)

# Step 1: Extract PDF with Docling
print("\nStep 1: Extracting PDF with Docling...")
pipeline_options = PdfPipelineOptions()
pipeline_options.generate_picture_images = True
pipeline_options.images_scale = 2.0

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)

source = "https://arxiv.org/pdf/2206.01062"
print(f"Converting {source}...")
result = converter.convert(source)

# Export to markdown with embedded base64 images
markdown = result.document.export_to_markdown(image_mode=ImageRefMode.EMBEDDED)
print(f"✓ Conversion complete. Markdown length: {len(markdown)} characters")

# Step 2: Extract all base64 images and assign UUIDs
print("\nStep 2: Extracting base64 images and assigning UUIDs...")
images = extract_base64_images(markdown)
print(f"✓ Found {len(images)} images")

# Step 3: Get descriptions from OpenAI for each image
print("\nStep 3: Getting descriptions from OpenAI Vision API...")
for i, img_data in enumerate(images, 1):
    print(f"\nImage {i}/{len(images)} (UUID: {img_data['uuid']}):")
    print(f"  Base64 length: {len(img_data['base64'])} characters")
    
    # Get description from OpenAI
    description = get_image_description(img_data['base64'], img_data['uuid'])
    img_data['description'] = description

# Step 4: Update markdown with descriptions
print("\nStep 4: Updating markdown with descriptions and UUIDs...")
final_markdown = update_markdown_with_descriptions(markdown, images)

# Save original markdown
with open("output_original.md", "w", encoding="utf-8") as f:
    f.write(markdown)
print("✓ Original markdown saved to: output_original.md")

# Save enhanced markdown with descriptions
with open("output_with_descriptions.md", "w", encoding="utf-8") as f:
    f.write(final_markdown)
print("✓ Enhanced markdown saved to: output_with_descriptions.md")

# Step 5: Save UUID -> Description mapping as JSON
print("\nStep 5: Saving UUID mappings...")
uuid_mapping = {
    img_data['uuid']: {
        'description': img_data['description'],
        'alt_text': img_data['alt_text'],
        'base64_length': len(img_data['base64'])
    }
    for img_data in images
}

with open("image_descriptions.json", "w", encoding="utf-8") as f:
    json.dump(uuid_mapping, f, indent=2)
print("✓ UUID mappings saved to: image_descriptions.json")

# Display summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Total images processed: {len(images)}")
print(f"Original markdown size: {len(markdown)} characters")
print(f"Enhanced markdown size: {len(final_markdown)} characters")
print(f"Size increase: +{len(final_markdown) - len(markdown)} characters")

print("\nUUID -> Description mapping:")
print("-"*80)
for img_data in images:
    print(f"\nUUID: {img_data['uuid']}")
    print(f"Description: {img_data['description'][:100]}...")

print("\n" + "="*80)
print("DONE!")
print("="*80)
print("Files created:")
print("  1. output_original.md - Original markdown with base64 images")
print("  2. output_with_descriptions.md - Enhanced with OpenAI descriptions")
print("  3. image_descriptions.json - UUID to description mappings")

print("=============")
for img_data in images:
    print(f"\nUUID: {img_data['uuid']}")
    print(f"Description: {img_data['description']}...")