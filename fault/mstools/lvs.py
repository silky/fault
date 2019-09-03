import os
from pathlib import Path
from fault.subprocess_run import subprocess_run


cmd_tmpl = '''\
#!tvf

LAYOUT SYSTEM {layout_system}
LAYOUT PRIMARY "{layout_primary}"
LAYOUT PATH "{layout_path}"
SOURCE SYSTEM {source_system}
SOURCE PRIMARY "{source_primary}"
SOURCE PATH "{source_path}"
LVS REPORT "{lvs_report}"

{source_files}
'''


def lvs(layout, schematic, rules=None, cwd='.', env=None, add_to_env=None,
        out='lvs.report', layout_system='GDSII', source_system='SPICE',
        source_primary=None, layout_primary=None, nl='\n'):
    # NOTE: cwd should be set to the directory that contains the cds.lib
    # file.

    # set defaults
    if rules is None:
        rules = []
    if source_primary is None:
        source_primary = Path(schematic).stem
    if layout_primary is None:
        layout_primary = Path(layout).stem

    # path wrapping
    cwd = Path(cwd)
    out = Path(out)

    # create the output directory if needed
    os.makedirs(cwd, exist_ok=True)

    # format commands to source in external files
    source_files = [f'source "{rule}"' for rule in rules]
    source_files = nl.join(source_files)

    # write command file
    cmd = cmd_tmpl.format(
        layout_system=layout_system,
        layout_primary=layout_primary,
        layout_path=f'{layout}',
        source_system=source_system,
        source_primary=source_primary,
        source_path=f'{schematic}',
        source_files=source_files
    )
    cmd_file = cwd / 'cmd.tvf'
    with open(cmd_file, 'w') as f:
        f.write(cmd)

    # construct the command
    args = []
    args += ['calibre']
    args += ['-hier']
    args += ['-lvs', f'{cmd_file}']

    # run the command
    subprocess_run(args, cwd=cwd, env=env, add_to_env=add_to_env)
