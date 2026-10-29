"""Keep usable PDF text; OCR pages with sparse or corrupt text layers."""
import re
from io import BytesIO

def usable_text(text):
    text=text.strip()
    if len(text)<30:return False
    nonspace=[c for c in text if not c.isspace()]
    meaningful=sum(c.isalnum() for c in nonspace)/max(len(nonspace),1)
    words=re.findall(r'[^\W\d_]{2,}',text,flags=re.UNICODE)
    replacements=text.count('\ufffd')/max(len(text),1)
    return meaningful>=0.35 and len(words)>=3 and replacements<0.03

def extract_pdf(path,force_ocr=False):
    import pymupdf
    import pytesseract
    from PIL import Image
    pages=[]
    with pymupdf.open(path) as pdf:
        for i in range(min(len(pdf),30)):
            page=pdf[i];text=page.get_text()
            if force_ocr or not usable_text(text):
                # Cap rendered image size while retaining 300 dpi for normal paperwork.
                scale=min(300/72,(40_000_000/max(page.rect.width*page.rect.height,1))**0.5)
                pix=page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False,colorspace=pymupdf.csRGB)
                with Image.open(BytesIO(pix.tobytes('png'))) as image:
                    text=pytesseract.image_to_string(image,timeout=120)
            pages.append(text)
        if len(pdf)>30:pages.append('[Only first 30 pages extracted. Review original for remaining pages.]')
    return '\n'.join(pages)[:250000]
