"""App B: produce mediciones de humedad, sin comunicación con la plataforma."""
import asyncio, os, random, time
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI
COLLECTOR_URL=os.environ.get('COLLECTOR_URL','http://collector00:8080')
INTERVAL=float(os.environ.get('INTERVAL_SECONDS','3'))
started=time.monotonic()
sent=0
last_http_status=None
async def emit_loop():
    global sent,last_http_status
    await asyncio.sleep(3)
    while True:
        try:
            async with httpx.AsyncClient(timeout=3,trust_env=False) as client:
                r=await client.post(COLLECTOR_URL+'/reading',json={'humidity':round(random.uniform(35,65),2),'origin':'environment-app-b'})
                last_http_status=r.status_code
                if r.is_success: sent+=1
        except httpx.HTTPError: last_http_status=0
        await asyncio.sleep(INTERVAL)
@asynccontextmanager
async def lifespan(app):
    task=asyncio.create_task(emit_loop())
    try: yield
    finally:
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass
from qos_faults import FaultProfile
fault_profile = FaultProfile()
app=FastAPI(lifespan=lifespan)
@app.get('/health')
def health(): return {'status':'ok'}
@app.get('/metrics')
def metrics():return fault_profile.decorate({'response_time_ms':20,'execution_time':5,'availability':24,'reliability':0.01,'cost':0.1,'status':'ok'})


@app.post('/admin/simulate')
def inject_qos_fault(payload: dict):
    """Modifica TEMPORALMENTE métricas expuestas por este contenedor real."""
    from fastapi import HTTPException
    try:
        return fault_profile.inject(payload)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
