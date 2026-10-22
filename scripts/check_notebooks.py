"""Validate maintained notebooks without authenticating or executing remote exports."""
from pathlib import Path
import ast
import nbformat
root=Path(__file__).resolve().parents[1]
count=0
for path in sorted((root/'notebooks').glob('*.ipynb')):
    nb=nbformat.read(path,as_version=4);nbformat.validate(nb)
    for cell in nb.cells:
        if cell.cell_type=='code':
            ast.parse(cell.source,filename=str(path));count+=1
            if cell.execution_count is not None or cell.outputs:
                raise ValueError(f'Generated working notebook must be output-free: {path}')
print(f'Validated {len(list((root/"notebooks").glob("*.ipynb")))} notebooks and {count} Python cells; no remote execution claimed.')
