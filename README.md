# A.D.A V2 - Advanced Design Assistant

ADA V2 is a sophisticated AI assistant designed for multimodal interaction, running on a dual-environment architecture to bridge the gap between real-time vision, voice, and parametric CAD engineering.

## 🌟 Capabilities at a Glance

- **🗣️ Low-Latency Voice**: Real-time conversation with interruption handling using Gemini Native Audio.
- **🧊 Parametric CAD**: Generates editable, mathematically accurate 3D models (STL) using `build123d`.
- **🖐️ Minority Report UI**: Spatial gesture control for grabbing, moving, and snapping UI windows.
- **👁️ Face Authentication**: Local, secure computer vision login system.
- **🌐 Web Agent**: Autonomous browser automation for searching and data retrieval.
- **🏠 Smart Home**: control over local TP-Link Kasa lights and plugs.

---

## 🛠️ Installation Requirements

### 🆕 Absolute Beginner Setup (Start Here)
If you have never coded before, follow these steps first!

**Step 1: Install Visual Studio Code (The Editor)**
- Download and install [VS Code](https://code.visualstudio.com/). This is where you will write code and run commands.

**Step 2: Install Anaconda (The Manager)**
- Download [Miniconda](https://docs.conda.io/en/latest/miniconda.html) (a lightweight version of Anaconda).
- This tool allows us to create isolated "playgrounds" (environments) for our code so different projects don't break each other.
- **Windows Users**: During install, check "Add Anaconda to my PATH environment variable" (even if it says not recommended, it makes things easier for beginners).

**Step 3: Install Git (The Downloader)**
- **Windows**: Download [Git for Windows](https://git-scm.com/download/win).
- **Mac**: Open the "Terminal" app (Cmd+Space, type Terminal) and type `git`. If not installed, it will ask to install developer tools—say yes.

**Step 4: Get the Code**
1. Open your terminal (or Command Prompt on Windows).
2. Type this command and hit Enter:
   ```bash
   git clone https://github.com/nazirlouis/ada_v2.git
   ```
3. This creates a folder named `ada_v2`.

**Step 5: Open in VS Code**
1. Open VS Code.
2. Go to **File > Open Folder**.
3. Select the `ada_v2` folder you just downloaded.
4. Open the internal terminal: Press `Ctrl + ~` (tilde) or go to **Terminal > New Terminal**.

---

### ⚠️ Technical Prerequisites
Once you have the basics above, continue here. This project has **strict** requirements due to the combination of legacy vision libraries (`dlib` for face rec) and modern CAD tools (`build123d`).

### 1. System Dependencies (C++ Build Tools)
Required for compiling `dlib` and `face_recognition`.

**MacOS:**
```bash
# Core build tools for face_recognition/dlib
brew install cmake
brew install boost
brew install boost-python3

# Audio Input/Output support (PyAudio)
brew install portaudio
```

**Windows:**
- Install Visual Studio Community 2022 with "Desktop development with C++".
- Install CMake and add to PATH.

### 2. Python Environments (Dual Setup)
You must create **TWO** separate environments.

**Env A: Main Backend (`ada_v2_1`)**
Runs the Server, Voice, Vision, and Web Agent.
```bash
conda create -n ada_v2_1 python=3.10
conda activate ada_v2_1

# 1. Install dlib first (verify cmake is installed)
pip install dlib

# 2. Install main requirements
pip install -r requirements.txt

# 3. Install Playwright browsers
playwright install chromium
```

**Env B: CAD Generation (`ada_cad_env`)**
Runs isolated CAD generation scripts.
```bash
conda create -n ada_cad_env python=3.11
conda activate ada_cad_env

# Install build123d and numpy (requires newer numpy than Env A)
pip install build123d numpy
```

### ⚠️ CRITICAL: Configure CAD Agent Path
The main backend needs to know **exactly** where the CAD environment's python executable is located.

1. Activate your CAD env: `conda activate ada_cad_env`
2. Find the path: `which python` (or `where python` on Windows).
   - Example Output: `/opt/anaconda3/envs/ada_cad_env/bin/python`
3. Edit `backend/cad_agent.py` around line 147:
   ```python
   # UPDATE THIS PATH to match your system
   cad_python_path = "/path/to/your/envs/ada_cad_env/bin/python"
   ```

### 3. Frontend Setup
```bash
npm install
```

---

## ⚙️ Configuration (`settings.json`)

The system creates a `settings.json` file on first run. You can modify this to change behavior:

| Key | Type | Description |
| :--- | :--- | :--- |
| `face_auth_enabled` | `bool` | If `true`, blocks all AI interaction until your face is recognized via the camera. |
| `tool_permissions` | `obj` | Controls manual approval for specific tools. |
| `tool_permissions.generate_cad` | `bool` | If `true`, requires you to click "Confirm" on the UI before generating CAD. |
| `tool_permissions.run_web_agent` | `bool` | If `true`, requires confirmation before opening the browser agent. |
| `tool_permissions.write_file` | `bool` | **Critical**: Requires confirmation before the AI writes code/files to disk. |

---

## ▶️ Commands & Tools Reference

### �️ Voice Commands
- "Switch project to [Name]"
- "Create a new project called [Name]"
- "Turn on the [Room] light"
- "Make the light [Color]"
- "Pause audio" / "Stop audio"

### 🧊 3D CAD
- **Prompt**: "Create a 3D model of a hex bolt."
- **Iterate**: "Make the head thinner." (Requires previous context)
- **Files**: Saves to `projects/[ProjectName]/output.stl`.

### 🌐 Web Agent
- **Prompt**: "Go to Amazon and find a USB-C cable under $10."
- **Note**: The agent will auto-scroll, click, and type. Do not interfere with the browser window while it runs.

---

## 🧠 Under the Hood: System Architecture

### 1. Communication (The Brain)
**Native Audio Streaming (Low Latency)**
- **Direct WebSocket**: Uses `google.genai aio.live.connect` in `backend/ada.py` to establish a persistent WebSocket link.
- **Bypass Legacy Pipelines**: Audio PCM chunks are sent directly to **Gemini 2.5 Flash Native Audio**, bypassing traditional Transcribe-Think-TTS pipelines for ultra-low latency.
- **Interruption Handling**: The `receive_audio` loop actively manages the stream. If you speak while Ada is talking, the model halts generation instantly, mimicking natural conversation flow.

**Personality Injection**
- System instruction in `backend/ada.py` enforces a specific persona: "Witty," "Charming," addresses you as "Sir," and uses the "Kore" voice preset.

**Resilient Connection Logic**
- **Auto-Reconnect with Context**: If the connection drops, the system fetches the recent `chat_history.jsonl` via `ProjectManager` and feeds it back to the model so it "remembers" the context.

**Dual-Stream Visualization**
- **Input**: `TopAudioBar.jsx` uses the browser’s `AudioContext` to visualize raw microphone input.
- **Output**: `Visualizer.jsx` reacts to the AI’s audio frequency data with a breathing/pulsing circle effect that scales based on amplitude.

### 2. Hand Tracking & Interface (The Body)
**"Minority Report" Gesture Control**
- **MediaPipe Integration**: `App.jsx` initializes `HandLandmarker` on the CPU to avoid GPU context conflicts.
- **Coordinate Mapping**: Maps the Index Finger Tip (Landmark 8) to screen coordinates with a custom sensitivity factor (default 2.0x), allowing you to reach corners without exaggerated movement.
- **Physics-Based Smoothing**: Implements a Linear Interpolation (Lerp) factor of 0.2 to eliminate jitter and make the cursor feel "heavy" and precise.
- **Magnetic Button Snapping**: The cursor physically "snaps" to the center of interactive elements (buttons) when within 50px (`SNAP_THRESHOLD`), applying a glowing CSS effect.

**Modular Spatial UI (The "Fist" Gesture)**
- **Fist Detection**: Checks if finger tips are closer to the wrist than their respective knuckles.
- **Spatial Grabbing**: If a fist is detected while hovering over a window (CAD, Browser, Chat), it locks onto that element allow you to physically grab and rearrange UI components in 3D space.

### 3. CAD Generation (The Engineer)
**Parametric Design with "Thinking" Model**
- **Model Switching**: `backend/cad_agent.py` switches to **Gemini 3 Pro Preview** specifically for this task to utilize "Thinking" (Chain of Thought) capabilities.
- **Parametric Scripting**: Generates Python scripts using the `build123d` library ensuring mathematically accurate models.

**Isolated Execution Environment**
- Code is executed locally using a specific Conda environment (`/opt/anaconda3/envs/ada_cad_env`) to manage dependencies (like numpy versions) separately from the main backend.

**The "Reflexion" Loop (Self-Healing)**
- If the generated Python script crashes, the agent captures the `stderr` (error), feeds it back to Gemini with the prompt "Please fix the code...", and retries automatically up to 3 times.

**Real-Time "Thinking" Stream**
- The backend streams the model's internal "Thought" process to the frontend (`CadWindow.jsx`), displaying a Matrix-style scrolling log of how the AI is solving the geometry problem.

### 4. Browser Control (The Knowledge)
**Computer Use Agent**
- Uses **Gemini 2.5 Computer Use Preview** in `backend/web_agent.py`.
- **Full Action Suite**: Supports `click_at`, `type_text_at` (with auto-clearing via Ctrl+A), `scroll`, and `drag_and_drop`.
- **Live Feedback**: Streams screenshots via Playwright after every action to `BrowserWindow.jsx` along with a scrolling action log.
- **Safety**: Automatically detects and acknowledges "safety_decision" flags from the API to maintain agent flow.

### 5. Smart Home Control (The Physical World)
**Cloud-Free Discovery**
- Uses `python-kasa` in `backend/kasa_agent.py` to discover devices on the local LAN via broadcast (No Cloud/Internet required).
- **Intelligent Resolution**: Resolves targets by Alias ("Bedroom Light") or IP.
- **Natural Language Color Mapping**: Maps names like "cyan", "warm", "pink" to specific HSV tuples for complex mood lighting.

### 6. Project & File Management (The Organizer)
**Dynamic Project System**
- **Auto-Creation**: Automatically creates detailed project folders in `projects/` when work begins in the temp buffer.
- **Context Injection**: When switching projects, the manager reads all compatible text files (.py, .js, .md) and injects them into the AI's context window.
- **Chat Persistence**: Every message is logged to `chat_history.jsonl` within the specific project folder.

### 7. Security & Protocol (The Gatekeeper)
**Face Authentication Lock**
- **Local Vision**: `backend/authenticator.py` runs `face_recognition` and `dlib` in a separate thread.
- **Hard Lock**: The audio loop checks `authenticator.authenticated`; if false, voice commands are completely ignored.
- **Human-in-the-Loop**: Sensitive tools (`write_file`, `run_web_agent`) trigger a `ConfirmationPopup.jsx` on the frontend that creates a blocking wait on the backend until approved.

### 8. Long Term Memory (The Soul)
- **Session Serialization**: Conversation logs are saved to `long_term_memory/` with timestamps.
- **Memory Injection**: The `upload_memory` event allows uploading previous logs, treating them as "System Notifications" to restore the AI's memory of past events/rules.
