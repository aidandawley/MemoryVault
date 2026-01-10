from fastapi import FastAPI

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:5173",
]

@app.get("/")
async def read_root():
    return {"Hello": "World"}
