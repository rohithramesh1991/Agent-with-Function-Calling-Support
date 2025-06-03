import os
import importlib

tool_dir = os.path.dirname(__file__)
for file in os.listdir(tool_dir):
    if file.endswith(".py") and file != "__init__.py":
        importlib.import_module(f"tools.{file[:-3]}")