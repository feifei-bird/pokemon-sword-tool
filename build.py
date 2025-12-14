import PyInstaller.__main__
import os

PyInstaller.__main__.run([
    'Pokemon.py',
    '--onefile',
    '--windowed',
    '--icon=app.ico',  # 如果有图标文件的话
    '--name=宝可梦剑工具',
    '--add-data=ItemData.txt;.',
    '--add-data=pokemon_internal_id_name.json;.',
    '--add-data=pokemon_ability.json;.',
    '--add-data=pokemon_move.json;.',
    '--add-data=pokemon_move_explanation.json;.',
    '--add-data=pokemon_ability_explanation.json;.',
    '--add-data=item_category_rules.json;.',
    '--add-data=pokemon_types_final.json;.',
    '--add-data=pokemon_abilities_final.json;.',
    '--add-data=type_exclusive_function.py;.'
])
