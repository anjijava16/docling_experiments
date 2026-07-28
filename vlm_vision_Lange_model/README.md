PDF

↓

Convert PDF pages

↓

PP-DocLayoutV3

↓

Detect Regions

↓

Crop Regions

↓

Qwen3.5-4B

↓

Recognize Text

↓

Formatter

↓

Markdown / JSON



This configuration file gives us a very good picture of the GLM-OCR architecture. Let's go from **zero to hero**.

## 1. What is a Vision Language Model (VLM)?

A **Vision Language Model (VLM)** is an AI model that understands **both images and text**.

Traditional LLM:

```text
Input:
"What is Python?"

↓

LLM

↓

"It is a programming language."
```

A VLM can do this:

```text
Image + Text Prompt

↓

Vision Encoder

↓

LLM

↓

Text Response
```

Example:

```
+---------------------+
| Invoice             |
| ABC Company         |
| Total : $2,500      |
+---------------------+
```

Prompt:

```
Extract this invoice.
```

Output:

```json
{
  "vendor":"ABC Company",
  "total":"$2500"
}
```

The model is not just reading letters—it is understanding the document.

---

# 2. What VLM is GLM-OCR using?

From your configuration:

```yaml
ocr_api:
    model: Qwen/Qwen3.5-4B
```



This tells us that **GLM-OCR itself is not the OCR model**.

Instead, it sends requests to a self-hosted **Qwen 3.5 4B Vision Language Model** through an OpenAI-compatible API.

Architecture:

```text
                 GLM-OCR SDK
                      │
                      ▼
          Build Prompt + Images
                      │
                      ▼
       OpenAI Compatible HTTP API
                      │
                      ▼
          vLLM / SGLang Server
                      │
                      ▼
             Qwen3.5-4B VLM
                      │
                      ▼
              OCR Response
```

So **GlmOcr is the orchestrator**, while **Qwen3.5-4B is the AI model doing the recognition**.

---

# 3. Why is there a separate Layout Model?

Your config also shows:

```yaml
layout:
    model_dir:
       PP-DocLayoutV3
```



So the pipeline actually uses **two AI models**.

### Model 1

```
PP-DocLayoutV3

↓

Detect Regions
```

Example:

```
Invoice

+----------------+

Title

Paragraph

Table

Image

Footer

+----------------+
```

It detects

* Text
* Table
* Figure
* Header
* Footer
* Formula

---

### Model 2

Each detected region is sent to

```
Qwen3.5-4B
```

which recognizes the contents.

```
Detected Table

↓

Qwen

↓

Markdown Table
```

---

# 4. Entire GLM-OCR Pipeline

```text
PDF

↓

Convert PDF pages

↓

PP-DocLayoutV3

↓

Detect Regions

↓

Crop Regions

↓

Qwen3.5-4B

↓

Recognize Text

↓

Formatter

↓

Markdown / JSON
```

Notice that layout detection and OCR are separate stages.

---

# 5. Why use a VLM instead of Tesseract?

### Traditional OCR

```
Invoice

↓

Read Characters

↓

Text
```

Output:

```
Invoice

ABC Company

Laptop

2000

Total
```

It doesn't understand relationships.

---

### VLM

```
Invoice Image

↓

Vision Transformer

↓

LLM

↓

Reasoning

↓

Structured Output
```

Output:

```json
{
  "Invoice Number":"INV-100",
  "Vendor":"ABC Company",
  "Items":[...],
  "Total":"$2000"
}
```

The VLM understands the document semantically.

---

# 6. Why are there prompts in the config?

Your config contains:

```yaml
task_prompt_mapping:

text:

table:

formula:

image_desc:
```



This is a key difference from classic OCR.

Instead of simply saying "read text," GLM-OCR **asks the VLM different questions** depending on the detected region.

For a text block:

```
OCR and recognize the text...
```

For a table:

```
Convert this table into Markdown.
```

For a formula:

```
Convert to LaTeX.
```

For a chart:

```
Describe the image.
```

This is why VLMs are much more flexible than traditional OCR engines.

---

# 7. Where does vLLM fit?

Your configuration mentions:

```
Self-hosted vLLM/SGLang
```



vLLM is **not the model**.

Think of it as a high-performance inference server.

```
GPU

↓

Qwen Model

↓

vLLM

↓

HTTP API

↓

GLM-OCR SDK
```

The SDK sends HTTP requests, and vLLM efficiently batches and serves them on the GPU.

---

# 8. What is the 4B?

```
Qwen3.5-4B
```

means approximately **4 billion parameters**.

Approximate comparison:

| Model              |                           Parameters | Typical Use                |
| ------------------ | -----------------------------------: | -------------------------- |
| BERT               |                                 110M | NLP                        |
| Llama 3 8B         |                                   8B | General LLM                |
| Qwen3.5-4B         |                                   4B | Smaller, efficient LLM/VLM |
| GPT-4-class models | Much larger (exact size undisclosed) | Advanced reasoning         |

Larger models generally have stronger reasoning capabilities but require more GPU memory and compute.

---

# 9. End-to-End Flow

Putting it all together:

```text
                PDF
                 │
                 ▼
      Render PDF Pages
                 │
                 ▼
      PP-DocLayoutV3
      (Layout Detection)
                 │
        ┌────────┼─────────┐
        ▼        ▼         ▼
      Text     Table     Formula
        │         │          │
        ▼         ▼          ▼
     Prompt    Prompt     Prompt
        │         │          │
        └─────────┼──────────┘
                  ▼
         vLLM / SGLang Server
                  │
                  ▼
          Qwen3.5-4B VLM
                  │
                  ▼
       OCR + Semantic Understanding
                  │
                  ▼
      Formatter (Markdown / JSON)
                  │
                  ▼
          Final Structured Output
```

### Key takeaway

The uploaded configuration shows that **GLM-OCR is an orchestration framework**, not a single OCR model. It combines:

* **PP-DocLayoutV3** for document layout detection and region segmentation.
* **Qwen3.5-4B Vision Language Model** as the OCR and understanding engine, served through **vLLM or SGLang** using an OpenAI-compatible API.
* A formatter that merges the recognized regions into Markdown or JSON output.  

This modular design lets you swap or upgrade the VLM (for example, a newer Qwen vision model) while keeping the rest of the GLM-OCR pipeline largely unchanged.
