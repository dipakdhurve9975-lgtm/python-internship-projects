"""Package source and final deliverables without runtime histories or environments."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
root=Path(__file__).resolve().parents[1]
target=root.parent/'python-internship-projects.zip'
excluded={'.venv','__pycache__','.pytest_cache','qa','runtime','.git'}
with ZipFile(target,'w',ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob('*')):
        relative=path.relative_to(root)
        if not path.is_file() or any(part in excluded for part in relative.parts):continue
        if path.suffix in ('.pyc','.sqlite3') or path.name in ('history.json','.env'):continue
        archive.write(path,root.name+'/'+relative.as_posix())
with ZipFile(target) as archive:
    assert archive.testzip() is None
    names=archive.namelist()
    assert any(name.endswith('Python_Applications_Report.pdf') for name in names)
    assert not any('/runtime/' in name or '/.venv/' in name for name in names)
print(f'{target}\n{len(names)} files; {target.stat().st_size} bytes; archive integrity verified.')
