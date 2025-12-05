import socketio
import uvicorn
from fastapi import FastAPI
import asyncio
import threading
import sys
import os

# Ensure we can import ada
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import ada

# Create a Socket.IO server
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()
app_socketio = socketio.ASGIApp(sio, app)

# Global state
audio_loop = None
loop_task = None

@app.get("/status")
async def status():
    return {"status": "running", "service": "A.D.A Backend"}

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")
    await sio.emit('status', {'msg': 'Connected to A.D.A Backend'}, room=sid)

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

@sio.event
async def start_audio(sid, data=None):
    global audio_loop, loop_task
    print("Starting Audio Loop...")
    
    device_index = None
    if data and 'device_index' in data:
        device_index = data['device_index']
        print(f"Using input device index: {device_index}")
    
    if audio_loop:
        print("Audio loop already running")
        return

    # Callback to send audio data to frontend
    def on_audio_data(data_bytes):
        # We need to schedule this on the event loop
        # This is high frequency, so we might want to downsample or batch if it's too much
        asyncio.create_task(sio.emit('audio_data', {'data': list(data_bytes)}))

    # Initialize ADA
    try:
        audio_loop = ada.AudioLoop(
            video_mode="none", 
            on_audio_data=on_audio_data,
            input_device_index=device_index
        )
        loop_task = asyncio.create_task(audio_loop.run())
        await sio.emit('status', {'msg': 'A.D.A Started'})
    except Exception as e:
        print(f"Error starting ADA: {e}")
        await sio.emit('error', {'msg': str(e)})

@sio.event
async def stop_audio(sid):
    global audio_loop
    if audio_loop:
        # We need to implement a stop method in ADA
        audio_loop.stop() 
        print("Stopping Audio Loop")
        # For now, we just kill the task? No, that's bad.
        # We will implement a stop flag in ada.py
        audio_loop = None
        pass

@sio.event
async def user_input(sid, data):
    text = data.get('text')
    if text and audio_loop and audio_loop.session:
        print(f"User input: {text}")
        await audio_loop.session.send(input=text, end_of_turn=True)

if __name__ == "__main__":
    uvicorn.run(app_socketio, host="127.0.0.1", port=8000)
