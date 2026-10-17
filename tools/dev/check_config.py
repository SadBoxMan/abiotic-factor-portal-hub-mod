import sys, os
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))
import lupa
L = lupa.LuaRuntime()
src = open(sys.argv[1], encoding="utf-8").read()
fn = L.eval("""function(s)
  local f, e = load(s)
  if not f then return 'SYNTAX ERROR: ' .. e end
  local t = f()
  local ids = {}
  for k in pairs(t.worlds) do ids[#ids + 1] = k end
  table.sort(ids)
  local out = 'syntax OK; worlds: ' .. table.concat(ids, ', ') .. '; portals:'
  for _, p in ipairs(t.portals) do out = out .. ' ' .. p.slot .. '=' .. p.destination end
  return out
end""")
print(fn(src))
