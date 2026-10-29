import tempfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import pymupdf
from ocr_reader import usable_text,extract_pdf
assert not usable_text("$..7..'....8...............*....\n"+'.'*2000)
assert usable_text('Insurance Policy 12345. This document has readable native text.')
with tempfile.TemporaryDirectory() as tmp:
 image=Image.new('RGB',(1400,300),'white')
 ImageDraw.Draw(image).text((30,90),'HEALTH CARE SUMMARY BALANCE 76.84',font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',42),fill='black')
 imagepath=Path(tmp)/'sample.png';image.save(imagepath)
 p=Path(tmp)/'mixed.pdf'
 with pymupdf.open() as pdf:
  page=pdf.new_page();page.insert_text((40,40),'Insurance Policy 12345. Readable native text is retained.')
  page=pdf.new_page(width=700,height=220);page.insert_image(pymupdf.Rect(0,30,700,180),filename=str(imagepath));page.insert_text((20,20),'$..7..'*100)
  pdf.save(p)
 text=extract_pdf(p)
 assert '12345' in text and '76.84' in text,text
 print('PASS: readable native text retained; long corrupt text triggers OCR; both pages extracted.')
