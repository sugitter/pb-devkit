import { Component, EventEmitter, Output, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { invoke } from '@tauri-apps/api/core';
import { open } from '@tauri-apps/plugin-dialog';

@Component({
  selector: 'app-diff-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="diff-panel">
      <div class="header">
        <h2><span class="material-icons" style="vertical-align:middle">compare</span> 代码对比</h2>
        <button class="btn-close" (click)="close.emit()">
          <span class="material-icons">close</span>
        </button>
      </div>

      <div class="file-selector">
        <div class="file-input">
          <label>文件/目录 1:</label>
          <input type="text" [(ngModel)]="path1" readonly placeholder="选择第一个文件或目录">
          <button class="btn-browse" (click)="browseFile(1)">
            <span class="material-icons">folder_open</span>
          </button>
        </div>
        <div class="file-input">
          <label>文件/目录 2:</label>
          <input type="text" [(ngModel)]="path2" readonly placeholder="选择第二个文件或目录">
          <button class="btn-browse" (click)="browseFile(2)">
            <span class="material-icons">folder_open</span>
          </button>
        </div>
        <button class="btn-primary" (click)="runDiff()" [disabled]="!path1 || !path2">
          <span class="material-icons">play_arrow</span> 执行对比
        </button>
      </div>

      @if (loading) {
        <div class="loading">
          <div class="spinner"></div>
          <span>正在对比...</span>
        </div>
      }

      @if (result) {
        <div class="result">
          <pre>{{ result }}</pre>
        </div>
      }

      @if (error) {
        <div class="error">
          <span class="material-icons">error</span> {{ error }}
        </div>
      }
    </div>
  `,
  styles: [`
    .diff-panel {
      padding: 20px;
      height: 100%;
      display: flex;
      flex-direction: column;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }
    .header h2 {
      margin: 0;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .file-selector {
      display: flex;
      flex-direction: column;
      gap: 12px;
      margin-bottom: 20px;
    }
    .file-input {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .file-input label {
      min-width: 100px;
      font-weight: 500;
    }
    .file-input input {
      flex: 1;
      padding: 8px 12px;
      border: 1px solid #ddd;
      border-radius: 4px;
      background: #fafafa;
    }
    .btn-browse {
      padding: 8px 12px;
      background: #f5f5f5;
      border: 1px solid #ddd;
      border-radius: 4px;
      cursor: pointer;
    }
    .btn-browse:hover {
      background: #eee;
    }
    .btn-primary {
      padding: 10px 20px;
      background: #7c3aed;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .btn-primary:disabled {
      background: #ccc;
      cursor: not-allowed;
    }
    .btn-close {
      background: none;
      border: none;
      cursor: pointer;
      padding: 4px;
    }
    .result {
      flex: 1;
      overflow: auto;
      background: #1e1e1e;
      color: #d4d4d4;
      padding: 16px;
      border-radius: 4px;
    }
    .result pre {
      margin: 0;
      white-space: pre-wrap;
      font-family: 'Consolas', monospace;
      font-size: 13px;
    }
    .loading {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 20px;
      color: #666;
    }
    .spinner {
      width: 20px;
      height: 20px;
      border: 2px solid #f3f3f3;
      border-top: 2px solid #7c3aed;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }
    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
    .error {
      padding: 12px;
      background: #fee;
      color: #c00;
      border-radius: 4px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
  `]
})
export class DiffPanelComponent implements OnInit {
  @Output() close = new EventEmitter<void>();

  path1 = '';
  path2 = '';
  result = '';
  error = '';
  loading = false;

  ngOnInit() {}

  async browseFile(num: 1 | 2) {
    try {
      const selected = await open({
        multiple: false,
        directory: true
      });
      if (selected) {
        if (num === 1) this.path1 = selected as string;
        else this.path2 = selected as string;
      }
    } catch (e) {
      this.error = String(e);
    }
  }

  async runDiff() {
    if (!this.path1 || !this.path2) return;

    this.loading = true;
    this.error = '';
    this.result = '';

    try {
      const result = await invoke<string>('run_diff', {
        args: [this.path1, this.path2]
      });
      this.result = result;
    } catch (e) {
      this.error = String(e);
    } finally {
      this.loading = false;
    }
  }
}