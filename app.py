import knowledge as kb
import contextlib, json, threading, uuid, concurrent.futures
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from parsers import parse

kb.init()
app=FastAPI(title='本地知识库',docs_url=None,redoc_url=None,openapi_url=None)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','testserver'])
POOL=concurrent.futures.ThreadPoolExecutor(max_workers=1,thread_name_prefix='rag-import')
JOBS={}; JOB_LOCK=threading.Lock()
MAX_FILE=50*1024*1024
MAX_BATCH=300*1024*1024

@app.middleware('http')
async def protect(request:Request,call_next):
    origin=request.headers.get('origin')
    if origin and origin not in ('http://127.0.0.1:8765','http://localhost:8765','http://testserver'):
        return JSONResponse({'detail':'不允许跨站访问本地知识库'},status_code=403)
    if request.method in ('POST','PUT','DELETE','PATCH') and request.headers.get('x-rag-ui')!='1':
        return JSONResponse({'detail':'缺少本地管理请求标识'},status_code=403)
    if int(request.headers.get('content-length','0'))>MAX_BATCH+2*1024*1024:
        return JSONResponse({'detail':'单批上传不超过 300 MB'},status_code=413)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Content-Security-Policy']="default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
    response.headers['Cache-Control']='no-store'
    return response

@app.exception_handler(ValueError)
async def invalid(request,exc): return JSONResponse({'detail':str(exc)},status_code=400)
@app.exception_handler(KeyError)
async def missing(request,exc): return JSONResponse({'detail':str(exc)},status_code=404)

@app.get('/')
def home(): return FileResponse(kb.ROOT/'web'/'index.html',media_type='text/html')
app.mount('/static',StaticFiles(directory=kb.ROOT/'web'),name='static')

@app.get('/api/status')
def status(): return kb.status()
@app.get('/api/list')
def listing(folder:str='',q:str=''): return kb.listing(folder,q)
class Folder(BaseModel): path:str=Field(max_length=1000)
@app.post('/api/folders')
def folder_create(body:Folder): return kb.create_folder(body.path)
@app.delete('/api/folders')
def folder_delete(path:str,recursive:bool=False): return kb.delete_folder(path,recursive)
@app.get('/api/documents/{doc_id}')
def document(doc_id:str): return kb.get_document(doc_id)
class Edit(BaseModel): content:str=Field(max_length=kb.MAX_TEXT); version:int
@app.put('/api/documents/{doc_id}')
def edit(doc_id:str,body:Edit): return kb.update_document(doc_id,body.content,body.version)
@app.delete('/api/documents/{doc_id}')
def delete(doc_id:str): return kb.delete_document(doc_id)
class MoveDocument(BaseModel):
    target_folder:str=Field(max_length=1000)
    version:int
@app.post('/api/documents/{doc_id}/move')
def move_document(doc_id:str,body:MoveDocument):
    return kb.move_document(doc_id,body.target_folder,body.version)
class MoveFolder(BaseModel):
    source:str=Field(max_length=1000)
    target_parent:str=Field(max_length=1000)
@app.post('/api/folders/move')
def move_folder(body:MoveFolder):
    return kb.move_folder(body.source,body.target_parent)
@app.get('/api/documents/{doc_id}/render')
def render_document(doc_id:str):
    from rendering import render
    doc=kb.get_document(doc_id)
    return {'id':doc_id,'version':doc['version'],**render(doc['name'],doc['content'])}

@app.get('/api/documents/{doc_id}/original')
def original(doc_id:str):
    with kb.connect() as c: row=c.execute('SELECT name,original FROM documents WHERE id=?',(doc_id,)).fetchone()
    if not row: raise KeyError('文档不存在')
    from urllib.parse import quote
    return Response(row['original'],media_type='application/octet-stream',headers={'Content-Disposition':"attachment; filename*=UTF-8''"+quote(row['name'])})
class Search(BaseModel): query:str=Field(min_length=1,max_length=2000); scope:str='auto'; category:str=''; top_k:int=Field(default=5,ge=1,le=20)
@app.post('/api/search')
def search(body:Search): return kb.search(**body.model_dump())

def run_import(job_id,items):
    for item in items:
        try:
            raw=item['temp'].read_bytes()
            text,warning=parse(item['name'],raw)
            result=kb.import_document(item['folder'],item['name'],raw,text,warning)
            event={'path':item['relative'],'status':'success',**result}
        except Exception as exc: event={'path':item['relative'],'status':'error','error':str(exc)[:600]}
        finally: item['temp'].unlink(missing_ok=True)
        with JOB_LOCK:
            JOBS[job_id]['items'].append(event); JOBS[job_id]['completed']+=1
    with JOB_LOCK: JOBS[job_id]['state']='done'

@app.post('/api/upload')
async def upload(files:list[UploadFile]=File(...),paths:str=Form(...),folder:str=Form('')):
    base=kb.path_name(folder)
    try: names=json.loads(paths)
    except json.JSONDecodeError as exc: raise ValueError('文件目录信息无效') from exc
    if not isinstance(names,list) or len(names)!=len(files) or not 1<=len(files)<=2000: raise ValueError('每批上传 1–2000 个文件，目录信息须一致')
    items=[]; total=0
    try:
        # Validate every relative path before storing any part.
        safe=[kb.path_name(x,False) for x in names]
        for f,rel in zip(files,safe):
            components=rel.split('/'); target='/'.join(x for x in [base,'/'.join(components[:-1])] if x)
            kb.path_name(target)
            tmp=kb.ROOT/'tmp'/('upload-'+uuid.uuid4().hex)
            items.append({'temp':tmp,'name':components[-1],'folder':target,'relative':rel})
            size=0
            with tmp.open('wb') as stream:
                while block:=await f.read(1024*1024):
                    size+=len(block); total+=len(block)
                    if size>MAX_FILE or total>MAX_BATCH: raise ValueError('单文件不超过 50 MB，每批不超过 300 MB')
                    stream.write(block)
        job_id=uuid.uuid4().hex
        with JOB_LOCK:
            if len(JOBS)>100:
                for old in list(JOBS):
                    if JOBS[old]['state']=='done': del JOBS[old]
                    if len(JOBS)<=80: break
            if sum(j['state']!='done' for j in JOBS.values())>=10: raise ValueError('上传队列已满，请等待已有任务完成')
            JOBS[job_id]={'id':job_id,'state':'processing','total':len(items),'completed':0,'items':[]}
        POOL.submit(run_import,job_id,items)
        return {'job_id':job_id}
    except Exception:
        for item in items: item['temp'].unlink(missing_ok=True)
        raise
    finally:
        for f in files: await f.close()

@app.get('/api/jobs/{job_id}')
def job(job_id:str):
    with JOB_LOCK:
        if job_id not in JOBS: raise KeyError('上传任务不存在或服务已重启')
        return json.loads(json.dumps(JOBS[job_id]))

if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8765,access_log=False)
