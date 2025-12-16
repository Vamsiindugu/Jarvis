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
    def __init__(self):
        self.client = genai.Client(http_options={"api_version": "v1beta"}, api_key=os.getenv("GEMINI_API_KEY"))
        # Using the flash model with code execution capabilities
        self.model = "gemini-2.0-flash-exp" 
        
        self.system_instruction = """
You are a Python-based 3D CAD Engineer using the `build123d` library.
Your goal is to write a Python script that generates a 3D model based on the user's request.

Requirements:
1. ALWAYS import `build123d` and all its components: `from build123d import *`.
2. Create parts using the `BuildPart` context manager or direct CSG operations.
3. You MUST assign the final object to a variable named `result_part`.
4. If you create a sketch or line, extrude it to make it a solid `Part`.
5. The model should be centered at (0,0,0) and have reasonable dimensions (mm).
6. At the end of the script, you MUST export the `result_part` to an STL file named 'output.stl'.
   Example: `export_stl(result_part, 'output.stl')`

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
            # Clean up old output
            if os.path.exists("output.stl"):
                os.remove("output.stl")

            # 1. Ask Gemini for the code (NO cloud execution)
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=f"You are a build123d expert. Write a generic python script to create a 3D model of: {prompt}. Ensure you export to 'output.stl'. Unscaled.",
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.7 
                )
            )
            
            raw_content = response.text
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
            script_name = "temp_cad_gen.py"
            with open(script_name, "w") as f:
                f.write(code)
                
            print(f"[CadAgent DEBUG] [EXEC] Running local script: {script_name}")
            
            # 4. Execute Locally
            import subprocess
            import sys
            
            # Use the current python interpreter (which has build123d installed)
            proc = await asyncio.create_subprocess_exec(
                sys.executable, script_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                print(f"[CadAgent DEBUG] [ERR] Script Execution Failed:\n{stderr.decode()}")
                return None
            
            print(f"[CadAgent DEBUG] [OK] Script executed successfully.")
            
            # 5. Read Output
            if os.path.exists("output.stl"):
                print("[CadAgent DEBUG] [file] 'output.stl' found.")
                with open("output.stl", "rb") as f:
                    stl_data = f.read()
                    
                import base64
                b64_stl = base64.b64encode(stl_data).decode('utf-8')
                
                return {
                    "format": "stl",
                    "data": b64_stl
                }
            else:
                 print("[CadAgent DEBUG] [ERR] 'output.stl' was not generated.")
                 return None

        except Exception as e:
            print(f"CadAgent Error: {e}")
            import traceback
            traceback.print_exc()
            return None

