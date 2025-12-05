import os
import json
import asyncio
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

class CadAgent:
    def __init__(self):
        self.client = genai.Client(http_options={"api_version": "v1beta"}, api_key=os.getenv("GEMINI_API_KEY"))
        # Using a model that supports code execution and is smart enough
        self.model = "gemini-2.0-flash" 
        
        self.system_instruction = """
You are a 3D Geometry Engine. 
1. When the user asks for a shape, write a Python script to calculate its vertices (x, y, z) and faces using `numpy`.
2. DO NOT use matplotlib.
3. Your script must print the result in valid Wavefront .obj format:
   - Vertices: `v x y z`
   - Faces: `f v1 v2 v3` (1-based indexing)
4. Enclose the final OBJ output between two markers: `<<<START_OBJ>>>` and `<<<END_OBJ>>>`.
5. Ensure the mesh is valid (no duplicate vertices, correct winding order).
"""

    def parse_obj(self, obj_text):
        """
        Parses Wavefront OBJ text into vertices and edges for the frontend.
        """
        vertices = []
        edges = []
        
        lines = obj_text.split('\n')
        for line in lines:
            parts = line.strip().split()
            if not parts:
                continue
                
            if parts[0] == 'v':
                # Vertex: v x y z
                try:
                    x, y, z = map(float, parts[1:4])
                    vertices.append([x, y, z])
                except ValueError:
                    continue
                    
            elif parts[0] in ('f', 'l'):
                # Face: f v1 v2 v3 ... or Line: l v1 v2 ...
                # OBJ uses 1-based indexing
                try:
                    # Extract vertex indices (handling v/t/n format if present)
                    # We just need the first part of "v/t/n"
                    # Filter out non-numeric parts if any (sometimes models add extra junk)
                    indices = []
                    for p in parts[1:]:
                        if not p: continue
                        try:
                            # Handle negative indices (relative) - though specific prompt implies absolute
                            idx_str = p.split('/')[0]
                            idx = int(idx_str)
                            if idx < 0:
                                idx = len(vertices) + idx
                            else:
                                idx -= 1
                            indices.append(idx)
                        except ValueError:
                            continue
                    
                    if len(indices) < 2:
                        continue
                        
                    # Create edges from the face/line
                    # For a face, we connect all vertices in a loop
                    # For a line 'l', we connect them in sequence. 
                    # If it's a closed loop face, (i+1)%len. If 'l', usually it is a strip?
                    # Standard OBJ 'l' is a polyline.
                    
                    is_face = (parts[0] == 'f')
                    
                    for i in range(len(indices) - 1):
                        start = indices[i]
                        end = indices[i+1]
                        edges.append([start, end])
                    
                    # Close the loop for faces
                    if is_face:
                        edges.append([indices[-1], indices[0]])
                        
                except Exception as e:
                    print(f"Error parsing line '{line}': {e}")
                    continue
                    
        return {"vertices": vertices, "edges": edges}

    async def generate_prototype(self, prompt: str):
        """
        Generates 3D geometry for the given prompt using Gemini Code Execution.
        Returns a dictionary with 'vertices' and 'edges'.
        """
        print(f"CadAgent: Generating prototype for '{prompt}'...")
        
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    tools=[types.Tool(code_execution=types.ToolCodeExecution())],
                    temperature=1.0 # High temperature for creativity in code generation
                )
            )
            
            # Extract OBJ from execution output
            obj_data = None
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.code_execution_result:
                        output = part.code_execution_result.output
                        if "<<<START_OBJ>>>" in output:
                            try:
                                obj_data = output.split("<<<START_OBJ>>>")[1].split("<<<END_OBJ>>>")[0].strip()
                            except IndexError:
                                print("CadAgent: markers found but failed to extract data.")
            
            if not obj_data:
                # Fallback: Check text output if no code execution result (unlikely with forced tool but possible)
                print("CadAgent: No OBJ data found in code execution result.")
                # Sometimes the model might output text explaining why it failed or just text
                print(f"Debug Raw Response Text: {response.text}")
                return None

            print("CadAgent: OBJ data extracted. Parsing...")
            data = self.parse_obj(obj_data)
            
            # Basic validation
            if not data["vertices"]:
                print("CadAgent: Parsed JSON has no vertices.")
                return None
                
            print(f"CadAgent: Successfully generated {len(data['vertices'])} vertices and {len(data['edges'])} edges.")
            return data
            
        except Exception as e:
            print(f"CadAgent Error: {e}")
            import traceback
            traceback.print_exc()
            return None
