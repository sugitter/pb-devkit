// pbl_writer.rs — Pure-Rust PowerBuilder Library Writer
//
// Creates valid .pbl binary files from source entries.
// NO Python dependency, NO PBORCA DLL required.
//
// Format (verified against PbdViewer + chunk_engine.py):
//   HDR*  (512B ANSI / 1024B Unicode)  — library header
//   FRE*  (512B)                        — free-block sentinel
//   NOD*  (3072B, 6 × 512B)            — B-tree node(s) containing ENT* entries
//   DAT*  (512B per block, chained)    — data blocks for each entry
//
// ENT* header layout:
//   ANSI:    ENT*(4) + ver(4) + offset(4) + size(4) + ts(4) + pad(2) + name_len(2) = 24B
//   Unicode: ENT*(4) + ver(8) + offset(4) + size(4) + ts(4) + pad(2) + name_len(2) = 28B
//
// After ENT* header: [name_buf bytes] → next ENT*

use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use crate::pbl::SOURCE_EXT_MAP;

// ─── Constants ─────────────────────────────────────────────────────────

const BLOCK_SIZE: usize = 512;
const NODE_BLOCK_SIZE: usize = 3072; // 6 × 512
const MAX_DATA_PER_BLOCK: usize = 502;
const ENTRIES_PER_NODE: usize = 40;

// Version constants for ENT* entries
const VERSION_ANSI: &[u8; 4] = b"0600";
const VERSION_UNICODE_FULL: &[u8; 8] = &[
    b'1', 0x00, b'2', 0x00, b'5', 0x00, b'0', 0x00,
]; // "1250" in UTF-16LE

// ─── Config types ──────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum PblEncoding {
    Ansi,
    Unicode,
}

impl PblEncoding {
    pub fn is_unicode(&self) -> bool {
        *self == PblEncoding::Unicode
    }
}

// ─── Internal entry representation ─────────────────────────────────────

struct PblWriterEntry {
    name: String,
    _obj_type: u8, // Reserved for future PB object type validation
    data: Vec<u8>,
    timestamp: u32,
}

impl PblWriterEntry {
    fn encoded_name_ansi(&self) -> Vec<u8> {
        self.name.as_bytes().to_vec()
    }

    fn encoded_name_unicode(&self) -> Vec<u8> {
        self.name.encode_utf16()
            .flat_map(|c| c.to_le_bytes())
            .collect()
    }

    fn name_buf(&self, is_unicode: bool) -> Vec<u8> {
        let mut buf = if is_unicode {
            self.encoded_name_unicode()
        } else {
            self.encoded_name_ansi()
        };
        if is_unicode {
            buf.extend_from_slice(&[0x01, 0x00]); // UNICODE ver_suffix
        } else {
            buf.push(0x01); // ANSI ver_suffix
        }
        buf
    }
}

// ─── Public API ────────────────────────────────────────────────────────

/// Builds a valid PBL binary from in-memory entries.
pub struct PblWriter {
    pb_version: u32,
    encoding: PblEncoding,
    entries: Vec<PblWriterEntry>,
}

impl PblWriter {
    pub fn new(pb_version: u32, encoding: PblEncoding) -> Self {
        PblWriter {
            pb_version,
            encoding,
            entries: Vec::new(),
        }
    }

    /// Add a named PB object entry with raw bytes.
    pub fn add_entry(
        &mut self,
        name: &str,
        obj_type: u8,
        data: Vec<u8>,
        timestamp: Option<u32>,
    ) {
        let ts = timestamp.unwrap_or_else(|| now_unix());
        let name_lower = name.to_lowercase();
        if self.entries.iter().any(|e| e.name.to_lowercase() == name_lower) {
            return; // Skip duplicates
        }
        self.entries.push(PblWriterEntry {
            name: name.to_string(),
            _obj_type: obj_type,
            data,
            timestamp: ts,
        });
    }

    /// Add a source file by path, auto-detecting type from extension.
    /// Returns true on success.
    pub fn add_source_file(&mut self, path: &Path) -> bool {
        if !path.exists() || !path.is_file() {
            return false;
        }
        let ext = path.extension()
            .and_then(|e| e.to_str())
            .map(|e| format!(".{}", e.to_lowercase()))
            .unwrap_or_default();
        let obj_type = match SOURCE_EXT_MAP.iter().find(|(e, _)| *e == ext.as_str()) {
            Some((_, t)) => *t,
            None => return false,
        };
        let ts = file_mtime(path).unwrap_or_else(now_unix);
        let raw = match fs::read(path) {
            Ok(b) => b,
            Err(_) => return false,
        };
        let data = self.encode_source_bytes(&raw);
        let name = path.file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("unknown.srw");
        self.add_entry(name, obj_type, data, Some(ts));
        true
    }

    /// Add all supported source files from a directory.
    /// Returns count of files added.
    pub fn add_source_directory(&mut self, dir: &Path, recursive: bool) -> usize {
        if !dir.is_dir() {
            return 0;
        }
        let mut added = 0;
        let mut files: Vec<PathBuf> = Vec::new();
        collect_source_files(dir, recursive, &mut files);
        // Sort for deterministic output
        files.sort();
        for f in &files {
            if self.add_source_file(f) {
                added += 1;
            }
        }
        added
    }

    /// Write the PBL binary to disk. Returns file size in bytes.
    /// Errors if no entries have been added.
    pub fn write(&self, output_path: &Path) -> Result<usize, String> {
        if self.entries.is_empty() {
            return Err("No entries to write — add entries first.".to_string());
        }
        if let Some(parent) = output_path.parent() {
            fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }
        let bytes = self.to_bytes()?;
        let size = bytes.len();
        fs::write(output_path, &bytes).map_err(|e| e.to_string())?;
        Ok(size)
    }

    /// Return the PBL binary as bytes without writing to disk.
    pub fn to_bytes(&self) -> Result<Vec<u8>, String> {
        if self.entries.is_empty() {
            return Err("No entries to write.".to_string());
        }
        let mut buf = Vec::new();
        self.build(&mut buf);
        Ok(buf)
    }

    /// Number of entries added.
    pub fn entry_count(&self) -> usize {
        self.entries.len()
    }

    // ─── Internal build logic ───────────────────────────────────────

    fn is_unicode(&self) -> bool {
        self.encoding.is_unicode()
    }

    fn encode_source_bytes(&self, raw: &[u8]) -> Vec<u8> {
        if raw.len() >= 2 {
            if raw[..2] == [0xFF, 0xFE] {
                // UTF-16LE BOM
                if self.is_unicode() {
                    return raw[2..].to_vec();
                } else {
                    let text = decode_utf16le(&raw[2..]);
                    return text.into_bytes(); // Latin-1 approximation
                }
            }
            if raw[..2] == [0xFE, 0xFF] {
                // UTF-16BE
                let text = decode_utf16be(&raw[2..]);
                if self.is_unicode() {
                    return encode_utf16le(&text);
                } else {
                    return text.into_bytes();
                }
            }
        }
        // Assume UTF-8 / ASCII / Latin-1
        let text = String::from_utf8(raw.to_vec())
            .unwrap_or_else(|_| String::from_utf8_lossy(raw).into_owned());
        if self.is_unicode() {
            encode_utf16le(&text)
        } else {
            text.into_bytes()
        }
    }

    fn build(&self, buf: &mut Vec<u8>) {
        let hdr_size = if self.is_unicode() { 1024 } else { 512 };
        let node_count = (self.entries.len() + ENTRIES_PER_NODE - 1).max(1) / ENTRIES_PER_NODE;
        let dat_start = hdr_size + BLOCK_SIZE + node_count * NODE_BLOCK_SIZE;

        // Calculate DAT* offsets per entry
        let mut entry_offsets: Vec<usize> = Vec::with_capacity(self.entries.len());
        let mut cur = dat_start;
        for e in &self.entries {
            entry_offsets.push(cur);
            let block_count = ((e.data.len() + MAX_DATA_PER_BLOCK - 1) / MAX_DATA_PER_BLOCK).max(1);
            cur += block_count * BLOCK_SIZE;
        }

        self.write_hdr(buf, hdr_size);
        self.write_fre(buf);

        for node_idx in 0..node_count {
            let start = node_idx * ENTRIES_PER_NODE;
            let end = (start + ENTRIES_PER_NODE).min(self.entries.len());
            self.write_nod(buf, &self.entries[start..end], &entry_offsets[start..end]);
        }

        for e in &self.entries {
            self.write_dat_chain(buf, &e.data);
        }

        // Final 512B alignment
        let rem = buf.len() % BLOCK_SIZE;
        if rem != 0 {
            buf.resize(buf.len() + BLOCK_SIZE - rem, 0);
        }
    }

    fn write_hdr(&self, buf: &mut Vec<u8>, hdr_size: usize) {
        let mut block = vec![0u8; hdr_size];
        block[0..4].copy_from_slice(b"HDR*");

        if self.is_unicode() {
            // Unicode PBL header: "PowerBuilder Library\0" in UTF-16LE
            let lib_name = "PowerBuilder Library\0";
            let name_encoded = encode_utf16le(lib_name);
            let name_len = name_encoded.len();
            block[4..4 + name_len].copy_from_slice(&name_encoded);

            // Version string e.g. "1200\0" in UTF-16LE
            let ver_str = format!("{}00\0", self.pb_version);
            let ver_encoded = encode_utf16le(&ver_str);
            let ver_offset = 4 + name_len;
            let ver_end = (ver_offset + ver_encoded.len()).min(hdr_size - 8);
            block[ver_offset..ver_end].copy_from_slice(&ver_encoded[..ver_end - ver_offset]);
        } else {
            // ANSI PBL header
            let lib_name = b"PowerBuilder Library\0";
            let name_len = lib_name.len();
            block[4..4 + name_len].copy_from_slice(lib_name);

            let ver_str = format!("0{}00\0", self.pb_version);
            let ver_bytes = ver_str.as_bytes();
            let ver_offset = 4 + name_len;
            let ver_end = (ver_offset + ver_bytes.len()).min(hdr_size - 8);
            block[ver_offset..ver_end].copy_from_slice(&ver_bytes[..ver_end - ver_offset]);
        }

        // Entry count at hdr_size - 8
        let count = self.entries.len() as u32;
        block[hdr_size - 8..hdr_size - 4].copy_from_slice(&count.to_le_bytes());

        buf.extend_from_slice(&block);
    }

    fn write_fre(&self, buf: &mut Vec<u8>) {
        let mut block = vec![0u8; BLOCK_SIZE];
        block[0..4].copy_from_slice(b"FRE*");
        buf.extend_from_slice(&block);
    }

    fn write_nod(
        &self,
        buf: &mut Vec<u8>,
        entries: &[PblWriterEntry],
        offsets: &[usize],
    ) {
        let mut block = vec![0u8; NODE_BLOCK_SIZE];

        block[0..4].copy_from_slice(b"NOD*");
        // right_sibling = 0 at offset 12
        // entry_count at offset 20
        let count = entries.len() as u16;
        block[20..22].copy_from_slice(&count.to_le_bytes());
        let mut pos = 32;

        let is_uni = self.is_unicode();

        for (e, &dat_offset) in entries.iter().zip(offsets.iter()) {
            let name_buf = e.name_buf(is_uni);
            let name_buf_len = name_buf.len();

            let (ver_bytes, ent_hdr_size) = if is_uni {
                (&VERSION_UNICODE_FULL[..], 28usize)
            } else {
                (&VERSION_ANSI[..], 24usize)
            };

            let total_ent_size = ent_hdr_size + name_buf_len;
            if pos + total_ent_size > NODE_BLOCK_SIZE {
                break;
            }

            let num2 = 4 + if is_uni { 8 } else { 4 }; // = 4 + num*4

            // ENT* magic
            block[pos..pos + 4].copy_from_slice(b"ENT*");
            // Version bytes
            let ver_start = pos + 4;
            block[ver_start..ver_start + ver_bytes.len()].copy_from_slice(ver_bytes);
            // Fixed fields
            block[pos + num2..pos + num2 + 4].copy_from_slice(&(dat_offset as u32).to_le_bytes());
            block[pos + num2 + 4..pos + num2 + 8].copy_from_slice(&(e.data.len() as u32).to_le_bytes());
            block[pos + num2 + 8..pos + num2 + 12].copy_from_slice(&e.timestamp.to_le_bytes());
            // 2 bytes padding at num2+12/num2+13 — leave zero
            block[pos + num2 + 14..pos + num2 + 16].copy_from_slice(&(name_buf_len as u16).to_le_bytes());

            pos += ent_hdr_size;
            block[pos..pos + name_buf_len].copy_from_slice(&name_buf);
            pos += name_buf_len;
        }

        buf.extend_from_slice(&block);
    }

    fn write_dat_chain(&self, buf: &mut Vec<u8>, data: &[u8]) {
        let total = data.len();
        let mut offset = 0;
        let mut block_indices: Vec<usize> = Vec::new();

        let base = buf.len();

        // Write blocks first
        while offset < total {
            let chunk_len = MAX_DATA_PER_BLOCK.min(total - offset);
            let mut block = vec![0u8; BLOCK_SIZE];
            block[0..4].copy_from_slice(b"DAT*");
            // next_offset placeholder → patched later
            block[8..10].copy_from_slice(&(chunk_len as u16).to_le_bytes());
            block[10..10 + chunk_len].copy_from_slice(&data[offset..offset + chunk_len]);
            block_indices.push(buf.len());
            buf.extend_from_slice(&block);
            offset += chunk_len;
        }

        if block_indices.is_empty() {
            let mut block = vec![0u8; BLOCK_SIZE];
            block[0..4].copy_from_slice(b"DAT*");
            buf.extend_from_slice(&block);
            return;
        }

        // Patch next_offset fields
        for i in 0..block_indices.len() {
            let next_off = if i < block_indices.len() - 1 {
                (base + (i + 1) * BLOCK_SIZE) as u32
            } else {
                0u32
            };
            let idx = block_indices[i];
            buf[idx + 4..idx + 8].copy_from_slice(&next_off.to_le_bytes());
        }
    }
}

// ─── Convenience functions ─────────────────────────────────────────────

/// One-shot: scan a source directory and write a .pbl file.
pub fn pack_directory(
    source_dir: &Path,
    output_pbl: &Path,
    pb_version: u32,
    encoding: PblEncoding,
    recursive: bool,
) -> Result<usize, String> {
    let mut w = PblWriter::new(pb_version, encoding);
    let added = w.add_source_directory(source_dir, recursive);
    if added == 0 {
        return Err("No source files found.".to_string());
    }
    w.write(output_pbl)?;
    Ok(added)
}

/// Pack a PBL tree (output of export_pbl_tree) back into .pbl files.
/// Expects structure: pbl_tree_dir/
///   common.pbl/
///     w_base.srw
///   dw_app.pbl/
///     d_orders.srd
/// Creates one .pbl per subdirectory.
pub fn pack_pbl_tree(
    pbl_tree_dir: &Path,
    output_dir: &Path,
    pb_version: u32,
    encoding: PblEncoding,
) -> Result<Vec<(String, usize)>, String> {
    fs::create_dir_all(output_dir).map_err(|e| e.to_string())?;

    let mut pbl_dirs: Vec<PathBuf> = Vec::new();
    if let Ok(entries) = fs::read_dir(pbl_tree_dir) {
        for entry in entries.flatten() {
            if entry.file_type().map(|t| t.is_dir()).unwrap_or(false) {
                pbl_dirs.push(entry.path());
            }
        }
    }
    pbl_dirs.sort();

    let mut results = Vec::new();
    for pbl_dir in &pbl_dirs {
        let dir_name = pbl_dir.file_name().unwrap_or_default().to_string_lossy();
        let pbl_name = if dir_name.ends_with(".pbl") {
            dir_name.to_string()
        } else {
            format!("{}.pbl", dir_name)
        };
        let mut w = PblWriter::new(pb_version, encoding);
        let added = w.add_source_directory(pbl_dir, false);
        if added == 0 {
            continue;
        }
        w.write(&output_dir.join(&pbl_name))?;
        results.push((pbl_name, added));
    }

    if results.is_empty() {
        return Err("No source files found in PBL tree.".to_string());
    }
    Ok(results)
}

// ─── Helpers ────────────────────────────────────────────────────────────

fn now_unix() -> u32 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as u32
}

fn file_mtime(path: &Path) -> Option<u32> {
    fs::metadata(path)
        .ok()?
        .modified()
        .ok()?
        .duration_since(UNIX_EPOCH)
        .ok()
        .map(|d| d.as_secs() as u32)
}

fn collect_source_files(dir: &Path, recursive: bool, out: &mut Vec<PathBuf>) {
    if let Ok(entries) = fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            let ft = match entry.file_type() {
                Ok(t) => t,
                Err(_) => continue,
            };
            if ft.is_dir() {
                if recursive {
                    let dir_name = path.file_name().unwrap_or_default().to_string_lossy();
                    if dir_name.starts_with('.') || dir_name == "target" || dir_name == "node_modules" {
                        continue;
                    }
                    collect_source_files(&path, true, out);
                }
            } else if ft.is_file() {
                if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
                    let ext_lower = format!(".{}", ext.to_lowercase());
                    if SOURCE_EXT_MAP.iter().any(|(e, _)| *e == ext_lower) {
                        out.push(path);
                    }
                }
            }
        }
    }
}

fn decode_utf16le(data: &[u8]) -> String {
    let mut result = String::new();
    for chunk in data.chunks_exact(2) {
        let ch = u16::from_le_bytes([chunk[0], chunk[1]]);
        if ch == 0 { break; }
        if let Some(c) = char::from_u32(ch as u32) {
            if c != '\0' {
                result.push(c);
            }
        }
    }
    result
}

fn decode_utf16be(data: &[u8]) -> String {
    let mut result = String::new();
    for chunk in data.chunks_exact(2) {
        let ch = u16::from_be_bytes([chunk[0], chunk[1]]);
        if ch == 0 { break; }
        if let Some(c) = char::from_u32(ch as u32) {
            if c != '\0' {
                result.push(c);
            }
        }
    }
    result
}

fn encode_utf16le(text: &str) -> Vec<u8> {
    text.encode_utf16()
        .flat_map(|c| c.to_le_bytes())
        .collect()
}

// ─── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::{NamedTempFile, TempDir};

    // ─── PblWriter basic ───

    #[test]
    fn test_new_writer_empty() {
        let w = PblWriter::new(12, PblEncoding::Unicode);
        assert_eq!(w.entry_count(), 0);
        assert!(w.to_bytes().is_err()); // no entries
    }

    #[test]
    fn test_add_entry_increments_count() {
        let mut w = PblWriter::new(12, PblEncoding::Unicode);
        w.add_entry("w_main.srw", 2, b"// test".to_vec(), None);
        assert_eq!(w.entry_count(), 1);
    }

    #[test]
    fn test_add_entry_dedup_case_insensitive() {
        let mut w = PblWriter::new(12, PblEncoding::Unicode);
        w.add_entry("w_main.srw", 2, b"a".to_vec(), None);
        w.add_entry("W_MAIN.srw", 2, b"b".to_vec(), None); // duplicate
        assert_eq!(w.entry_count(), 1);
    }

    // ─── PBL binary generation ───

    #[test]
    fn test_unicode_pbl_has_hdr_signature() {
        let mut w = PblWriter::new(12, PblEncoding::Unicode);
        w.add_entry("w_main.srw", 2, b"// test window".to_vec(), Some(100000000));
        let data = w.to_bytes().unwrap();
        assert_eq!(&data[0..4], b"HDR*");
        // Unicode: header 1024B, then FRE* at 1024
        assert_eq!(&data[1024..1028], b"FRE*");
    }

    #[test]
    fn test_ansi_pbl_has_hdr_signature() {
        let mut w = PblWriter::new(9, PblEncoding::Ansi);
        w.add_entry("w_main.srw", 2, b"// test".to_vec(), Some(100000000));
        let data = w.to_bytes().unwrap();
        assert_eq!(&data[0..4], b"HDR*");
        // ANSI: header 512B, then FRE* at 512
        assert_eq!(&data[512..516], b"FRE*");
    }

    #[test]
    fn test_unicode_pbl_contains_nod_and_dat() {
        let mut w = PblWriter::new(12, PblEncoding::Unicode);
        w.add_entry("w_main.srw", 2, b"// test window".to_vec(), Some(100000000));
        let data = w.to_bytes().unwrap();
        let text = String::from_utf8_lossy(&data);
        assert!(text.contains("NOD*"), "should contain NOD* block");
        assert!(text.contains("DAT*"), "should contain DAT* block");
    }

    #[test]
    fn test_unicode_pbl_contains_ent() {
        let mut w = PblWriter::new(12, PblEncoding::Unicode);
        w.add_entry("w_main.srw", 2, b"// test".to_vec(), Some(100000000));
        let data = w.to_bytes().unwrap();
        let text = String::from_utf8_lossy(&data);
        assert!(text.contains("ENT*"), "should contain ENT* entry");
    }

    #[test]
    fn test_pbl_size_is_512_aligned() {
        let mut w = PblWriter::new(12, PblEncoding::Unicode);
        w.add_entry("w_main.srw", 2, b"// test".to_vec(), Some(100000000));
        let data = w.to_bytes().unwrap();
        assert_eq!(data.len() % 512, 0, "PBL size must be 512B aligned");
    }

    // ─── File I/O ───

    #[test]
    fn test_write_and_read_back() {
        let mut w = PblWriter::new(12, PblEncoding::Unicode);
        w.add_entry("w_main.srw", 2, b"// test window".to_vec(), Some(100000000));
        let tmp = NamedTempFile::new().unwrap();
        let path = tmp.path();
        w.write(path).unwrap();
        assert!(path.exists());
        let data = fs::read(path).unwrap();
        assert_eq!(&data[0..4], b"HDR*");
    }

    // ─── Source directory scanning ───

    #[test]
    fn test_add_source_directory_finds_files() {
        let dir = TempDir::new().unwrap();
        fs::write(dir.path().join("w_main.srw"), b"// window").unwrap();
        fs::write(dir.path().join("d_emp.srd"), b"// datawindow").unwrap();
        fs::write(dir.path().join("readme.txt"), b"ignored").unwrap();

        let mut w = PblWriter::new(12, PblEncoding::Unicode);
        let added = w.add_source_directory(dir.path(), false);
        assert_eq!(added, 2);
    }

    #[test]
    fn test_add_source_directory_recursive() {
        let dir = TempDir::new().unwrap();
        let sub = dir.path().join("subdir");
        fs::create_dir_all(&sub).unwrap();
        fs::write(dir.path().join("w_main.srw"), b"// main").unwrap();
        fs::write(sub.join("d_sub.srd"), b"// sub").unwrap();

        let mut w = PblWriter::new(12, PblEncoding::Unicode);
        let added = w.add_source_directory(dir.path(), true);
        assert_eq!(added, 2);
    }

    #[test]
    fn test_add_source_directory_skips_dot_dirs() {
        let dir = TempDir::new().unwrap();
        let git_dir = dir.path().join(".git");
        fs::create_dir_all(&git_dir).unwrap();
        fs::write(git_dir.join("hidden.srw"), b"// git").unwrap();

        let mut w = PblWriter::new(12, PblEncoding::Unicode);
        let added = w.add_source_directory(dir.path(), true);
        assert_eq!(added, 0);
    }

    // ─── Encoding handling ───

    #[test]
    fn test_utf16le_bom_stripped_in_unicode_mode() {
        let mut raw = vec![0xFF, 0xFE]; // BOM
        raw.extend_from_slice(b"// test");
        let w = PblWriter::new(12, PblEncoding::Unicode);
        let data = w.encode_source_bytes(&raw);
        // BOM should be stripped, content in UTF-16LE
        assert!(!data.is_empty());
        assert_ne!(&data[..2], &[0xFF, 0xFE]);
    }

    #[test]
    fn test_utf8_source_encodes_to_utf16le() {
        let w = PblWriter::new(12, PblEncoding::Unicode);
        let data = w.encode_source_bytes(b"// test");
        // Should be UTF-16LE: each char takes 2 bytes
        assert!(data.len() >= 14); // "// test" → 7 chars * 2 bytes
    }

    #[test]
    fn test_ansi_mode_keeps_bytes() {
        let w = PblWriter::new(9, PblEncoding::Ansi);
        let data = w.encode_source_bytes(b"// test");
        assert_eq!(data, b"// test");
    }

    // ─── pack_directory convenience ───

    #[test]
    fn test_pack_directory_roundtrip() {
        let dir = TempDir::new().unwrap();
        fs::write(dir.path().join("w_main.srw"), b"// window").unwrap();
        let out = dir.path().join("test.pbl");

        let added = pack_directory(dir.path(), &out, 12, PblEncoding::Unicode, false).unwrap();
        assert_eq!(added, 1);
        assert!(out.exists());
        let data = fs::read(&out).unwrap();
        assert_eq!(&data[0..4], b"HDR*");
        assert!(data.len() % 512 == 0);
    }

    #[test]
    fn test_pack_directory_empty_dir_errors() {
        let dir = TempDir::new().unwrap();
        let out = dir.path().join("empty.pbl");
        let result = pack_directory(dir.path(), &out, 12, PblEncoding::Unicode, false);
        assert!(result.is_err());
    }

    // ─── pack_pbl_tree ───

    #[test]
    fn test_pack_pbl_tree() {
        let tree = TempDir::new().unwrap();
        let common = tree.path().join("common.pbl");
        fs::create_dir_all(&common).unwrap();
        fs::write(common.join("w_base.srw"), b"// base").unwrap();

        let dw = tree.path().join("dw_app.pbl");
        fs::create_dir_all(&dw).unwrap();
        fs::write(dw.join("d_orders.srd"), b"// orders").unwrap();

        let out = tree.path().join("output");
        let results = pack_pbl_tree(tree.path(), &out, 12, PblEncoding::Unicode).unwrap();
        assert_eq!(results.len(), 2);
        assert!(out.join("common.pbl").exists());
        assert!(out.join("dw_app.pbl").exists());
    }

    #[test]
    fn test_pack_pbl_tree_empty() {
        let tree = TempDir::new().unwrap();
        let out = tree.path().join("output");
        let result = pack_pbl_tree(tree.path(), &out, 12, PblEncoding::Unicode);
        assert!(result.is_err());
    }
}
