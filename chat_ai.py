import os
import json
import uuid
import time
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from llama_cpp import Llama
from huggingface_hub import hf_hub_download
from typing import List, Optional
import re
from stt_whisper import STTEngine as WhisperEngine
from stt_vosk import STTEngine as VoskEngine
from tts_piper import PocketAudio

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Model Configuration ---
REPO_ID = "Qwen/Qwen3-0.6B-GGUF"
FILENAME = "Qwen3-0.6B-Q8_0.gguf"
LOCAL_DIR = "./models"
MODEL_PATH = os.path.join(LOCAL_DIR, FILENAME)
CONVERSATIONS_FILE = "conversations.json"

# --- Data Models ---
class Message(BaseModel):
    role: str
    content: str
    timestamp: float

class Conversation(BaseModel):
    id: str
    title: str
    messages: List[Message]
    updated_at: float

# --- Conversation Manager ---
class ConversationManager:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.conversations = self.load_conversations()

    def load_conversations(self):
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                return {c['id']: c for c in data}
        return {}

    def save_conversations(self):
        with open(self.storage_path, 'w') as f:
            json.dump(list(self.conversations.values()), f, indent=2)

    def create_conversation(self, title: str = "New Chat"):
        conv_id = str(uuid.uuid4())
        new_conv = {
            "id": conv_id,
            "title": title,
            "messages": [],
            "updated_at": time.time()
        }
        self.conversations[conv_id] = new_conv
        self.save_conversations()
        return new_conv

    def get_conversation(self, conv_id: str):
        return self.conversations.get(conv_id)

    def update_conversation(self, conv_id: str, messages: List[dict]):
        if conv_id in self.conversations:
            self.conversations[conv_id]["messages"] = messages
            self.conversations[conv_id]["updated_at"] = time.time()
            self.save_conversations()

    def rename_conversation(self, conv_id: str, new_title: str):
        if conv_id in self.conversations:
            self.conversations[conv_id]["title"] = new_title
            self.conversations[conv_id]["updated_at"] = time.time()
            self.save_conversations()
            return self.conversations[conv_id]
        return None

    def list_conversations(self):
        return sorted(list(self.conversations.values()), key=lambda x: x['updated_at'], reverse=True)

    def delete_conversation(self, conv_id: str):
        if conv_id in self.conversations:
            del self.conversations[conv_id]
            self.save_conversations()

# --- AI State ---
class AIState:
    def __init__(self):
        self.llm = None
        self.stt = WhisperEngine()
        self.vosk = VoskEngine()
        self.tts = PocketAudio()
        self.conv_manager = ConversationManager(CONVERSATIONS_FILE)
        self.is_recording = False
        self.is_vosk_recording = False
        self.voice_messages = [
            {"role": "system", "content": "You are a helpful assistant. Keep your responses concise for text-to-speech."}
        ]

    def load_model(self):
        if not os.path.exists(MODEL_PATH):
            print("Downloading model...")
            os.makedirs(LOCAL_DIR, exist_ok=True)
            hf_hub_download(repo_id=REPO_ID, filename=FILENAME, local_dir=LOCAL_DIR)
        
        print("Loading LLM...")
        self.llm = Llama(model_path=MODEL_PATH, n_ctx=4096, n_threads=4, verbose=False)
        self.stt.load_model()
        self.vosk.load_model()
        print("Chat AI Ready.")

    async def generate_response(self, messages, thinking=True):
        # Prepare messages
        llm_messages = []
        for m in messages:
            content = m["content"]
            # Append mode flag
            if thinking:
                if " /no_think" in content: content = content.replace(" /no_think", " /think")
                elif " /think" not in content: content += " /think"
            else:
                if " /think" in content: content = content.replace(" /think", " /no_think")
                elif " /no_think" not in content: content += " /no_think"
            llm_messages.append({"role": m["role"], "content": content})

        if not any(m["role"] == "system" for m in llm_messages):
            llm_messages.insert(0, {"role": "system", "content": "You are a helpful assistant."})

        # Sampling params based on thinking mode
        current_temp = 0.6 if thinking else 0.7
        current_top_p = 0.95 if thinking else 0.8

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: self.llm.create_chat_completion(
            messages=llm_messages,
            max_tokens=2048,
            temperature=current_temp,
            top_p=current_top_p,
            top_k=20,
            min_p=0.0,
            presence_penalty=1.5,
            stream=True
        ))
        return response

ai = AIState()

@app.on_event("startup")
async def startup_event():
    ai.load_model()

# --- REST Endpoints ---

@app.get("/conversations")
async def list_conversations():
    return ai.conv_manager.list_conversations()

@app.post("/conversations")
async def create_conversation():
    return ai.conv_manager.create_conversation()

@app.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    conv = ai.conv_manager.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv

@app.patch("/conversations/{conv_id}")
async def rename_conversation(conv_id: str, data: dict):
    new_title = data.get("title")
    if not new_title:
        raise HTTPException(status_code=400, detail="Title is required")
    conv = ai.conv_manager.rename_conversation(conv_id, new_title)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv

@app.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    ai.conv_manager.delete_conversation(conv_id)
    return {"status": "success"}

# --- WebSocket Endpoint ---

@app.websocket("/ws/chat/{conv_id}")
async def chat_websocket_endpoint(websocket: WebSocket, conv_id: str):
    await websocket.accept()
    
    conv = ai.conv_manager.get_conversation(conv_id)
    if not conv:
        await websocket.send_json({"type": "error", "message": "Conversation not found"})
        await websocket.close()
        return

    # Send history
    await websocket.send_json({
        "type": "history", 
        "messages": [{"role": m["role"], "text": m["content"]} for m in conv["messages"]]
    })

    abort_event = asyncio.Event()
    message_queue = asyncio.Queue()

    async def receive_messages():
        try:
            while True:
                data = await websocket.receive_json()
                await message_queue.put(data)
        except:
            pass

    receive_task = asyncio.create_task(receive_messages())

    try:
        while True:
            # Wait for next message from queue
            data = await message_queue.get()
            
            if data["type"] == "send":
                abort_event.clear()
                user_text = data.get("message", "")
                if not user_text:
                    continue

                # Add user message to history
                conv["messages"].append({"role": "user", "content": user_text, "timestamp": time.time()})
                
                # Update title if it's the first message
                if len(conv["messages"]) == 1:
                    conv["title"] = user_text[:30] + ("..." if len(user_text) > 30 else "")
                
                ai.conv_manager.update_conversation(conv_id, conv["messages"])

                await websocket.send_json({"type": "stream_start"})
                
                full_reply = ""
                # Use unified generator
                response = await ai.generate_response(conv["messages"], thinking=True)

                for chunk in response:
                    # Check for abort command in queue without blocking
                    while not message_queue.empty():
                        msg = await message_queue.get()
                        if msg.get("type") == "abort":
                            abort_event.set()
                        # If it's another command while generating, we could handle it here

                    if abort_event.is_set():
                        await websocket.send_json({"type": "stream_aborted"})
                        break

                    delta = chunk['choices'][0]['delta']
                    if 'content' in delta:
                        content = delta['content']
                        full_reply += content
                        await websocket.send_json({"type": "stream_delta", "text": full_reply})
                    
                    await asyncio.sleep(0.01)

                if not abort_event.is_set():
                    await websocket.send_json({"type": "stream_final", "text": full_reply})
                    # Add assistant message to history
                    conv["messages"].append({"role": "assistant", "content": full_reply, "timestamp": time.time()})
                    ai.conv_manager.update_conversation(conv_id, conv["messages"])
            
            elif data["type"] == "abort":
                abort_event.set()

    except WebSocketDisconnect:
        print(f"Client disconnected from conversation {conv_id}")
    finally:
        receive_task.cancel()

# --- Voice WebSocket Endpoint (Migrated from app.py) ---

@app.websocket("/ws")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()
    print("Voice client connected")
    
    abort_event = asyncio.Event()
    message_queue = asyncio.Queue()

    async def receive_messages():
        try:
            while True:
                data = await websocket.receive_json()
                await message_queue.put(data)
        except:
            pass

    receive_task = asyncio.create_task(receive_messages())

    try:
        while True:
            data = await message_queue.get()
            command = data.get("type")

            if command == "start_vosk":
                if not ai.is_vosk_recording:
                    ai.is_vosk_recording = True
                    async def vosk_callback(text):
                        try:
                            await websocket.send_json({"type": "vosk_partial", "text": text})
                        except: pass
                    ai.vosk.start_listening(callback=lambda t: asyncio.run_coroutine_threadsafe(vosk_callback(t), asyncio.get_event_loop()))
                    await websocket.send_json({"status": "vosk_started"})

            elif command == "stop_vosk":
                if ai.is_vosk_recording:
                    ai.is_vosk_recording = False
                    text = ai.vosk.stop_listening()
                    await websocket.send_json({"type": "vosk_final", "text": text})

            elif command == "toggle_voice":
                if not ai.is_recording:
                    abort_event.clear()
                    ai.is_recording = True
                    ai.stt.start_capture()
                    await websocket.send_json({"status": "recording"})
                else:
                    ai.is_recording = False
                    await websocket.send_json({"status": "processing"})
                    text = ai.stt.stop_and_transcribe()
                    
                    if text:
                        await websocket.send_json({"type": "transcription", "text": text})
                        
                        # Process with LLM (Voice mode: thinking=False)
                        ai.voice_messages.append({"role": "user", "content": text})
                        
                        await websocket.send_json({"type": "ai_start"})
                        full_response = ""
                        
                        response = await ai.generate_response(ai.voice_messages, thinking=False)
                        
                        for chunk in response:
                            while not message_queue.empty():
                                msg = await message_queue.get()
                                if msg.get("type") == "abort":
                                    abort_event.set()

                            if abort_event.is_set():
                                await websocket.send_json({"type": "ai_aborted"})
                                break

                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                if "content" in delta:
                                    content = delta["content"]
                                    full_response += content
                                    await websocket.send_json({"type": "ai_delta", "text": full_response})
                            
                            await asyncio.sleep(0.01)

                        if not abort_event.is_set():
                            ai.voice_messages.append({"role": "assistant", "content": full_response})
                            
                            # History limit for voice
                            if len(ai.voice_messages) > 11:
                                ai.voice_messages = [ai.voice_messages[0]] + ai.voice_messages[-10:]

                            # Clean response for TTS (strip <think> tags)
                            clean_reply = re.sub(r'<think>.*?</think>', '', full_response, flags=re.DOTALL).strip()
                            
                            if clean_reply:
                                await websocket.send_json({"type": "ai_final", "text": full_response})
                                # Trigger TTS
                                ai.tts.speak(clean_reply)
                            else:
                                await websocket.send_json({"type": "ai_final", "text": full_response})
                    else:
                        await websocket.send_json({"status": "idle", "error": "No speech detected"})

            elif command == "abort":
                abort_event.set()

    except WebSocketDisconnect:
        print("Voice client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        receive_task.cancel()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
