"""Launch an unmodified Windows vendor converter with process-local paths."""
import os
from pathlib import Path
import runpy
import sys

root = Path(os.environ.get('QB560D_SNPE_SDK_ROOT', str(Path(__file__).resolve().parents[1] / '.build/sdk-public-2.26/qairt/2.26.0.240828'))).resolve()
sys.path.insert(0, str(root / 'lib/python'))
os.environ['SNPE_ROOT'] = str(root)
os.environ['QNN_SDK_ROOT'] = str(root)
os.environ['PATH'] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get('PATH', '')
dll_directory = os.add_dll_directory(str(root / 'lib/x86_64-windows-msvc'))
entry = root / 'bin/x86_64-windows-msvc' / sys.argv[1]
sys.argv = [str(entry)] + sys.argv[2:]
runpy.run_path(str(entry), run_name='__main__')
