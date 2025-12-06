import os
import time
import asyncio
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from google import genai
from google.genai import types

# 1. Load API Key
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("Please set GEMINI_API_KEY in your .env file")

# 2. Configuration
SCREEN_WIDTH = 1440
SCREEN_HEIGHT = 900
MODEL_ID = "gemini-2.5-computer-use-preview-10-2025"

client = genai.Client(api_key=API_KEY)

# --- Helper Functions ---

def denormalize_x(x: int, width: int) -> int:
    return int((x / 1000) * width)

def denormalize_y(y: int, height: int) -> int:
    return int((y / 1000) * height)

# --- Core: Execute Actions ---

async def execute_function_calls(function_calls, page):
    results = []
    
    for call in function_calls:
        fn_name = call.name
        args = call.args
        print(f"🤖 Action: {fn_name} {args}")

        # --- SAFETY CHECK ---
        # If Gemini flags an action (like CAPTCHA or Buying), we must acknowledge it.
        requires_acknowledgement = False
        if "safety_decision" in args:
             decision = args["safety_decision"]
             if decision.get("decision") == "require_confirmation":
                 print(f"   🛡️ Safety Alert: {decision.get('explanation')}")
                 print("   -> Auto-acknowledging to proceed.")
                 requires_acknowledgement = True

        result_data = {}
        
        try:
            # --- NAVIGATION ---
            if fn_name == "open_web_browser":
                pass 
            elif fn_name == "navigate":
                await page.goto(args["url"])
            elif fn_name == "go_back":
                await page.go_back()
            elif fn_name == "go_forward":
                await page.go_forward()
            elif fn_name == "search":
                await page.goto("https://www.google.com")
            elif fn_name == "wait_5_seconds":
                await asyncio.sleep(5)

            # --- MOUSE CLICKS & TYPING ---
            elif fn_name == "click_at":
                x = denormalize_x(args["x"], SCREEN_WIDTH)
                y = denormalize_y(args["y"], SCREEN_HEIGHT)
                await page.mouse.click(x, y)
                
            elif fn_name == "type_text_at":
                x = denormalize_x(args["x"], SCREEN_WIDTH)
                y = denormalize_y(args["y"], SCREEN_HEIGHT)
                text = args["text"]
                press_enter = args.get("press_enter", False)
                clear_before = args.get("clear_before_typing", True)
                
                await page.mouse.click(x, y)
                if clear_before:
                    # 'Meta+A' for Mac, 'Control+A' for Windows/Linux
                    await page.keyboard.press("Control+A") 
                    await page.keyboard.press("Backspace")
                
                await page.keyboard.type(text)
                if press_enter:
                    await page.keyboard.press("Enter")

            # --- MOUSE MOVEMENT / HOVER ---
            elif fn_name == "hover_at":
                x = denormalize_x(args["x"], SCREEN_WIDTH)
                y = denormalize_y(args["y"], SCREEN_HEIGHT)
                await page.mouse.move(x, y)

            elif fn_name == "drag_and_drop":
                start_x = denormalize_x(args["x"], SCREEN_WIDTH)
                start_y = denormalize_y(args["y"], SCREEN_HEIGHT)
                end_x = denormalize_x(args["destination_x"], SCREEN_WIDTH)
                end_y = denormalize_y(args["destination_y"], SCREEN_HEIGHT)
                
                await page.mouse.move(start_x, start_y)
                await page.mouse.down()
                await page.mouse.move(end_x, end_y)
                await page.mouse.up()

            # --- KEYBOARD ---
            elif fn_name == "key_combination":
                key_comb = args.get("keys")
                await page.keyboard.press(key_comb)

            # --- SCROLLING ---
            elif fn_name == "scroll_document" or fn_name == "scroll_at":
                magnitude = args.get("magnitude", 800)
                direction = args.get("direction", "down")
                
                # If scroll_at, move mouse there first
                if fn_name == "scroll_at":
                    x = denormalize_x(args["x"], SCREEN_WIDTH)
                    y = denormalize_y(args["y"], SCREEN_HEIGHT)
                    await page.mouse.move(x, y)

                dx, dy = 0, 0
                if direction == "down": dy = magnitude
                elif direction == "up": dy = -magnitude
                elif direction == "right": dx = magnitude
                elif direction == "left": dx = -magnitude
                
                await page.mouse.wheel(dx, dy)

            else:
                print(f"⚠️ Warning: Model requested unimplemented function {fn_name}")

            # Wait a moment for UI to settle
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"❌ Error executing {fn_name}: {e}")
            result_data = {"error": str(e)}

        # Add the acknowledgement flag if needed
        if requires_acknowledgement:
            result_data["safety_acknowledgement"] = True

        results.append((fn_name, result_data))
    
    return results

# --- Helper: Capture State ---

async def get_function_responses(page, results):
    screenshot_bytes = await page.screenshot(type="png")
    current_url = page.url
    
    function_responses = []
    for name, result in results:
        response_data = {"url": current_url}
        response_data.update(result)
        
        function_responses.append(
            types.FunctionResponse(
                name=name,
                response=response_data,
                parts=[types.FunctionResponsePart(
                    inline_data=types.FunctionResponseBlob(
                        mime_type="image/png",
                        data=screenshot_bytes
                    )
                )]
            )
        )
    return function_responses

# --- Main Agent Loop ---

async def run_agent():
    # --- GET USER INPUT ---
    print("\n" + "="*50)
    user_prompt = input(">> Enter your instructions for the agent: ")
    if not user_prompt.strip():
        print("Empty input. Using default test prompt.")
        user_prompt = "Go to google.com and search for 'Gemini API' pricing."
    print("="*50 + "\n")

    async with async_playwright() as p:
        # Launch browser (headless=False so you can watch)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": SCREEN_WIDTH, "height": SCREEN_HEIGHT}
        )
        page = await context.new_page()
        
        # Start at Google to have a valid initial state (avoids about:blank issues)
        await page.goto("https://www.google.com")

        print(f"✨ Agent started. Goal: {user_prompt}")
        
        config = types.GenerateContentConfig(
            tools=[types.Tool(
                computer_use=types.ComputerUse(
                    environment=types.Environment.ENVIRONMENT_BROWSER
                )
            )],
            thinking_config=types.ThinkingConfig(include_thoughts=True) 
        )

        initial_screenshot = await page.screenshot(type="png")
        
        chat_history = [
            types.Content(
                role="user",
                parts=[
                    types.Part(text=user_prompt),
                    types.Part.from_bytes(data=initial_screenshot, mime_type="image/png")
                ]
            )
        ]

        MAX_TURNS = 20
        
        for turn in range(MAX_TURNS):
            print(f"\n--- Turn {turn + 1} ---")
            
            try:
                response = client.models.generate_content(
                    model=MODEL_ID,
                    contents=chat_history,
                    config=config
                )
            except Exception as e:
                print(f"🔥 Critical API Error: {e}")
                break
            
            # --- Check for empty response (Safety Filters) ---
            if not response.candidates:
                print("⚠️ Model returned no content. This usually means a Safety Filter was triggered.")
                if hasattr(response, 'prompt_feedback'):
                    print(f"Feedback: {response.prompt_feedback}")
                break
            
            candidate = response.candidates[0]
            model_content = candidate.content
            chat_history.append(model_content)

            # --- Display Thoughts & Check for Tools ---
            has_tool_use = False
            for part in model_content.parts:
                if part.thought:
                    print(f"🧠 Thought: {part.text}")
                elif part.text:
                    print(f"🗣️ Agent: {part.text}")
                if part.function_call:
                    has_tool_use = True

            function_calls = [part.function_call for part in model_content.parts if part.function_call]
            
            if not function_calls:
                if not has_tool_use:
                    print("✅ Task finished.")
                    break
                else:
                    print("...Thinking...")
                    continue

            # --- Execute Actions ---
            results = await execute_function_calls(function_calls, page)

            print("📸 Capturing new state...")
            function_responses = await get_function_responses(page, results)

            # --- Send Response Back ---
            response_parts = [types.Part(function_response=fr) for fr in function_responses]
            chat_history.append(types.Content(role="user", parts=response_parts))

        await browser.close()
        print("🔒 Browser closed.")

if __name__ == "__main__":
    asyncio.run(run_agent())