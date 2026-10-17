# Read-only look at a UE5 IoStore table of contents (.utoc): header, flags, compression methods, and the file list (directory index).
import struct, sys

path = sys.argv[1]
b = open(path, 'rb').read()
magic = b[0:16]
print('magic ok:', magic == b'-==--==--==--==-')
ver, = struct.unpack_from('<B', b, 16)
(hdr_size, entry_count, cblock_count, cblock_size, cm_count, cm_len, cblock_bytes, dir_size, part_count) = struct.unpack_from('<9I', b, 20)
container_id, = struct.unpack_from('<Q', b, 56)
enc_guid = b[64:80]
flags, = struct.unpack_from('<B', b, 80)
seeds_count, = struct.unpack_from('<I', b, 84)
part_size, = struct.unpack_from('<Q', b, 88)
no_hash_count, = struct.unpack_from('<I', b, 96)
print('version', ver, 'header size', hdr_size, 'chunks', entry_count, 'compression blocks', cblock_count, 'block size', cblock_bytes)
print('container id: %016x' % container_id)
print('flags: compressed=%s encrypted=%s signed=%s indexed=%s' % (bool(flags & 1), bool(flags & 2), bool(flags & 4), bool(flags & 8)))
off = hdr_size
off += entry_count * 12          # chunk ids
off += entry_count * 10          # offset/lengths
off += seeds_count * 4           # perfect hash seeds
off += no_hash_count * 4         # chunks without perfect hash
off += cblock_count * cblock_size  # compression blocks
names = []
for i in range(cm_count):
    raw = b[off + i * cm_len: off + (i + 1) * cm_len]
    names.append(raw.split(b'\0')[0].decode('ascii', 'replace'))
off += cm_count * cm_len
print('compression methods:', names or ['(none)'])
if flags & 4:
    hash_size, = struct.unpack_from('<i', b, off); off += 4
    off += hash_size * 2 + cblock_count * 20
if dir_size and not (flags & 2):
    d = b[off: off + dir_size]
    p = 0
    def fstr():
        global p
        n, = struct.unpack_from('<i', d, p); p += 4
        if n == 0: return ''
        if n > 0:
            s = d[p: p + n].split(b'\0')[0].decode('utf-8', 'replace'); p += n
        else:
            s = d[p: p - n * 2].decode('utf-16-le', 'replace').rstrip('\0'); p += -n * 2
        return s
    mount = fstr()
    nd, = struct.unpack_from('<I', d, p); p += 4
    dirs = [struct.unpack_from('<4I', d, p + i * 16) for i in range(nd)]; p += nd * 16
    nf, = struct.unpack_from('<I', d, p); p += 4
    files = [struct.unpack_from('<3I', d, p + i * 12) for i in range(nf)]; p += nf * 12
    ns, = struct.unpack_from('<I', d, p); p += 4
    strings = [fstr() for _ in range(ns)]
    NONE = 0xFFFFFFFF
    out = []
    def walk(di, prefix):
        name, first_child, next_sib, first_file = dirs[di]
        here = prefix + (strings[name] + '/' if name != NONE else '')
        f = first_file
        while f != NONE:
            fn, nxt, _ = files[f]
            out.append(here + strings[fn]); f = nxt
        c = first_child
        while c != NONE:
            walk(c, here); c = dirs[c][2]
    if nd: walk(0, mount)
    print('mount point:', mount, ' files listed:', len(out))
    for x in out: print('   ', x)
else:
    print('directory index:', 'none' if not dir_size else 'encrypted')
