import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--repak', required=True, type=Path)
parser.add_argument('--uassetgui', required=True, type=Path)
parser.add_argument('--game-pak', required=True, type=Path)
parser.add_argument('--work', required=True, type=Path)
options = parser.parse_args()

output = Path(__file__).resolve().parent.parent
work = options.work.resolve()
originals = work / 'original'
payload = work / 'payload'
env = dict(os.environ, DOTNET_ROLL_FORWARD='Major')

shredders = {
    'Astro/Content/Components_Medium/Shredder_T2': (60.0, 20.0),
    'Astro/Content/Components_Large/Shredder/Shredder_T3': (60.0, 25.0),
    'Astro/Content/Components_XL/Shredder_T4': (60.0, 30.0),
}

def uassetgui(*command):
    subprocess.run(
        [str(options.uassetgui), '--portable', *map(str, command)],
        env=env, check=True,
    )

for asset, times in shredders.items():
    source = originals / f'{asset}.uasset'
    source.parent.mkdir(parents=True, exist_ok=True)
    for extension in ('.uasset', '.uexp'):
        with source.with_suffix(extension).open('wb') as file:
            subprocess.run(
                [str(options.repak), 'get', str(options.game_pak), asset + extension],
                stdout=file, check=True,
            )

    data_file = work / f'{source.stem}.json'
    uassetgui('tojson', source, data_file, 'VER_UE4_27')
    data = json.loads(data_file.read_text(encoding='utf-8-sig'))
    converter = next(
        export for export in data['Exports']
        if export['ObjectName'] == 'ItemConverter_GEN_VARIABLE'
    )

    for field, original in zip(
        ('MinPowerUnitProductionTime', 'MaxPowerUnitProductionTime'), times
    ):
        prop = next(item for item in converter['Data'] if item['Name'] == field)
        if prop['Value'] != original:
            raise ValueError(f'{asset}: unexpected {field} value {prop["Value"]}')
        prop['Value'] = original / 5

    edited_file = work / f'{source.stem}.edited.json'
    edited_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
    destination = payload / f'{asset}.uasset'
    destination.parent.mkdir(parents=True, exist_ok=True)
    uassetgui('fromjson', edited_file, destination)
    print(f'{source.stem}: {times} -> {[value / 5 for value in times]}')

metadata = {
    'schema_version': 2,
    'name': 'Faster Shredders',
    'mod_id': 'FasterShredders',
    'author': 'yuexr',
    'version': '1.0.0',
    'description': 'Astroneer mod: 5x processing speed for Medium, Large, and XL Shredders.',
    'sync': 'serverclient',
}
(payload / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')

pak = output / '000-FasterShredders-1.0.0_P.pak'
subprocess.run(
    [str(options.repak), 'pack', str(payload), str(pak), '--version', 'V8B'],
    check=True,
)
print(f'Built {pak}')


