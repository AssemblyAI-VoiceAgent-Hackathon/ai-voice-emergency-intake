from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_item():
  return{"message":"Working good"}