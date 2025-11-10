import uvicorn
from app import app

if __name__ == "__main__":
    # This is the main entry point for the web application.
    # It starts the Uvicorn server, which runs the FastAPI app.
    uvicorn.run(app, host="0.0.0.0", port=8000)
