from fastapi import FastAPI

app = FastAPI(title="SURA API", version="1.0.0")

@app.get("/")
def health_check():
    return {"status": "ok", "mensaje": "API SURA funcionando"}