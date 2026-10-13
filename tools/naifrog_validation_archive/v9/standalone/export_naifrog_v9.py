"""Export the current development snapshot; never label it final art delivery."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess
import time

CHAT = Path(__file__).resolve().parents[1]
REPO = Path('/Users/lpz/Documents/Happy_Dash_Forward')
ENGINE = Path('/Users/lpz/Documents/Codex/2026-10-12/git-github-com-devid-hui-happy/work/audit/runtime/Godot.app/Contents/MacOS/Godot')
OUT = CHAT / 'outputs/naifrog-standalone-v9'
OUT.mkdir(parents=True, exist_ok=True)
APP = OUT / 'TheMidnightAcademy-naifrog-v9.app'
if APP.exists():
    raise SystemExit('Preflight app already exists; preserve its evidence and choose a new output directory.')
TEMPLATE_RECEIPT = json.loads((CHAT/'outputs/export-template-preparation/verified-template.json').read_text())
TEMPLATE = Path(TEMPLATE_RECEIPT['macos_template'])

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def snapshot():
    paths = [REPO/'project.godot']
    for directory, suffixes in [('scripts',{'.gd','.gdshader'}), ('scenes',{'.tscn'}),
                                ('assets/refined',{'.glb','.png','.jpg','.jpeg','.json','.ttf','.otf'})]:
        paths += [p for p in (REPO/directory).rglob('*') if p.is_file() and p.suffix in suffixes
                  and 'reference_candidate' not in p.parts and 'reconstructed_candidate' not in p.parts]
    return {str(p.relative_to(REPO)):sha(p) for p in sorted(set(paths))}

def run(command, log, timeout):
    with (OUT/log).open('w') as handle:
        p = subprocess.Popen(command, cwd=OUT, env=ENV, stdout=handle, stderr=subprocess.STDOUT)
        print('OWNED_PID', p.pid, log, flush=True)
        try:
            code = p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.terminate()
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
            code = 124
    content = (OUT/log).read_text(errors='replace')
    errors = [line for line in content.splitlines() if 'SCRIPT ERROR:' in line or line.startswith('ERROR:')]
    return {'exit':code, 'errors':errors, 'log':log}

ENV = os.environ.copy()
ENV['HDF_ARCHIVE_PATH'] = str(OUT/'isolated-archive.json')
assert sha(TEMPLATE) == TEMPLATE_RECEIPT['macos_sha256']
PRESET = REPO/'export_presets.cfg'
original = PRESET.read_bytes()
(OUT/'export_presets-before.cfg').write_bytes(original)
temporary = original.decode().replace('[preset.0.options]\n',
    '[preset.0.options]\n\ncustom_template/release='+json.dumps(str(TEMPLATE))+'\n',1).encode()
assert temporary != original
receipt = {'scope':'Current naifrog V9 production export; ordinary full-game input and subjective commercial art acceptance are not asserted.',
           'template':TEMPLATE_RECEIPT, 'production_new_character':True,
           'final_delivery':False, 'started':time.time(), 'archive_path':ENV['HDF_ARCHIVE_PATH']}
with (CHAT/'work/godot-render-import.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    before = snapshot()
    (OUT/'source-before.json').write_text(json.dumps(before,indent=2)+'\n')
    try:
        PRESET.write_bytes(temporary)
        receipt['export'] = run([str(ENGINE),'--headless','--path',str(REPO),'--export-release','macOS',str(APP)], 'export.log', 600)
    finally:
        modified = PRESET.read_bytes()
        (OUT/'export_presets-after-engine.cfg').write_bytes(modified)
        # Engine normalization is recorded; never overwrite another writer's config silently.
        if modified != temporary:
            raise RuntimeError('Unexpected concurrent preset edit; temporary and original snapshots preserved.')
        PRESET.write_bytes(original)
    receipt['preset_restored'] = PRESET.read_bytes() == original
    after = snapshot()
    receipt['inputs_unchanged'] = before == after
    receipt['changed_input_paths'] = [p for p in sorted(set(before)|set(after)) if before.get(p)!=after.get(p)]
    (OUT/'source-after.json').write_text(json.dumps(after,indent=2)+'\n')
    if receipt['export']['exit'] == 0 and not receipt['export']['errors']:
        plist_path = APP/'Contents/Info.plist'
        plist = plistlib.loads(plist_path.read_bytes())
        exe = APP/'Contents/MacOS'/plist['CFBundleExecutable']
        receipt['bundle'] = {'info':plist, 'executable':str(exe), 'sha256':sha(exe),
                             'executable_permission':os.access(exe,os.X_OK),
                             'files':[str(p.relative_to(APP)) for p in APP.rglob('*') if p.is_file()]}
        receipt['standalone_menu_startup'] = run([str(exe),'--headless','--quit-after','30'], 'standalone-menu.log',120)
        probe = (CHAT/'work/export-audit/native_pack_probe.gd').read_text().replace('res://assets/refined/nailong/nailong_lod', 'res://assets/refined/naifrog/naifrog_lod')
        probe = re.sub(r'^const OUT = .*$', 'const OUT = '+json.dumps(str(OUT/'native-load-receipt.json')),probe,flags=re.M)
        probe = probe.replace('\tquit(1 if failed else 0)',
            '\tcall_deferred("_finish", 1 if failed else 0)\n\n'
            'func _finish(exit_code: int) -> void:\n'
            '\tfor child in root.get_children():\n\t\tchild.queue_free()\n'
            '\tawait process_frame\n\tawait process_frame\n'
            '\tawait create_timer(1.0).timeout\n\tquit(exit_code)')
        probe_path = OUT/'standalone_resource_probe.gd'
        probe_path.write_text(probe)
        # Official release template omits unsafe external --script/path overrides.
        # Inspect the same exported pack with the exact-version editor runtime.
        pack = APP/'Contents/Resources'/(plist['CFBundleExecutable']+'.pck')
        receipt['pack_sha256'] = sha(pack)
        receipt['pack_resource_load'] = run([str(ENGINE),'--headless','--main-pack',str(pack),'--script',str(probe_path)], 'pack-resources.log',180)
        receipt['pack_resource_load']['runtime'] = 'Exact4.7.2 editor reads exportedPCK; no repository path supplied; distinct from release-binary input acceptance.'
        receipt['codesign_verify'] = run(['/usr/bin/codesign','--verify','--deep','--strict',str(APP)], 'codesign-verify.log',60)
receipt['finished'] = time.time()
(OUT/'validation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
assert receipt['preset_restored'] and receipt['inputs_unchanged']
assert receipt['export']['exit']==0 and not receipt['export']['errors']
for key in ['standalone_menu_startup','pack_resource_load','codesign_verify']:
    assert receipt[key]['exit']==0 and not receipt[key]['errors'], (key,receipt[key])
load_receipt = json.loads((OUT/'native-load-receipt.json').read_text())
assert load_receipt['failed']==0
print('NAIFROG_V9_STANDALONE_EXPORT_PASS; full-game ordinary input and commercial art acceptance are not asserted',flush=True)
