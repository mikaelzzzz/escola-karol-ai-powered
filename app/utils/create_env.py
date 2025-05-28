"""
Script to create .env file from .env.template
"""
import os
import shutil
from pathlib import Path

def create_env():
    # Get the project root directory (2 levels up from this script)
    project_root = Path(__file__).parent.parent.parent
    
    template_path = project_root / '.env.template'
    env_path = project_root / '.env'
    
    if not template_path.exists():
        print(f'Error: Template file not found at {template_path}')
        return
        
    shutil.copy(template_path, env_path)
    print(f'.env file created successfully at {env_path}!')

if __name__ == '__main__':
    create_env() 