// Build commands — wrap CLI `build_cmd` logic for Tauri

use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct PbgenStatus {
    pub found: bool,
    pub path: String,
    pub version: String,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct BuildResult {
    pub success: bool,
    pub exe_path: String,
    pub exe_size_kb: u64,
    pub mode: String,
    pub log: String,
    pub errors: Vec<String>,
}

/// Check if PBGen.exe is available on this system
#[tauri::command]
pub fn check_pbgen() -> PbgenStatus {
    match find_pbgen(None) {
        Some(path) => {
            // Try to get version
            let version = Command::new(&path)
                .arg("-version")
                .output()
                .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
                .unwrap_or_else(|_| "unknown".to_string());

            PbgenStatus {
                found: true,
                path: path.to_string_lossy().to_string(),
                version,
            }
        }
        None => PbgenStatus {
            found: false,
            path: String::new(),
            version: String::new(),
        },
    }
}

/// Build a PowerBuilder application using PBGen.exe
#[tauri::command]
pub fn build_pb_application(
    pbl_path: String,
    app_name: String,
    mode: String,
    output_dir: String,
    machine_code: bool,
    pbgen_path: Option<String>,
) -> Result<BuildResult, String> {
    let pbl = PathBuf::from(&pbl_path);
    if !pbl.exists() {
        return Err(format!("PBL file not found: {}", pbl_path));
    }

    let pbgen = find_pbgen(pbgen_path.as_deref())
        .ok_or_else(|| {
            "PBGen.exe not found.\n\
            Install PowerBuilder IDE, then add PBGen.exe to PATH.\n\
            Typical location: C:\\Program Files\\Appeon\\PowerBuilder XX.X\\PBGen.exe"
                .to_string()
        })?;

    let out_dir = Path::new(&output_dir);
    std::fs::create_dir_all(out_dir).map_err(|e| e.to_string())?;

    let exe_out = out_dir.join(format!("{}.exe", app_name));
    let lib_list = pbl_path.clone();

    let mut cmd_args: Vec<String> = vec![
        "-l".to_string(),
        lib_list,
        "-a".to_string(),
        app_name.clone(),
        "-e".to_string(),
        exe_out.to_string_lossy().to_string(),
    ];

    if machine_code {
        cmd_args.push("-m".to_string());
    }

    // Compute PBD flags for mode
    match mode.as_str() {
        "exe" => cmd_args.push("-p".to_string()),
        "exe+pbd" => {
            cmd_args.push("-p".to_string());
            cmd_args.push("y".to_string());
        }
        _ => {}
    }

    let result = Command::new(&pbgen)
        .args(&cmd_args)
        .output()
        .map_err(|e| format!("Cannot execute PBGen: {}", e))?;

    let stdout = String::from_utf8_lossy(&result.stdout).to_string();
    let stderr = String::from_utf8_lossy(&result.stderr).to_string();

    let mut log = String::new();
    log.push_str(&format!("Command: {} {}\n", pbgen.display(), cmd_args.join(" ")));
    if !stdout.is_empty() {
        log.push_str("=== stdout ===\n");
        log.push_str(&stdout);
    }
    if !stderr.is_empty() {
        log.push_str("=== stderr ===\n");
        log.push_str(&stderr);
    }

    if !result.status.success() {
        let code = result.status.code().unwrap_or(-1);
        return Err(format!("PBGen exited with code {}\n{}", code, log));
    }

    let exe_size_kb = exe_out
        .metadata()
        .map(|m| m.len() / 1024)
        .unwrap_or(0);

    Ok(BuildResult {
        success: true,
        exe_path: exe_out.to_string_lossy().to_string(),
        exe_size_kb,
        mode: mode.clone(),
        log,
        errors: vec![],
    })
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn find_pbgen(explicit: Option<&str>) -> Option<PathBuf> {
    if let Some(path) = explicit {
        let p = PathBuf::from(path);
        if p.exists() {
            return Some(p);
        }
    }

    // Check PATH via 'where'
    if let Ok(output) = Command::new("where").arg("PBGen.exe").output() {
        if output.status.success() {
            let line = String::from_utf8_lossy(&output.stdout);
            let first = line.lines().next().unwrap_or("").trim();
            if !first.is_empty() {
                return Some(PathBuf::from(first));
            }
        }
    }

    // Common install locations (Windows)
    for base in &[
        r"C:\Program Files\Appeon",
        r"C:\Program Files (x86)\Appeon",
        r"C:\Program Files\Sybase",
        r"C:\Program Files (x86)\Sybase",
    ] {
        let base_p = PathBuf::from(base);
        if base_p.is_dir() {
            if let Ok(entries) = std::fs::read_dir(&base_p) {
                for entry in entries.flatten() {
                    let candidate = entry.path().join("PBGen.exe");
                    if candidate.exists() {
                        return Some(candidate);
                    }
                }
            }
        }
    }

    None
}
