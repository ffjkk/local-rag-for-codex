"""Safe display formats: Markdown, formatted JSON and CSV/TSV tables."""
import csv,html,io,json
from pathlib import Path
from markdown_it import MarkdownIt
import bleach

def render(name,text):
    ext=Path(name).suffix.lower()
    if ext in ('.md','.markdown','.mdown'):
        parser=MarkdownIt('commonmark',{'html':False}).enable('table').enable('strikethrough').disable('image')
        result=parser.render(text)
        clean=bleach.clean(result,tags=['p','br','hr','h1','h2','h3','h4','h5','h6','strong','em','s','blockquote','ul','ol','li','pre','code','a','table','thead','tbody','tr','th','td'],attributes={'a':['href','title'],'ol':['start']},protocols=['https','http','mailto'],strip=True)
        return {'format':'Markdown','html':clean}
    if ext=='.json':
        try: formatted=json.dumps(json.loads(text),ensure_ascii=False,indent=2)
        except (ValueError,RecursionError) as exc: raise ValueError('JSON 格式无效，请查看源码并修正') from exc
        return {'format':'JSON','html':'<pre><code>'+html.escape(formatted)+'</code></pre>'}
    if ext in ('.csv','.tsv'):
        rows=[]
        for i,row in enumerate(csv.reader(io.StringIO(text),delimiter='\t' if ext=='.tsv' else ',')):
            if i>=500: break
            tag='th' if i==0 else 'td'
            rows.append('<tr>'+''.join(f'<{tag}>'+html.escape(v)+f'</{tag}>' for v in row)+'</tr>')
        return {'format':'表格（最多显示 500 行）','html':'<table>'+''.join(rows)+'</table>'}
    raise ValueError('此文件使用源码预览；渲染支持 Markdown、JSON、CSV 和 TSV')
