from pypdf import PdfReader


def read_pdf(pdf_path):
    with open(pdf_path, "rb") as file:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()  
    return text


content = read_pdf(pdf_path=r"C:\Users\1657820\Documents\Downloads\1\20251021\1.pdf")

print(content)

with open('example.txt', 'w', encoding="utf-8") as file:
    file.write(content)
