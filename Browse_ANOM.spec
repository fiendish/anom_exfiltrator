# -*- mode: python -*-

block_cipher = None


a = Analysis(['Browse_ANOM.py'],
             pathex=['/home/avi/anom_exfiltrator'],
             binaries=None,
             datas=[('loading.gif','.')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='Browse_ANOM',
          debug=False,
          strip=False,
          upx=True,
          console=True )