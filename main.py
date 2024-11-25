from fastapi import FastAPI
from vidit_validation_router import validate_router

app = FastAPI()

# Include the router from vidit_validation_router
app.include_router(validate_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)