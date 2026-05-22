"""Test PBSpyORCA export of datasync.pbl windows."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
orca_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "orca"))
os.add_dll_directory(orca_dir)
os.environ["PATH"] = orca_dir + ";" + os.environ.get("PATH", "")

from pb_devkit.pborca_engine import PBORCAEngine, find_dll, is_available

print("DLL found:", find_dll())
print("Available:", is_available())

# Test with datasync.pbl
pbl = r"F:\workspace\X6\3.5\datasync\datasync.pbl"
print(f"\nOpening {pbl}...")
engine = PBORCAEngine(pb_version=120)  # PB12
try:
    engine.session_open()
    print("Session opened!")

    # List directory
    entries = engine.library_directory(pbl)
    print(f"\nEntries ({len(entries)}):")
    for name, tc, comment in entries:
        c = comment[:50] if comment else ""
        print(f"  {name} (type={tc}) {c}")

    # Try exporting w_datasync_setup
    print("\n" + "=" * 60)
    print("Exporting w_datasync_setup (window)...")
    print("=" * 60)
    src = engine.export_entry(pbl, "w_datasync_setup", 2)  # type 2 = window
    print(src[:3000])
    if len(src) > 3000:
        print(f"... ({len(src)} total chars)")

    # Try exporting w_icontray
    print("\n" + "=" * 60)
    print("Exporting w_icontray (window)...")
    print("=" * 60)
    src2 = engine.export_entry(pbl, "w_icontray", 2)
    print(src2[:3000])
    if len(src2) > 3000:
        print(f"... ({len(src2)} total chars)")

except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
finally:
    engine.session_close()
