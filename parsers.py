"""Offline upload parsers. No uploaded content is sent to external services."""
import io, zipfile, unicodedata
from pathlib import Path
from knowledge import MAX_TEXT
# PDF/Word have dedicated parsers; every other extension is inspected as text.
BINARY_SIGNATURES=(b'MZ',b'\x7fELF',b'PK\x03\x04',b'PK\x05\x06',b'\x89PNG',b'\xff\xd8\xff',b'GIF87a',b'GIF89a',b'\x1f\x8b',b'7z\xbc\xaf\x27\x1c',b'Rar!',b'SQLite format 3\x00',b'\x00asm',b'\xd0\xcf\x11\xe0',b'RIFF')
_ocr=None

def decode(raw):
    if raw.startswith(BINARY_SIGNATURES):
        raise ValueError('检测到二进制文件，不能作为纯文本入库；旧版 Word 请另存为 DOCX')
    if raw.startswith((b'\xff\xfe\x00\x00',b'\x00\x00\xfe\xff')):
        encodings=['utf-32']
    elif raw.startswith((b'\xff\xfe',b'\xfe\xff')):
        encodings=['utf-16']
    else:
        encodings=['utf-8-sig','gb18030']
    for encoding in encodings:
        try:
            text=raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        if any(unicodedata.category(c)=='Cc' and c not in '\t\n\r\f' for c in text):
            raise ValueError('检测到二进制数据或不可读控制字符，请转换为正常文本后上传')
        return text
    raise ValueError('无法识别文本编码，请保存为 UTF-8 后重试')


def parse(name,raw):
    ext=Path(name).suffix.lower()
    warning=''
    if ext not in ('.pdf','.docx','.docs'): text=decode(raw)
    elif ext in ('.docx','.docs'):
        from docx import Document
        from docx.table import Table
        from docx.text.paragraph import Paragraph
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                if sum(x.file_size for x in z.infolist())>100*1024*1024: raise ValueError('Word 解压后体积过大')
            doc=Document(io.BytesIO(raw))
        except (zipfile.BadZipFile,KeyError) as e: raise ValueError('该文件不是有效 DOCX；请用 Word 另存为 .docx') from e
        lines=[]
        def visit(container):
            for block in container.iter_inner_content():
                if isinstance(block,Paragraph): lines.append(block.text)
                elif isinstance(block,Table):
                    for row in block.rows: lines.append(' | '.join(cell.text.replace('\n',' / ') for cell in row.cells))
        visit(doc)
        text='\n'.join(lines)
        warning='已提取正文与表格；图片、批注、页眉页脚不参与检索。'
    else:
        from pypdf import PdfReader
        reader=PdfReader(io.BytesIO(raw))
        if reader.is_encrypted and not reader.decrypt(''): raise ValueError('PDF 已加密，请解密后上传')
        if len(reader.pages)>500: raise ValueError('PDF 超过 500 页，请拆分后上传')
        pages=[]; scanned=[]; rendered=None
        try:
            for i,page in enumerate(reader.pages):
                value=page.extract_text() or ''
                if len(value.strip())<15:
                    import pypdfium2 as pdfium
                    import numpy as np
                    global _ocr
                    if _ocr is None:
                        from rapidocr_onnxruntime import RapidOCR
                        _ocr=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=2)
                    if rendered is None: rendered=pdfium.PdfDocument(raw)
                    p=rendered[i]; bitmap=None
                    try:
                        w,h=p.get_size(); scale=min(2.0,2400/max(w,h))
                        bitmap=p.render(scale=scale)
                        result,_=_ocr(np.array(bitmap.to_pil()))
                        value='\n'.join(item[1] for item in result) if result else value
                        scanned.append(i+1)
                    finally:
                        if bitmap is not None: bitmap.close()
                        p.close()
                pages.append(f'## 第 {i+1} 页\n\n'+value)
                if sum(map(len,pages))>MAX_TEXT: raise ValueError('PDF 文本过大，请拆分后上传')
        finally:
            if rendered is not None: rendered.close()
        if not any(len(p.split('\n\n',1)[-1].strip()) for p in pages): raise ValueError('PDF 文本提取和 OCR 均未识别到文字')
        text='\n\n'.join(pages)
        if scanned: warning='第 '+', '.join(map(str,scanned))+' 页使用本地 OCR，请检查识别结果。'
    if len(text)>MAX_TEXT: raise ValueError('解析文本超过 200 万字符，请拆分上传')
    if not text.strip(): raise ValueError('文件中没有可索引的文字')
    return text,warning
