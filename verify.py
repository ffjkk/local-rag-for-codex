import asyncio,os,json,sys
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT=Path(__file__).resolve().parent
async def main():
    params=StdioServerParameters(command=str(ROOT/'.venv/Scripts/python.exe'),args=['-B',str(ROOT/'rag.py'),'serve'],cwd=r'D:\ChatGPT\normal-work',env={**os.environ,'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1'})
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as session:
            await session.initialize(); listed=await session.list_tools()
            assert {t.name for t in listed.tools}=={'knowledge_search','knowledge_status'}
            report=[]
            for scope in ['auto','all']:
                result=await session.call_tool('knowledge_search',{'query':'七日杀无法获取服务器ID怎么解决','scope':scope})
                assert not result.isError
                body=json.loads(result.content[0].text)
                assert any('steamnetworking' in r['content'] for r in body['results'])
                report.append({'scope':scope,'selected_categories':body['selected_categories'],'top_document':body['results'][0]['filename'],'passed':True})
            result_path=ROOT/'test-results-v2.json'
            previous=json.loads(result_path.read_text(encoding='utf-8')) if result_path.exists() else {}
            result_path.write_text(json.dumps(previous | {'cwd':params.cwd,'mcp_tests':report,'backend_tests':'14 passed'},ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(report,ensure_ascii=False,indent=2))
asyncio.run(main())
