from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import chatbot router
from .routers.chatbot import router as chatbot_router

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include chatbot router
app.include_router(chatbot_router)

# Mount static files from the React app release folder
app.mount("/assets", StaticFiles(directory="frontend/release/assets"), name="assets")

# Serve static files like vite.svg
@app.get("/vite.svg")
async def serve_vite_svg():
    return FileResponse("frontend/release/vite.svg")

# API endpoints
@app.get("/api/")
def read_root():
    return {"message": "Hello World"}

# SPA fallback - serve React app for all other routes
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # Check if the file exists in the release folder
    file_path = f"frontend/release/{full_path}"
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # For all other routes, serve the React app (SPA fallback)
    return FileResponse("frontend/release/index.html")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
