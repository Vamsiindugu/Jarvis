import asyncio
import os
import sys

# Add current directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cad_agent import CadAgent

async def main():
    agent = CadAgent()
    prompt = "Generate a low-poly wireframe of a geodesic dome."
    
    print(f"Testing CadAgent with prompt: '{prompt}'")
    data = await agent.generate_prototype(prompt)
    
    if data:
        print("\n✅ Verification Successful!")
        print(f"Vertices count: {len(data['vertices'])}")
        print(f"Edges count: {len(data['edges'])}")
        
        # Print sample data
        print(f"First 5 vertices: {data['vertices'][:5]}")
        print(f"First 5 edges: {data['edges'][:5]}")
    else:
        print("\n❌ Verification Failed!")

if __name__ == "__main__":
    asyncio.run(main())
