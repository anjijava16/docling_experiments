from docling.document_converter import DocumentConverter

source = "https://arxiv.org/pdf/2408.09869"  # document per local path or URL
converter = DocumentConverter()
result = converter.convert(source)
print(result.document.export_to_markdown()) 
for i, picture in enumerate(result.document.pictures):
        print(f"Picture {i}:")
        print(f"  URL: {picture.url}")
        print(f"  Caption: {picture.caption}")
    # Get the image as PIL Image
    # image = picture.get_image() 
    # print(image) 