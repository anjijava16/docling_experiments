# EasyOCR Quick Reference

## 🚀 Quick Start

### Installation
```bash
pip install easyocr
```

**First run downloads models (~500MB)**

### Basic Usage
```python
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions

# Configure EasyOCR
easyocr_options = EasyOcrOptions(
    lang=['en'],  # Languages
    use_gpu=False  # True if you have CUDA GPU
)

pipeline_options = PdfPipelineOptions()
pipeline_options.ocr_options = easyocr_options  # Set EasyOCR
```

## 🌍 Language Configurations

### English Only
```python
easyocr_options = EasyOcrOptions(lang=['en'])
```

### Multi-Language (Asian)
```python
# English + Chinese (Simplified)
easyocr_options = EasyOcrOptions(lang=['en', 'ch_sim'])

# English + Japanese
easyocr_options = EasyOcrOptions(lang=['en', 'ja'])

# English + Korean
easyocr_options = EasyOcrOptions(lang=['en', 'ko'])

# All three
easyocr_options = EasyOcrOptions(lang=['en', 'ch_sim', 'ja', 'ko'])
```

### European Languages
```python
# English + French + German + Spanish
easyocr_options = EasyOcrOptions(lang=['en', 'fr', 'de', 'es'])
```

### Middle Eastern Languages
```python
# English + Arabic
easyocr_options = EasyOcrOptions(lang=['en', 'ar'])

# English + Persian
easyocr_options = EasyOcrOptions(lang=['en', 'fa'])

# English + Hebrew
easyocr_options = EasyOcrOptions(lang=['en', 'he'])
```

### South Asian Languages
```python
# English + Hindi
easyocr_options = EasyOcrOptions(lang=['en', 'hi'])

# English + Bengali
easyocr_options = EasyOcrOptions(lang=['en', 'bn'])

# English + Tamil
easyocr_options = EasyOcrOptions(lang=['en', 'ta'])
```

## 🎯 Common Use Cases

### Case 1: Chinese Business Documents
```python
EASYOCR_LANGUAGES = ['en', 'ch_sim']  # Simplified Chinese
# or
EASYOCR_LANGUAGES = ['en', 'ch_tra']  # Traditional Chinese
```

### Case 2: Japanese Academic Papers
```python
EASYOCR_LANGUAGES = ['en', 'ja']
```

### Case 3: Korean Government Forms
```python
EASYOCR_LANGUAGES = ['en', 'ko']
```

### Case 4: European Multi-Language
```python
EASYOCR_LANGUAGES = ['en', 'fr', 'de', 'es', 'it']
```

### Case 5: Arabic Medical Records
```python
EASYOCR_LANGUAGES = ['en', 'ar']
```

## 💻 GPU vs CPU

### CPU (Default)
```python
easyocr_options = EasyOcrOptions(
    lang=['en'],
    use_gpu=False  # Uses CPU
)
```
- ⏱️ Slower (10-30 minutes for 100 pages)
- 💰 Cheaper infrastructure
- 🔋 Lower power usage

### GPU (Recommended for production)
```python
easyocr_options = EasyOcrOptions(
    lang=['en'],
    use_gpu=True  # Uses CUDA GPU
)
```
- ⏱️ Faster (2-5 minutes for 100 pages)
- 💰 Higher infrastructure cost
- 🚀 Better for high volume

## 📊 Performance Expectations

### CPU Processing
```
10-page PDF:     ~2-5 minutes
50-page PDF:     ~10-20 minutes
100-page PDF:    ~20-40 minutes
```

### GPU Processing
```
10-page PDF:     ~30-60 seconds
50-page PDF:     ~2-4 minutes
100-page PDF:    ~4-8 minutes
```

## 🔧 Complete Configuration Examples

### Example 1: English Documents (Fast)
```python
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat

easyocr_options = EasyOcrOptions(
    lang=['en'],
    use_gpu=False
)

pipeline_options = PdfPipelineOptions()
pipeline_options.ocr_options = easyocr_options
pipeline_options.generate_picture_images = True

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)

result = converter.convert("document.pdf")
```

### Example 2: Chinese + English (Business)
```python
easyocr_options = EasyOcrOptions(
    lang=['en', 'ch_sim'],  # Simplified Chinese
    use_gpu=True  # Use GPU for speed
)

pipeline_options = PdfPipelineOptions()
pipeline_options.ocr_options = easyocr_options
pipeline_options.generate_picture_images = True
pipeline_options.images_scale = 2.0

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)

result = converter.convert("business_doc.pdf")
```

### Example 3: Multi-Language Reports
```python
easyocr_options = EasyOcrOptions(
    lang=['en', 'fr', 'de', 'es'],  # European languages
    use_gpu=False
)

pipeline_options = PdfPipelineOptions()
pipeline_options.ocr_options = easyocr_options
pipeline_options.generate_picture_images = True

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)

result = converter.convert("report.pdf")
```

## 🌐 Supported Languages

### Most Common
```
'en'      - English
'ch_sim'  - Chinese (Simplified)
'ch_tra'  - Chinese (Traditional)
'ja'      - Japanese
'ko'      - Korean
'ar'      - Arabic
'fr'      - French
'de'      - German
'es'      - Spanish
'it'      - Italian
'pt'      - Portuguese
'ru'      - Russian
'hi'      - Hindi
'th'      - Thai
'vi'      - Vietnamese
```

### Full List (80+ languages supported)
See: https://www.jaided.ai/easyocr/

## 💰 Cost Comparison

### Infrastructure Costs
```
CPU Server:
- AWS/GCP: ~$50-100/month
- Processing: Slow but cheap

GPU Server:
- AWS/GCP: ~$200-500/month
- Processing: Fast but expensive

Rule of thumb:
- < 1000 pages/day: Use CPU
- > 1000 pages/day: Use GPU (faster = cheaper per page)
```

## 🎯 When to Use Default vs EasyOCR

### Use DEFAULT when:
```
✅ Born-digital PDFs
✅ Clean typed text
✅ High quality scans
✅ English only
✅ Speed is critical
```

### Use EASYOCR when:
```
✅ Scanned documents
✅ Handwritten text
✅ Poor quality images
✅ Non-English languages
✅ Multi-language documents
✅ Complex backgrounds
```

## 🐛 Troubleshooting

### "CUDA not found" Error
```python
# Set to False if no GPU
easyocr_options = EasyOcrOptions(
    lang=['en'],
    use_gpu=False  # Use CPU instead
)
```

### Slow Processing
```
Problem: Taking too long
Solutions:
1. Reduce image scale:
   pipeline_options.images_scale = 1.0  # Lower quality, faster
   
2. Use GPU:
   use_gpu=True
   
3. Process fewer languages:
   lang=['en']  # Instead of ['en', 'ch_sim', 'ja', 'ko']
```

### Poor Accuracy
```
Problem: Text not recognized well
Solutions:
1. Increase image scale:
   pipeline_options.images_scale = 3.0  # Higher quality
   
2. Add more languages:
   lang=['en', 'ch_sim']  # If document is multi-language
   
3. Check if correct language specified
```

### Memory Issues
```
Problem: Out of memory
Solutions:
1. Process in smaller batches
2. Use CPU instead of GPU
3. Reduce images_scale to 1.0
4. Add more RAM to server
```

## 📝 Quick Test Script

```python
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
from docling.document_converter import PdfFormatOption
from docling.datamodel.base_models import InputFormat

# Configure EasyOCR
easyocr_options = EasyOcrOptions(
    lang=['en'],  # Change as needed
    use_gpu=False
)

pipeline_options = PdfPipelineOptions()
pipeline_options.ocr_options = easyocr_options
pipeline_options.generate_picture_images = True

# Create converter
converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)

# Test
print("Testing EasyOCR...")
result = converter.convert("test.pdf")
markdown = result.document.export_to_markdown()

print(f"✓ Extracted {len(markdown)} characters")
print("\nFirst 500 characters:")
print(markdown[:500])
```

## 🚀 Integration with ChromaDB Script

Just change the configuration at the top:

```python
# In pdf_chromadb_easyocr.py
OPENAI_API_KEY = "your-key"
EASYOCR_LANGUAGES = ['en', 'ch_sim']  # Customize
USE_GPU = True  # If available

# Then run normally
ingest_pdf("document.pdf")
```

## 📚 More Info

- **EasyOCR Docs:** https://www.jaided.ai/easyocr/
- **Docling Docs:** https://docling-project.github.io/docling/
- **Language Codes:** https://www.jaided.ai/easyocr/
