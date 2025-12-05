import os

def create_project_folder(project_name: str):
    """Creates a new folder for a project.
    
    Args:
        project_name: The name of the project folder to create.
    """
    # Sanitize the project name to be safe for file systems
    safe_project_name = "".join([c for c in project_name if c.isalpha() or c.isdigit() or c in (' ', '_', '-')]).rstrip()
    safe_project_name = safe_project_name.replace(" ", "_")
    
    # Define the root directory for projects. 
    # Adjust this path as needed. For now, using a "Projects" folder in the current directory.
    # In a real scenario, this might be an absolute path or relative to the user's home.
    # Given the user's context: c:\Users\nazir\Documents\Projects\ada_v2
    # We'll create it in the parent directory or a subdirectory. 
    # Let's create it in a 'Projects' subdirectory of the current working directory for safety and visibility.
    
    base_path = os.path.join(os.getcwd(), "Projects")
    
    if not os.path.exists(base_path):
        os.makedirs(base_path)
        
    project_path = os.path.join(base_path, safe_project_name)
    
    try:
        if not os.path.exists(project_path):
            os.makedirs(project_path)
            return {"result": f"Created project folder at {project_path}"}
        else:
            return {"result": f"Folder already exists at {project_path}"}
    except Exception as e:
        return {"result": f"Failed to create folder: {str(e)}"}

# Tool definition for Gemini
create_project_folder_tool = {
    "name": "create_project_folder",
    "description": "Creates a new folder for a project with the given name.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "project_name": {
                "type": "STRING",
                "description": "The name of the project."
            }
        },
        "required": ["project_name"]
    }
}

tools_list = [{"function_declarations": [create_project_folder_tool]}]
