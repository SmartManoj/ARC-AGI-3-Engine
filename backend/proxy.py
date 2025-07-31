from fastapi import FastAPI, Request, Response
import httpx

app = FastAPI()

# allow cors
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3194"],  # or ["*"] for all origins
    allow_methods=["*"],
    allow_headers=["x-api-key", "Authorization", "Content-Type", "*"],  # include your custom headers here
)

TARGET_URL = 'https://three.arcprize.org'

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy(path: str, request: Request):
    url = f"{TARGET_URL}/{path}"
    headers = {'x-api-key': request.headers.get('x-api-key')}
    async with httpx.AsyncClient() as client:
        req = client.build_request(
            method=request.method,
            url=f"{TARGET_URL}/{path}",
            headers=headers,
            content=await request.body(),
        )
        resp = await client.send(req, stream=True)
        return Response(
            content=await resp.aread(),
            status_code=resp.status_code,
            headers=resp.headers,
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3193)