"""
Wrapper command that imports the actual implementation from import_config directory.
This allows Django's management command discovery to find the command while keeping
the implementation organized in the import_config directory.
"""

import sys
import os

# Add the import_config directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
import_config_dir = os.path.join(os.path.dirname(current_dir), "import_config")
sys.path.insert(0, import_config_dir)

# Import the actual command implementation
from import_program_config import Command  # noqa: F401, E402
