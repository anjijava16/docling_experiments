
```
PDF
 ↓
Docling + EasyOCR
 ↓
Claude 3 Vision (Bedrock)
 ↓
Claude 3 Text
 ↓
Titan Embeddings
 ↓
ChromaDB

```



```
Images → Claude Vision
Tables → Claude Text
Text → Titan Embeddings
Vectors → ChromaDB
Search → Semantic Retrieval

```



```
PDF
 ↓
Extract:
  • Text
  • Images
  • Tables
 ↓
Claude 3 Vision → image descriptions
Claude 3 Text → table summaries
 ↓
Chunk text
 ↓
Titan Embeddings
 ↓
ChromaDB
 ↓
Semantic Search
```