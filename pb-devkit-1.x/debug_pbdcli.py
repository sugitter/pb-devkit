"""Debug PbdCli entry parsing for datasync.pbl."""
import sys, os, struct

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "thirdparty", "PbdCli"))

# Direct binary inspection of datasync.pbl
pbl_path = r"F:\workspace\X6\3.5\datasync\datasync.pbl"
with open(pbl_path, "rb") as f:
    data = f.read()

print(f"File size: {len(data)} bytes")

# Find HDR*
pos = 0
while pos + 512 <= len(data):
    block = data[pos:pos + 512]
    if block[:4] == b"HDR*":
        # Try ANSI
        if block[4:16] == b"PowerBuilder":
            ver = block[18:22]
            print(f"HDR* at {pos}, ANSI, version: {ver}")
        # Try Unicode
        try:
            pb_str = block[4:28].decode("utf-16-le")
            ver_str = block[32:40].decode("utf-16-le")
            print(f"HDR* at {pos}, Unicode, PowerBuilder, version: {ver_str}")
        except:
            pass
        break
    pos += 512

# Find first NOD*
# For Unicode PB10+, NOD* is at HDR* offset + 1536
# For ANSI, at HDR* offset + 1024
if pos < len(data):
    # Try unicode first
    nod_offset = pos + 1536
    for try_offset in [nod_offset, pos + 1024]:
        if try_offset + 512 <= len(data):
            block = data[try_offset:try_offset + 512]
            if block[:4] == b"NOD*":
                print(f"NOD* found at {try_offset}")
                # Read entry count
                entry_count = struct.unpack_from("<H", block, 20)[0]
                print(f"Entry count: {entry_count}")
                
                # Parse first few entries
                current = try_offset + 32
                char_size = 2  # Unicode
                header_size = 4 + char_size * 4  # 12
                total_header_size = header_size + 16  # 28
                
                for i in range(min(entry_count, 5)):
                    hdr = data[current:current + total_header_size]
                    if hdr[:4] != b"ENT*":
                        print(f"  Entry {i}: NOT ENT* at {current}, got {hdr[:4]}")
                        break
                    
                    # Decode version string
                    ver_bytes = hdr[4:4 + char_size * 4]
                    ver_str = ver_bytes.decode("utf-16-le", errors="replace")
                    
                    data_start = struct.unpack_from("<I", hdr, header_size)[0]
                    data_size = struct.unpack_from("<I", hdr, header_size + 4)[0]
                    name_len = struct.unpack_from("<H", hdr, header_size + 14)[0]
                    
                    print(f"  Entry {i}: ver={ver_str}, offset={data_start}, size={data_size}, name_len={name_len}")
                    
                    # Read name
                    name_buf = data[current + total_header_size:current + total_header_size + name_len]
                    name = name_buf[:name_len - char_size].decode("utf-16-le", errors="replace")
                    print(f"    name: {name}")
                    
                    current = current + total_header_size + name_len
                
                break
            else:
                print(f"No NOD* at {try_offset}, got: {block[:4]}")
