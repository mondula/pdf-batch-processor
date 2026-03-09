# PDF Batch Variant Extraction

A desktop tool to extract structured product variant data from technical PDF datasheets and export clean CSV files using AI.

The tool reads PDF tables, detects product variants (e.g. DN sizes), normalizes fields, and generates one row per variant. Designed for batch processing many manufacturers and datasheets.

---

## Features

- Batch process multiple PDFs
- Manufacturer-based GUI workflow
- Automatic table and text extraction
- AI-powered normalization
- Stable CSV schema across runs
- Per-PDF, per-manufacturer, and global exports
- Includes source PDF path for traceability

---

## Quick Setup 

### macOS / Linux

```bash
git clone https://github.com/mondula/pdf-batch-processor.git && \
cd pdf-batch-processor && \
python -m venv venv && \
source venv/bin/activate && \
pip install -r requirements.txt && \
echo 'OPENAI_API_KEY="your-key-here"' > .env && \
python smart_batch_processor_gui_variants.py
