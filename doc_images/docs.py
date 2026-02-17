"""
FLEXIBLE VERSION: Customize how descriptions are added to markdown
Options for placing descriptions:
1. As alt text
2. Below image with UUID
3. In separate section
4. As HTML comments
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

# ============================================================================
# CONFIGURATION
# ============================================================================

# OpenAI Configuration
OPENAI_MODEL = "gpt-4o"  # Options: "gpt-4o", "gpt-4o-mini", "gpt-4-turbo"

# Description Prompt (customize this!)
DESCRIPTION_PROMPT = """Describe this image in detail. Focus on:
- What type of image it is (diagram, chart, photo, screenshot, etc.)
- Key visual elements and their relationships
- Any text, labels, or annotations visible
- The main purpose or message of the image
Keep it concise but informative (2-3 sentences)."""

# Description Placement Options:
# "alt_text" - Replace alt text with description
# "below" - Add description paragraph below image with UUID
# "caption" - Add as italicized caption below image
# "comment" - Add as HTML comment above image
# "section" - Add all descriptions in a separate section at the end
DESCRIPTION_STYLE = "below"  # Change this to customize placement

# PDF Source
PDF_SOURCE = "https://arxiv.org/pdf/2206.01062"
PDF_SOURCE="https://arxiv.org/pdf/2408.09869"
# ============================================================================
# FUNCTIONS
# ============================================================================

def get_image_description(base64_image, image_uuid, prompt=DESCRIPTION_PROMPT):
    """Send base64 image to OpenAI Vision API and get description"""
    try:
        client = OpenAI()
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300
        )
        print(base64_image)
        

        
        description = response.choices[0].message.content
        print(f"  ✓ UUID {image_uuid[:8]}...: {description[:60]}...")
        return description
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"  ✗ UUID {image_uuid[:8]}...: {error_msg}")
        return error_msg

def extract_base64_images(markdown_text):
    """Extract all base64 images from markdown and assign UUIDs"""
    pattern = r'!\[([^\]]*)\]\(data:image/([^;]+);base64,([^)]+)\)'
    
    images = []
    for match in re.finditer(pattern, markdown_text):
        alt_text = match.group(1)
        image_format = match.group(2)  # png, jpeg, etc.
        base64_data = match.group(3)
        original_markdown = match.group(0)
        
        image_uuid = str(uuid.uuid4())
        
        images.append({
            'uuid': image_uuid,
            'base64': base64_data,
            'format': image_format,
            'alt_text': alt_text,
            'original_markdown': original_markdown,
            'description': None
        })
    
    return images

def format_image_with_description(img_data, style):
    """Format image markdown based on chosen style"""
    
    if style == "alt_text":
        # Replace alt text with description
        return f"![{img_data['description']}](data:image/{img_data['format']};base64,{img_data['base64']})"
    
    elif style == "below":
        # Add description below with UUID
        return f"""![{img_data['alt_text']}](data:image/{img_data['format']};base64,{img_data['base64']})

**Image UUID: `{img_data['uuid']}`**  
**Description:** {img_data['description']}
"""
    
    elif style == "caption":
        # Add as italic caption
        return f"""![{img_data['alt_text']}](data:image/{img_data['format']};base64,{img_data['base64']})

*{img_data['description']}* (UUID: `{img_data['uuid']}`)
"""
    
    elif style == "comment":
        # Add as HTML comment above
        return f"""<!-- UUID: {img_data['uuid']} | Description: {img_data['description']} -->
![{img_data['alt_text']}](data:image/{img_data['format']};base64,{img_data['base64']})"""
    
    else:
        # Default: keep original
        return img_data['original_markdown']

def update_markdown_with_descriptions(markdown_text, images, style):
    """Update markdown with descriptions based on chosen style"""
    
    if style == "section":
        # Add all descriptions in a separate section at the end
        updated_markdown = markdown_text
        
        descriptions_section = "\n\n---\n\n## Image Descriptions\n\n"
        for i, img_data in enumerate(images, 1):
            descriptions_section += f"""
### Image {i} (UUID: `{img_data['uuid']}`)
{img_data['description']}

"""
        return updated_markdown + descriptions_section
    
    else:
        # Replace each image inline
        updated_markdown = markdown_text
        for img_data in images:
            new_markdown = format_image_with_description(img_data, style)
            updated_markdown = updated_markdown.replace(
                img_data['original_markdown'],
                new_markdown,
                1
            )
        return updated_markdown

# ============================================================================
# MAIN WORKFLOW
# ============================================================================

print("="*80)
print("DOCLING + OPENAI VISION: Extract and Describe Images")
print("="*80)
print(f"Model: {OPENAI_MODEL}")
print(f"Description Style: {DESCRIPTION_STYLE}")
print(f"Source: {PDF_SOURCE}")

# Step 1: Extract PDF
print("\n" + "="*80)
print("STEP 1: Extracting PDF with Docling")
print("="*80)

pipeline_options = PdfPipelineOptions()
pipeline_options.generate_picture_images = True
pipeline_options.images_scale = 2.0

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)

result = converter.convert(PDF_SOURCE)
markdown = result.document.export_to_markdown(image_mode=ImageRefMode.EMBEDDED)
print(f"✓ Extracted {len(markdown)} characters")

# Step 2: Extract images with UUIDs
print("\n" + "="*80)
print("STEP 2: Extracting Images and Assigning UUIDs")
print("="*80)

images = extract_base64_images(markdown)
print(f"✓ Found {len(images)} images")

for i, img in enumerate(images, 1):
    print(f"  Image {i}: UUID={img['uuid']}, Format={img['format']}, Base64 length={len(img['base64'])}")

# Step 3: Get descriptions from OpenAI
print("\n" + "="*80)
print("STEP 3: Getting Descriptions from OpenAI")
print("="*80)

for i, img_data in enumerate(images, 1):
    print(f"\n[{i}/{len(images)}] Processing image...")
    description = get_image_description(img_data['base64'], img_data['uuid'])
    img_data['description'] = description

# Step 4: Update markdown
print("\n" + "="*80)
print("STEP 4: Updating Markdown")
print("="*80)

final_markdown = update_markdown_with_descriptions(markdown, images, DESCRIPTION_STYLE)
print(f"✓ Updated markdown: {len(final_markdown)} characters")

# Step 5: Save files
print("\n" + "="*80)
print("STEP 5: Saving Files")
print("="*80)

# Save original
with open("output_original.md", "w", encoding="utf-8") as f:
    f.write(markdown)
print("✓ output_original.md")

# Save enhanced
with open("output_enhanced.md", "w", encoding="utf-8") as f:
    f.write(final_markdown)
print("✓ output_enhanced.md")

# Save UUID mappings as JSON
uuid_mapping = {
    img['uuid']: {
        'description': img['description'],
        'format': img['format'],
        'alt_text': img['alt_text'],
        'base64_length': len(img['base64'])
    }
    for img in images
}

with open("image_descriptions.json", "w", encoding="utf-8") as f:
    json.dump(uuid_mapping, f, indent=2)
print("✓ image_descriptions.json")

# Save base64 data separately (optional)
base64_data = {
    img['uuid']: img['base64']
    for img in images
}

with open("image_base64.json", "w", encoding="utf-8") as f:
    json.dump(base64_data, f, indent=2)
print("✓ image_base64.json")

# Display summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Total images: {len(images)}")
print(f"Original size: {len(markdown):,} chars")
print(f"Enhanced size: {len(final_markdown):,} chars")
print(f"Increase: +{len(final_markdown) - len(markdown):,} chars")

print("\n" + "="*80)
print("IMAGE DESCRIPTIONS")
print("="*80)
for i, img in enumerate(images, 1):
    print(f"\n[{i}] UUID: {img['uuid']}")
    print(f"    Description: {img['description']}")

print("\n" + "="*80)
print("DONE!")
print("="*80)
print("\nTo customize:")
print("  1. Change DESCRIPTION_STYLE at top of file")
print("  2. Change DESCRIPTION_PROMPT for different descriptions")
print("  3. Change OPENAI_MODEL for different quality/cost tradeoff")