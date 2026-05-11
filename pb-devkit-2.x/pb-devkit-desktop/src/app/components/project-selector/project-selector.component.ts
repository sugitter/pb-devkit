import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { open } from '@tauri-apps/plugin-dialog';
import { PblService, ProjectInfo, PblFileInfo } from '../../services/pbl.service';

@Component({
  selector: 'app-project-selector',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="project-selector">
      <div class="header">
        <h1>⚡ PB DevKit 2.0</h1>
        <p class="subtitle">PowerBuilder Legacy System Toolkit</p>
      </div>

      <div class="actions">
        <button class="btn-primary" (click)="selectProject()">
          📁 选择项目文件夹
        </button>
        <button class="btn-secondary" (click)="selectPblFile()">
          📄 选择 PBL/PBD 文件
        </button>
        <button class="btn-secondary" (click)="selectExeFile()">
          ⚙️ 选择 EXE/DLL 文件
        </button>
      </div>

      @if (loading) {
        <div class="loading">
          <div class="spinner"></div>
          <span>正在分析项目...</span>
        </div>
      }

      @if (projectInfo) {
        <div class="project-info">
          <h2>{{ projectInfo.name }}</h2>
          <p class="path" [title]="projectInfo.path">{{ projectInfo.path }}</p>

          @if (projectInfo.pbl_files.length > 0) {
            <div class="file-section">
              <h3>📦 PBL 文件 ({{ projectInfo.pbl_files.length }})</h3>
              <ul class="file-list">
                @for (pbl of projectInfo.pbl_files; track pbl.path) {
                  <li (click)="selectPbl(pbl)">
                    <span class="file-icon">📦</span>
                    <span class="file-name">{{ pbl.name }}</span>
                    <span class="file-size">{{ formatSize(pbl.size) }}</span>
                  </li>
                }
              </ul>
            </div>
          }

          @if (projectInfo.exe_files.length > 0) {
            <div class="file-section">
              <h3>⚙️ EXE/PBD 文件 ({{ projectInfo.exe_files.length }})</h3>
              <ul class="file-list">
                @for (exe of projectInfo.exe_files; track exe) {
                  <li (click)="selectExe(exe)">
                    <span class="file-icon">⚙️</span>
                    <span class="file-name">{{ getFileName(exe) }}</span>
                  </li>
                }
              </ul>
            </div>
          }

          @if (!projectInfo.is_valid) {
            <div class="warning">
              ⚠️ 未检测到有效的 PowerBuilder 项目文件
            </div>
          }
        </div>
      }

      @if (error) {
        <div class="error">{{ error }}</div>
      }
    </div>
  `,
  styles: [`
    .project-selector {
      display: flex;
      flex-direction: column;
      height: 100%;
      padding: 1rem;
      overflow-y: auto;
    }
    .header {
      text-align: center;
      margin-bottom: 1.5rem;
    }
    .header h1 {
      font-size: 1.25rem;
      color: #111;
      margin: 0 0 0.25rem;
    }
    .subtitle {
      color: #6b7280;
      font-size: 0.8rem;
      margin: 0;
    }
    .actions {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      margin-bottom: 1rem;
    }
    .btn-primary, .btn-secondary {
      padding: 0.6rem 1rem;
      border: none;
      border-radius: 6px;
      font-size: 0.85rem;
      cursor: pointer;
      transition: background 0.15s;
      width: 100%;
      text-align: left;
    }
    .btn-primary {
      background: #2563eb;
      color: white;
    }
    .btn-primary:hover { background: #1d4ed8; }
    .btn-secondary {
      background: #f3f4f6;
      color: #374151;
      border: 1px solid #d1d5db;
    }
    .btn-secondary:hover { background: #e5e7eb; }
    .loading {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 1rem;
      justify-content: center;
      color: #6b7280;
      font-size: 0.85rem;
    }
    .spinner {
      width: 16px; height: 16px;
      border: 2px solid #e5e7eb;
      border-top-color: #3b82f6;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .project-info {
      background: #f9fafb;
      border-radius: 6px;
      padding: 0.75rem;
    }
    .project-info h2 {
      margin: 0 0 0.25rem;
      font-size: 0.95rem;
      color: #111;
    }
    .path {
      color: #6b7280;
      font-size: 0.75rem;
      margin: 0 0 0.5rem;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .file-section { margin-top: 0.75rem; }
    .file-section h3 {
      font-size: 0.8rem;
      color: #374151;
      margin: 0 0 0.4rem;
    }
    .file-list {
      list-style: none;
      padding: 0;
      margin: 0;
    }
    .file-list li {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.4rem 0.5rem;
      cursor: pointer;
      border-radius: 4px;
      font-size: 0.8rem;
    }
    .file-list li:hover { background: #e5e7eb; }
    .file-size {
      margin-left: auto;
      color: #9ca3af;
      font-size: 0.7rem;
    }
    .warning {
      margin-top: 0.75rem;
      padding: 0.6rem;
      background: #fef3c7;
      border-radius: 6px;
      color: #92400e;
      font-size: 0.8rem;
    }
    .error {
      margin-top: 0.75rem;
      padding: 0.6rem;
      background: #fee2e2;
      border-radius: 6px;
      color: #dc2626;
      font-size: 0.8rem;
    }
  `]
})
export class ProjectSelectorComponent {
  @Output() pblSelected = new EventEmitter<string>();
  @Output() exeSelected = new EventEmitter<string>();
  @Output() projectDetected = new EventEmitter<ProjectInfo>();

  projectInfo: ProjectInfo | null = null;
  loading = false;
  error = '';

  constructor(private pblService: PblService) {}

  async selectProject() {
    try {
      const selected = await open({
        directory: true,
        multiple: false,
        title: '选择 PowerBuilder 项目文件夹'
      });

      if (selected) {
        this.loading = true;
        this.error = '';
        this.projectInfo = await this.pblService.detectProject(selected as string);
        this.projectDetected.emit(this.projectInfo);
      }
    } catch (e: any) {
      this.error = e.message || '选择项目失败';
    } finally {
      this.loading = false;
    }
  }

  async selectPblFile() {
    try {
      const selected = await open({
        multiple: false,
        filters: [{ name: 'PBL/PBD Files', extensions: ['pbl', 'pbd'] }],
        title: '选择 PBL 文件'
      });

      if (selected) {
        this.pblSelected.emit(selected as string);
      }
    } catch (e: any) {
      this.error = e.message || '选择文件失败';
    }
  }

  async selectExeFile() {
    try {
      const selected = await open({
        multiple: false,
        filters: [{ name: 'EXE/DLL Files', extensions: ['exe', 'dll'] }],
        title: '选择 EXE/DLL 文件'
      });

      if (selected) {
        this.exeSelected.emit(selected as string);
      }
    } catch (e: any) {
      this.error = e.message || '选择文件失败';
    }
  }

  selectPbl(pbl: PblFileInfo) {
    this.pblSelected.emit(pbl.path);
  }

  selectExe(exe: string) {
    this.exeSelected.emit(exe);
  }

  formatSize(bytes: number): string {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  getFileName(path: string): string {
    return path.split(/[\\/]/).pop() || path;
  }
}
