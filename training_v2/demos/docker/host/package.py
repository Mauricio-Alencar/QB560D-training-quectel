"""Build the complete training release, including this Docker module."""
from pathlib import Path
import subprocess
import sys
root=Path(__file__).resolve().parents[3]
if __name__=='__main__':
    subprocess.run([sys.executable,str(root/'host/build_release.py'),*sys.argv[1:]],check=True)
