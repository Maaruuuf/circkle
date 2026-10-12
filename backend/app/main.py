from fastapi import FastAPI

app = FastAPI(title="Y")

@app.get("/health")
async def health():
    return {"status": "ok"}