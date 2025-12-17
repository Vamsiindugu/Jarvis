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

### 4. 🔐 Face Authentication Setup
To use the secure voice features, ADA needs to know what you look like.

1. Take a clear photo of your face (or use an existing one).
2. Rename the file to `reference.jpg`.
3. Drag and drop this file into the `ada_v2/backend` folder.
4. (Optional) You can toggle this feature on/off in `settings.json` by changing `"face_auth_enabled": true/false`.

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

### 5. 🔑 Gemini API Key Setup
ADA uses Google's Gemini API for voice and intelligence. You need a free API key.

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Sign in with your Google account.
3. Click **"Create API Key"** and copy the generated key.
4. Create a file named `.env` in the `ada_v2` folder (same level as `README.md`).
5. Add this line to the file:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```
6. Replace `your_api_key_here` with the key you copied.

> **Note**: Keep this key private! Never commit your `.env` file to Git.

---

## 🚀 Running ADA V2

You have two options to run the app. Ensure your `ada_v2_1` environment is active!

### Option 1: The "Easy" Way (Single Terminal)
The app is smart enough to start the backend for you.
1. Open your terminal in the `ada_v2` folder.
2. Activate your environment: `conda activate ada_v2_1`
3. Run:
   ```bash
   npm run dev
   ```
4. The backend will start automatically in the background.

### Option 2: The "Developer" Way (Two Terminals)
Use this if you want to see the Python logs (recommended for debugging).

**Terminal 1 (Backend):**
```bash
conda activate ada_v2_1
python backend/server.py
```

**Terminal 2 (Frontend):**
```bash
# Environment doesn't matter here, but keep it simple
npm run dev
```

---

## ✅ First Flight Checklist (Things to Test)

1. **Voice Check**: Say "Hello Ada". She should respond.
2. **Vision Check**: Look at the camera. If Face Auth is on, the lock screen should unlock.
3. **CAD Check**: Open the CAD window and say "Create a cube". Watch the logs.
4. **Web Check**: Open the Browser window and say "Go to Google".
5. **Smart Home**: If you have Kasa devices, say "Turn on the lights".

---

## ▶️ Commands & Tools Reference

### 🗣️ Voice Commands
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

## ❓ Troubleshooting FAQ

### `dlib` fails to build / install
**Symptoms**: Errors mentioning `CMake`, `boost`, or C++ compilation during `pip install dlib`.

**Solution**:
- **Mac**: Ensure you ran `brew install cmake boost boost-python3`.
- **Windows**: Install Visual Studio 2022 with "Desktop development with C++" workload, then restart your terminal.
- Try installing `dlib` separately first: `pip install dlib` before running `pip install -r requirements.txt`.

---

### Camera not working / Permission denied (Mac)
**Symptoms**: Error about camera access, or video feed shows black.

**Solution**:
1. Go to **System Preferences > Privacy & Security > Camera**.
2. Ensure your terminal app (e.g., Terminal, iTerm, VS Code) has camera access enabled.
3. Restart the app after granting permission.

---

### `GEMINI_API_KEY` not found / Authentication Error
**Symptoms**: Backend crashes on startup with "API key not found".

**Solution**:
1. Make sure your `.env` file is in the root `ada_v2` folder (not inside `backend/`).
2. Verify the format is exactly: `GEMINI_API_KEY=your_key` (no quotes, no spaces).
3. Restart the backend after editing the file.

---

### CAD generation fails / build123d errors
**Symptoms**: "ModuleNotFoundError: build123d" or numpy version conflicts.

**Solution**:
1. Ensure you created the **second** environment: `conda create -n ada_cad_env python=3.11`.
2. Activate it (`conda activate ada_cad_env`) and run `pip install build123d numpy`.
3. Update the path in `backend/cad_agent.py` to point to this environment's Python (see [CAD Agent Path](#-critical-configure-cad-agent-path)).

---

### WebSocket connection errors (1011)
**Symptoms**: `websockets.exceptions.ConnectionClosedError: 1011 (internal error)`.

**Solution**:
This is a server-side issue from the Gemini API. Simply reconnect by clicking the connect button or saying "Hello Ada" again. If it persists, check your internet connection or try again later.

---

## 📸 What It Looks Like

*Coming soon! Screenshots and demo videos will be added here.*

