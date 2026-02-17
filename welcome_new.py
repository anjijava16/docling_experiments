"""
COPY-PASTE SOLUTION - Just replace your welcome_new.py with this entire file
This is the complete, working code with base64 image extraction.
"""

from docling.document_converter import DocumentConverter
from docling_core.types.doc import ImageRefMode
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption

# Configure pipeline to extract images (THIS IS THE KEY!)
pipeline_options = PdfPipelineOptions()
pipeline_options.generate_picture_images = True  # Extract images from PDF
pipeline_options.images_scale = 2.0               # Higher quality (optional)

# Create converter with pipeline options
converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)

# Convert PDF
result = converter.convert("https://arxiv.org/pdf/2206.01062")

# Export to markdown with embedded base64 images
markdown = result.document.export_to_markdown(
    image_mode=ImageRefMode.EMBEDDED
)

# Save to file
with open("output.md", "w", encoding="utf-8") as f:
    f.write(markdown)

# Display results
print(f"✓ Markdown with base64 images saved to output.md")
print(f"  Total length: {len(markdown)} characters")

if "data:image" in markdown:
    count = markdown.count("data:image")
    print(f"  ✓ Found {count} embedded base64 image(s)!")
else:
    print(f"  ✗ No embedded images found")