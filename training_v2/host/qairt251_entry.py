"""Run vendor converter with process-local paths; do not modify system Python or PATH."""
import os,runpy,sys
from pathlib import Path
root=Path(os.environ.get('QB560D_QAIRT251_SDK',str(Path(__file__).resolve().parents[1]/'.build/sdk251-host/qairt/2.51.40.260930'))).resolve()
sys.path.insert(0,str(root/'lib/python'))
os.environ['QNN_SDK_ROOT']=str(root);os.environ['SNPE_ROOT']=str(root);os.environ['QAIRT_SDK_ROOT']=str(root)
native=root/'lib/x86_64-windows-msvc';os.environ['PATH']=str(native)+os.pathsep+str(Path(sys.executable).parent)+os.pathsep+os.environ.get('PATH','')
directory=os.add_dll_directory(str(native))
temporary=Path(__file__).resolve().parents[1]/'.build/qairt251-temp';temporary.mkdir(exist_ok=True)
os.environ['QAIRT_TMP_DIR']=str(temporary);os.environ['TEMP']=str(temporary);os.environ['TMP']=str(temporary)
entry=root/'bin/x86_64-windows-msvc'/sys.argv[1];sys.argv=[str(entry)]+sys.argv[2:]
runpy.run_path(str(entry),run_name='__main__')
