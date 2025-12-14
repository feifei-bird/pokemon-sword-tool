# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['Pokemon.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app.ico', '.'),
        ('file_manager.py', '.'),
        ('type_exclusive_function.py', '.'),
        ('pokemon_class.py', '.'),
        ('pokemon_home.py', '.'),
        ('ccb.py', '.'),
        ('analyze_pk8.py', '.'),
        ('decrypt_main.py', '.'),
        ('config/ItemData.txt', 'config'),
        ('config/ItemDataAll.txt', 'config'),
        ('config/pokemon_internal_id_name.json', 'config'),
        ('config/pokemon_ability.json', 'config'),
        ('config/pokemon_move.json', 'config'),
        ('config/pokemon_move_explanation.json', 'config'),
        ('config/pokemon_ability_explanation.json', 'config'),
        ('config/item_category_rules.json', 'config'),
        ('config/pokemon_types_final.json', 'config'),
        ('config/pokemon_abilities_final.json', 'config'),
        ('config/pokemon_item_name.json', 'config'),
        ('config/pokemon_location.json', 'config'),
        ('config/pokemon_main_info.json', 'config')
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='宝可梦剑工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app.ico'],
)
