from io import BytesIO
from docling.datamodel.base_models import DocumentStream
from docling.document_converter import DocumentConverter

with open("welcome_dummy.pdf", "rb") as f:
    buf = BytesIO(f.read())

source = DocumentStream(name="welcome_dummy.pdf", stream=buf)
converter = DocumentConverter()
result = converter.convert(source)
markdown = result.document.export_to_markdown()
print(markdown)
