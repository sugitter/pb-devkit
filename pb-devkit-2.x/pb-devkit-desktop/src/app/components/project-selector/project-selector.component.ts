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
        <h1>PB DevKit 2.0</h1>
        <p>PowerBuilder Legacy System Toolkit</p>
      </div>
      
      <div class="actions">
        <button class="btn-primary" (click)="selectProject()">
          📁 选择项目文件夹
        </button>
        <button class="btn-secondary" (click)="selectPblFile()">
          📄 选择 PBL 文件
        </button>
      </div>

      @if (loading) {
        <div class="loading">正在分析项目...</div>
      }

      @if (projectInfo) {
        <div class="project-info">
          <h2>{{ projectInfo.name }}</h2>
          <p class="path">{{ projectInfo.path }}</p>
          
          @if (projectInfo.pbl_files.length > 0) {
            <div class="file-section">
              <h3>PBL 文件 ({{ projectInfo.pbl_files.length }})</h3>
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
              <h3>EXE/PBD 文件 ({{ projectInfo.exe_files.length }})</h3>
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
      padding: 2rem;
      max-width: 800px;
      margin: 0 auto;
    }
    .header {
      text-align: center;
      margin-bottom: 2rem;
    }
    .header h1 {
      font-size: 2rem;
      color: #333;
      margin-bottom: 0.5rem;
    }
    .header p {
      color: #666;
    }
    .actions {
      display: flex;
      gap: 1rem;
      justify-content: center;
      margin-bottom: 2rem;
    }
    .btn-primary, .btn-secondary {
      padding: 0.75rem 1.5rem;
      border: none;
      border-radius: 6px;
      font-size: 1rem;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-primary {
      background: #2563eb;
      color: white;
    }
    .btn-primary:hover {
      background: #1d4ed8;
    }
    .btn-secondary {
      background: #f3f4f6;
      color: #333;
    }
    .btn-secondary:hover {
      background: #e5e7eb;
    }
    .loading {
      text-align: center;
      padding: 2rem;
      color: #666;
    }
    .project-info {
      background: #f9fafb;
      border-radius: 8px;
      padding: 1.5rem;
    }
    .project-info h2 {
      margin: 0 0 0.5rem;
      color: #111;
    }
    .path {
      color: #666;
      font-size: 0.875rem;
      margin-bottom: 1rem;
    }
    .file-section {
      margin-top: 1rem;
    }
    .file-section h3 {
      font-size: 0.875rem;
      color: #374151;
      margin-bottom: 0.5rem;
    }
    .file-list {
      list-style: none;
      padding: 0;
      margin: 0;
    }
    .file-list li {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem;
      cursor: pointer;
      border-radius: 4px;
    }
    .file-list li:hover {
      background: #e5e7eb;
    }
    .file-size {
      margin-left: auto;
      color: #666;
      font-size: 0.75rem;
    }
    .warning {
      margin-top: 1rem;
      padding: 1rem;
      background: #fef3c7;
      border-radius: 6px;
      color: #92400e;
    }
    .error {
      margin-top: 1rem;
      padding: 1rem;
      background: #fee2e2;
      border-radius: 6px;
      color: #dc2626;
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
        filters: [{ name: 'PBL Files', extensions: ['pbl', 'pbd'] }],
        title: '选择 PBL 文件'
      });

      if (selected) {
        this.pblSelected.emit(selected as string);
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