import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.worker import BlenderWorker

file_path = r"C:\GitHub\vectoring\assets\testfile.dxf"
blender_worker = BlenderWorker(file_path)
blender_worker.main()