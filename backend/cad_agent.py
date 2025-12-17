import os
import json
import asyncio
from google import genai
from google.genai import types
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List

load_dotenv()

class CadAgent:
    def __init__(self, on_thought=None, on_status=None):
        self.client = genai.Client(http_options={"api_version": "v1beta"}, api_key=os.getenv("GEMINI_API_KEY"))
        # Using Gemini 2.5 Pro for thinking/streaming support
        self.model = "gemini-3-pro-preview"
        self.on_thought = on_thought  # Callback for streaming thoughts 
        self.on_status = on_status  # Callback for retry status info
        
        self.system_instruction = """
You are a Python-based 3D CAD Engineer using the `build123d` library.
Your goal is to write a Python script that generates a 3D model based on the user's request.

Requirements:
1. Start with `from build123d import *`.
2. Include `import numpy as np` if you use any numpy functions (like `np.sign`, `np.pi`).
3. You MUST assign the final object to a variable named `result_part`.
4. If you create a sketch or line, extrude it to make it a solid `Part`.
5. The model should be centered at (0,0,0) and have reasonable dimensions (mm).
6. **IMPORTANT**: Do NOT use old or PascalCase function names for core operations.
   - Use `make_face()` instead of `MakeFace()`.
   - Use `extrude()` instead of `Extrude()`.
   - Use `fillet()` instead of `Fillet()`.
   - Use `chamfer()` instead of `Chamfer()`.
   - Use `revolve()` instead of `Revolve()`.
   - Use `loft()` instead of `Loft()`.
   - Use `sweep()` instead of `Sweep()`.
   - Use `offset()` instead of `Offset()`.
   - generally prefer lowercase builder methods inside contexts.

7. **Vector Access**: Do NOT access vector components like `v.X`, `v.Y`, `v.Z` unless you are sure they exist (use `v.X` etc on Vector objects, but ensure they are Vectors).
8. **Final Output**: The script MUST end by exporting the final part to an STL file named 'output.stl'.
   - `export_stl(result_part, 'output.stl')`

9. **Robustness**: Operations like `fillet()` and `chamfer()` will crash if the radius is too large for the geometry.
   - Use conservative values (e.g., 0.5mm to 2mm) unless you are certain of the dimensions.
   - If a fillet is purely aesthetic, keep it small to ensure success.

Example Script:
```python
from build123d import *

with BuildPart() as p:
    Box(10, 10, 10)
    Fillet(p.edges(), radius=1)

result_part = p.part
export_stl(result_part, 'output.stl')
```
"""

    async def generate_prototype(self, prompt: str):
        """
        Generates 3D geometry by asking Gemini for a script, then running it LOCALLY.
        """
        print(f"[CadAgent DEBUG] [START] Generation started for: '{prompt}'")
        
        try:
            # Clean up old output (in /tmp)
            if os.path.exists("/tmp/output.stl"):
                os.remove("/tmp/output.stl")

            max_retries = 3
            current_prompt = f"You are a build123d expert. Write a generic python script to create a 3D model of: {prompt}. Ensure you export to 'output.stl'. Unscaled."
            
            for attempt in range(max_retries):
                print(f"[CadAgent DEBUG] Attempt {attempt + 1}/{max_retries}")
                
                # Emit status update
                if self.on_status:
                    status_info = {
                        "status": "generating" if attempt == 0 else "retrying",
                        "attempt": attempt + 1,
                        "max_attempts": max_retries,
                        "error": None
                    }
                    self.on_status(status_info)
                
                # 1. Ask Gemini for the code with streaming and thinking
                raw_content = ""
                stream = await self.client.aio.models.generate_content_stream(
                    model=self.model,
                    contents=current_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        temperature=1.0,
                        thinking_config=types.ThinkingConfig(include_thoughts=True)
                    )
                )
                async for chunk in stream:
                    if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                        for part in chunk.candidates[0].content.parts:
                            if not part.text:
                                continue
                            elif part.thought:
                                # Stream thought to callback
                                if self.on_thought:
                                    self.on_thought(part.text)
                            else:
                                # Accumulate answer text
                                raw_content += part.text
                
                if not raw_content:
                    print("[CadAgent DEBUG] [ERR] Empty response from model.")
                    return None

                # 2. Extract Code Block
                import re
                code_match = re.search(r'```python(.*?)```', raw_content, re.DOTALL)
                if code_match:
                    code = code_match.group(1).strip()
                else:
                    # Fallback: assume entire text is code if no blocks, or fail
                    print("[CadAgent DEBUG] [WARN] No ```python block found. Trying heuristic...")
                    if "import build123d" in raw_content:
                        code = raw_content
                    else:
                        print("[CadAgent DEBUG] [ERR] Could not extract python code.")
                        return None
                # 3. Save to Local File (use /tmp to avoid triggering uvicorn reload)
                script_name = "/tmp/temp_cad_gen.py"
                output_stl = "/tmp/output.stl"
                with open(script_name, "w") as f:
                    # Inject output path into the script
                    code_with_path = code.replace("output.stl", output_stl)
                    f.write(code_with_path)
                    
                print(f"[CadAgent DEBUG] [EXEC] Running local script: {script_name}")
                
                # 4. Execute Locally
                import subprocess
                import sys
                
                # Use the dedicated environment for CAD generation to avoid numpy conflicts
                # Main env: numpy < 2 (for face_recognition)
                # CAD env: numpy >= 2 (for build123d)
                cad_python_path = "/opt/anaconda3/envs/ada_cad_env/bin/python"
                
                proc = await asyncio.create_subprocess_exec(
                    cad_python_path, script_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await proc.communicate()
                
                if proc.returncode != 0:
                    error_msg = stderr.decode()
                    # Extract a concise error message for display
                    error_lines = error_msg.strip().split('\n')
                    short_error = error_lines[-1][:100] if error_lines else "Unknown error"
                    print(f"[CadAgent DEBUG] [ERR] Script Execution Failed:\n{error_msg}")
                    
                    # Emit retry status with error
                    if self.on_status:
                        self.on_status({
                            "status": "retrying",
                            "attempt": attempt + 1,
                            "max_attempts": max_retries,
                            "error": short_error
                        })
                    
                    # Preparing feedback for next attempt
                    current_prompt = f"""
The Python script you generated failed to execute with the following error:
{error_msg}

Please fix the code to resolve this error. Return the full corrected script. 
Ensure you still export to 'output.stl'.
Original request: {prompt}
"""
                    continue # Retry loop
                
                print(f"[CadAgent DEBUG] [OK] Script executed successfully.")
                
                # 5. Read Output
                if os.path.exists(output_stl):
                    print(f"[CadAgent DEBUG] [file] '{output_stl}' found.")
                    with open(output_stl, "rb") as f:
                        stl_data = f.read()
                        
                    import base64
                    b64_stl = base64.b64encode(stl_data).decode('utf-8')
                    
                    return {
                        "format": "stl",
                        "data": b64_stl
                    }
                else:
                     print(f"[CadAgent DEBUG] [ERR] '{output_stl}' was not generated.")
                     # If script ran but no output, treat as failure and retry?
                     # Ideally yes.
                     current_prompt = f"The script executed successfully but 'output.stl' was not found. Ensure you call `export_stl(result_part, 'output.stl')` at the end."
                     continue

            # If loop finishes without success
            print("[CadAgent DEBUG] [ERR] All attempts failed.")
            if self.on_status:
                self.on_status({
                    "status": "failed",
                    "attempt": max_retries,
                    "max_attempts": max_retries,
                    "error": "All generation attempts failed"
                })
            return None

        except Exception as e:
            print(f"CadAgent Error: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def iterate_prototype(self, prompt: str):
        """
        Iterates on the existing design by reading 'temp_cad_gen.py' and applying changes.
        """
        print(f"[CadAgent DEBUG] [START] Iteration started for: '{prompt}'")
        
        script_name = "/tmp/temp_cad_gen.py"
        output_stl = "/tmp/output.stl"
        existing_code = ""
        
        if os.path.exists(script_name):
            with open(script_name, "r") as f:
                existing_code = f.read()
        else:
             print("[CadAgent DEBUG] [WARN] No existing script found. Falling back to fresh generation.")
             return await self.generate_prototype(prompt)

        try:
            # Clean up old output
            if os.path.exists(output_stl):
                os.remove(output_stl)

            max_retries = 3
            current_prompt = f"""
You are iterating on an existing 3D model script.

Current Python Code:
```python
{existing_code}
```

User Request: {prompt}

Task: Rewrite the code to satisfy the user's request while maintaining the rest of the model structure.
Ensure you still export to 'output.stl'.
"""
            
            for attempt in range(max_retries):
                print(f"[CadAgent DEBUG] Iteration Attempt {attempt + 1}/{max_retries}")
                
                # Emit status update
                if self.on_status:
                    status_info = {
                        "status": "generating" if attempt == 0 else "retrying",
                        "attempt": attempt + 1,
                        "max_attempts": max_retries,
                        "error": None
                    }
                    self.on_status(status_info)
                
                # 1. Ask Gemini for the code with streaming and thinking
                raw_content = ""
                stream = await self.client.aio.models.generate_content_stream(
                    model=self.model,
                    contents=current_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        temperature=1.0,
                        thinking_config=types.ThinkingConfig(include_thoughts=True)
                    )
                )
                async for chunk in stream:
                    if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                        for part in chunk.candidates[0].content.parts:
                            if not part.text:
                                continue
                            elif part.thought:
                                # Stream thought to callback
                                if self.on_thought:
                                    self.on_thought(part.text)
                            else:
                                # Accumulate answer text
                                raw_content += part.text
                
                if not raw_content:
                    print("[CadAgent DEBUG] [ERR] Empty response from model.")
                    return None

                # 2. Extract Code Block
                import re
                code_match = re.search(r'```python(.*?)```', raw_content, re.DOTALL)
                if code_match:
                    code = code_match.group(1).strip()
                else:
                    # Fallback: assume entire text is code if no blocks, or fail
                    print("[CadAgent DEBUG] [WARN] No ```python block found. Trying heuristic...")
                    if "import build123d" in raw_content:
                        code = raw_content
                    else:
                        print("[CadAgent DEBUG] [ERR] Could not extract python code.")
                        return None
                
                # 3. Save to Local File
                # Overwrite the temp file so the next iteration builds on this one
                with open(script_name, "w") as f:
                    # Inject output path into the script
                    code_with_path = code.replace("output.stl", output_stl)
                    f.write(code_with_path)
                    
                print(f"[CadAgent DEBUG] [EXEC] Running local script: {script_name}")
                
                 # 4. Execute Locally
                import subprocess
                import sys
                
                # Use the dedicated environment for CAD generation to avoid numpy conflicts
                # Main env: numpy < 2 (for face_recognition)
                # CAD env: numpy >= 2 (for build123d)
                cad_python_path = "/opt/anaconda3/envs/ada_cad_env/bin/python"
                
                proc = await asyncio.create_subprocess_exec(
                    cad_python_path, script_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await proc.communicate()
                
                if proc.returncode != 0:
                    error_msg = stderr.decode()
                    print(f"[CadAgent DEBUG] [ERR] Script Execution Failed:\n{error_msg}")
                    
                    # Preparing feedback for next attempt
                    current_prompt = f"""
The updated Python script you generated failed to execute with the following error:
{error_msg}

Please fix the code to resolve this error. Return the full corrected script. 
Ensure you still export to 'output.stl'.
"""
                    continue # Retry loop
                
                print(f"[CadAgent DEBUG] [OK] Script executed successfully.")
                
                # 5. Read Output
                if os.path.exists(output_stl):
                    print(f"[CadAgent DEBUG] [file] '{output_stl}' found.")
                    with open(output_stl, "rb") as f:
                        stl_data = f.read()
                        
                    import base64
                    b64_stl = base64.b64encode(stl_data).decode('utf-8')
                    
                    return {
                        "format": "stl",
                        "data": b64_stl
                    }
                else:
                     print(f"[CadAgent DEBUG] [ERR] '{output_stl}' was not generated.")
                     current_prompt = f"The script executed successfully but '{output_stl}' was not found. Ensure you call `export_stl(result_part, 'output.stl')` at the end."
                     continue

            # If loop finishes without success
            print("[CadAgent DEBUG] [ERR] All attempts failed.")
            if self.on_status:
                self.on_status({
                    "status": "failed",
                    "attempt": max_retries,
                    "max_attempts": max_retries,
                    "error": "All iteration attempts failed"
                })
            return None

        except Exception as e:
            print(f"CadAgent Error: {e}")
            import traceback
            traceback.print_exc()
            return None

