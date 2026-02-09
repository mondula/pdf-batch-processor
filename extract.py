import pdfplumber
import json

def extract_pdf_content(pdf_path):
    """
    Extracts text and tables from a given PDF file.

    :param pdf_path: Path to the PDF file.
    :return: A dictionary containing extracted text and tables.
    """
    extracted_data = {"text": "", "tables": []}

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                extracted_data["text"] += text + "\n"

            tables = page.extract_tables()
            for table in tables:
                extracted_data["tables"].append(table)

    return extracted_data

if __name__ == "__main__":
    sample_pdf = "data/sample.pdf"
    extracted = extract_pdf_content(sample_pdf)
    print(json.dumps(extracted, indent=2))
