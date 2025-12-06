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
        self.model = "gemini-3-pro-preview" 
        
        self.system_instruction = """
You are a Python-based 3D Geometry Generator.
Your goal is to write a Python script that calculates 3D vertices and edges for a requested shape.

Requirements:
1. The script MUST natively `print()` the result as a valid JSON string to stdout.
2. The JSON structure must be: `{"vertices": [[x,y,z], ...], "edges": [[idx1, idx2], ...]}`.
3. Use `math` or `numpy` for calculations (circles, spirals, curves).
4. Vertices should be centered at (0,0,0) and scaled reasonable (e.g. radius 2-5).
5. Generate DETAILED wireframes. For curved surfaces, use enough segments to look smooth.
6. Do NOT plot using matplotlib. Just print the JSON.
"""

    async def generate_prototype(self, prompt: str):
        """
        Generates 3D geometry for the given prompt using Gemini Code Execution.
        Returns a dictionary with 'vertices' and 'edges' lists.
        """
        print(f"[CadAgent DEBUG] 🤖 Generation started for: '{prompt}'")
        
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(
                      thinking_level="low"  
                    ),
                    system_instruction=self.system_instruction,
                    tools=[types.Tool(code_execution=types.ToolCodeExecution())],
                    temperature=1.0 # keep at 1.0
                )
            )
            
            result = None
            
            # Extract JSON from execution output
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.code_execution_result:
                        output = part.code_execution_result.output.strip()
                        print(f"[CadAgent DEBUG] 🐍 Code Execution Complete.")
                        print(f"[CadAgent DEBUG] 📄 Raw Output Length: {len(output)} chars")
                        
                        # Try to parse the output as JSON
                        try:
                            # Sometimes there might be extra print statements, so we look for valid JSON start/end or just try parsing
                            result = json.loads(output)
                            print(f"[CadAgent DEBUG] 🧬 JSON Parsed Successfully (Direct).")
                        except json.JSONDecodeError:
                            print("[CadAgent DEBUG] ⚠️ Direct JSON parsing failed. Attempting regex extraction...")
                            # Basic attempt to find JSON block if mixed with text
                            import re
                            match = re.search(r'\{.*"vertices".*\}', output, re.DOTALL)
                            if match:
                                try:
                                    result = json.loads(match.group(0))
                                    print(f"[CadAgent DEBUG] 🧬 JSON Parsed Successfully (Regex).")
                                except:
                                    print("[CadAgent DEBUG] ❌ Regex extraction failed.")
                                    pass
            
            if not result or "vertices" not in result:
                print(f"[CadAgent DEBUG] ❌ No valid 'vertices' key found in output. Raw output snippet:\n{output[:500]}...")
                # Fallback: Check text if it decided not to run code (rare with forced tool but possible)
                return None

            # Validate structure
            if not isinstance(result["vertices"], list) or not isinstance(result["edges"], list):
                print("[CadAgent DEBUG] ❌ Invalid JSON structure (not lists).")
                return None
                
            # Basic validation check
            print(f"[CadAgent DEBUG] ✅ Validation Passed: {len(result['vertices'])} vertices, {len(result['edges'])} edges.")
            
            # Debug: Save to file for inspection
            with open("last_cad_generation.json", "w") as f:
                json.dump(result, f, indent=2)
                
            return result
            
        except Exception as e:
            print(f"CadAgent Error: {e}")
            import traceback
            traceback.print_exc()
            return None

