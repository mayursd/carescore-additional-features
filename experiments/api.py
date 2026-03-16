from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import shutil
from datetime import datetime
import uvicorn
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory to store recordings on the server - use absolute path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RECORDINGS_DIR = os.path.join(BASE_DIR, "recordings")
TEMP_DIR = os.path.join(BASE_DIR, "temp_chunks")

# Ensure directories exist
if not os.path.exists(RECORDINGS_DIR):
    os.makedirs(RECORDINGS_DIR)
    logger.info(f"Created recordings directory at {RECORDINGS_DIR}")
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)
    logger.info(f"Created temp directory at {TEMP_DIR}")

# Clean up temporary chunks on startup
for temp_file in os.listdir(TEMP_DIR):
    try:
        os.remove(os.path.join(TEMP_DIR, temp_file))
    except Exception as e:
        logger.warning(f"Could not delete temporary file {temp_file}: {e}")

# Dictionary to keep track of temporary chunk files for each recording
recording_sessions = {}

# Mount static files for recordings
app.mount("/static", StaticFiles(directory=BASE_DIR), name="static")

@app.post("/upload-audio/")
async def upload_audio(
    file: UploadFile = File(None),
    file_name: str = Form(...),
    is_chunk: bool = Form(False),
    is_final: bool = Form(False)
):
    # Change extension to .webm instead of .wav
    if not file_name.lower().endswith('.webm'):
        file_name = file_name.rstrip('.wav') + '.webm'
    
    # Full path to save the final file
    file_path = os.path.join(RECORDINGS_DIR, file_name)
    logger.info(f"Processing audio upload for {file_name}, is_chunk={is_chunk}, is_final={is_final}")
    
    # Check if the final file already exists
    if os.path.exists(file_path) and not is_chunk:
        # Generate a new name
        base_name = os.path.splitext(file_name)[0]
        extension = os.path.splitext(file_name)[1]
        timestamp = datetime.now().strftime("_%Y%m%d_%H%M%S")
        file_name = f"{base_name}{timestamp}{extension}"
        file_path = os.path.join(RECORDINGS_DIR, file_name)
        logger.info(f"File already exists, using new name: {file_name}")
    
    # Handle chunks
    if is_chunk and file:
        # Initialize session if not exists
        if file_name not in recording_sessions:
            recording_sessions[file_name] = []
        
        # Save the chunk to a temporary file
        chunk_path = os.path.join(TEMP_DIR, f"{file_name}_{len(recording_sessions[file_name])}.webm")
        with open(chunk_path, "wb") as f:
            content = await file.read()
            f.write(content)
        recording_sessions[file_name].append(chunk_path)
        logger.info(f"Chunk saved to {chunk_path}")
        return JSONResponse(content={"message": f"Chunk received for {file_name}"})
    
    # Handle finalization
    if is_final:
        if file_name not in recording_sessions or not recording_sessions[file_name]:
            if file:
                # Direct file upload without chunks
                with open(file_path, "wb") as f:
                    content = await file.read()
                    f.write(content)
                logger.info(f"Direct file upload saved to {file_path}")
                return JSONResponse(content={"message": f"Recording saved as {file_name}", "file_name": file_name})
            else:
                raise HTTPException(status_code=400, detail="No chunks or file found for this recording.")
        
        logger.info(f"Finalizing recording {file_name} from {len(recording_sessions[file_name])} chunks")
        
        try:
            # Simply combine all chunks by concatenating the files
            with open(file_path, "wb") as output_file:
                for chunk_path in recording_sessions[file_name]:
                    logger.info(f"Appending chunk: {chunk_path}")
                    with open(chunk_path, "rb") as chunk_file:
                        shutil.copyfileobj(chunk_file, output_file)
                    # Clean up chunk file
                    try:
                        os.remove(chunk_path)
                    except Exception as e:
                        logger.warning(f"Could not delete chunk file {chunk_path}: {e}")
            
            # Verify file was created
            if not os.path.exists(file_path):
                raise Exception(f"Failed to create file at {file_path}")
            
            # Clean up
            del recording_sessions[file_name]
            return JSONResponse(content={"message": f"Recording saved as {file_name}", "file_name": file_name})
        except Exception as e:
            logger.error(f"Error saving recording: {str(e)}", exc_info=True)
            
            # Attempt direct file save if processing fails
            if file:
                try:
                    logger.info("Attempting direct file save as fallback")
                    with open(file_path, "wb") as f:
                        file.seek(0)
                        content = await file.read()
                        f.write(content)
                    return JSONResponse(content={"message": f"Recording saved directly as {file_name}", "file_name": file_name})
                except Exception as direct_error:
                    logger.error(f"Direct save also failed: {str(direct_error)}")
            
            raise HTTPException(status_code=500, detail=f"Failed to save recording: {str(e)}")
    
    raise HTTPException(status_code=400, detail="Invalid request: must specify is_chunk or is_final")

@app.get("/list-recordings/")
async def list_recordings():
    # List all WebM files in the recordings directory
    try:
        all_files = os.listdir(RECORDINGS_DIR)
        saved_files = [f for f in all_files if f.endswith((".webm", ".wav"))]
        # Sort by modification time, newest first
        saved_files.sort(key=lambda x: os.path.getmtime(os.path.join(RECORDINGS_DIR, x)), reverse=True)
        logger.info(f"Found {len(saved_files)} recordings")
        return JSONResponse(content={"recordings": saved_files})
    except Exception as e:
        logger.error(f"Error listing recordings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list recordings: {str(e)}")

@app.delete("/delete-recording/{file_name}")
async def delete_recording(file_name: str):
    file_path = os.path.join(RECORDINGS_DIR, file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Recording {file_name} not found")
    
    try:
        os.remove(file_path)
        logger.info(f"Deleted recording {file_name}")
        return JSONResponse(content={"message": f"Recording {file_name} deleted successfully"})
    except Exception as e:
        logger.error(f"Error deleting file {file_name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete recording: {str(e)}")

@app.get("/recordings/{file_name}")
async def get_recording(file_name: str):
    file_path = os.path.join(RECORDINGS_DIR, file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Recording {file_name} not found")
    
    # Set appropriate media type based on file extension
    media_type = "audio/webm" if file_name.endswith(".webm") else "audio/wav"
    return FileResponse(file_path, media_type=media_type, filename=file_name)

if __name__ == "__main__":
    logger.info(f"Starting server with recordings dir: {RECORDINGS_DIR}")
    logger.info("Serving recordings through /static/recordings/ endpoint")
    uvicorn.run(app, host="0.0.0.0", port=8000)