# Check Lua files for syntax errors with a real Lua (lupa) before installing them in the game.
#   python tools\dev\lua_syntax_check.py mod\PortalHub\Scripts\main.lua mod\PortalMaterialLab\Scripts\main.lua
# lupa: pip install lupa   (or pip install --target %TEMP%\pylib lupa, which this script also looks in)
import os, sys
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))
import lupa

check = lupa.LuaRuntime().eval("function(s) local f, e = load(s); return e end")
bad = 0
for path in sys.argv[1:]:
    err = check(open(path, encoding="utf-8").read())
    print(("syntax OK   " if err is None else "SYNTAX ERROR ") + path + ("" if err is None else ": " + err))
    bad += err is not None
sys.exit(1 if bad else 0)
