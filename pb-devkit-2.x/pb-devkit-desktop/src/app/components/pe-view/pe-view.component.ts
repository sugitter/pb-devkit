import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

export interface PeInfo {
  is_pb_exe: boolean;
  is_64bit: boolean;
  machine_type: string;
  timestamp: string | null;
  embedded_pbl_count: number;
  resources: Array<{
    name: string;
    offset: number;
    size: number;
    resource_type: string;
  }>;
}

@Component({
  selector: 'app-pe-view',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="pe-view">
      <div class="pe-header">
        <span class="material-icons mi-lg">description</span>
        <h3>PE Analysis / PE 分析</h3>
      </div>

      @if (loading) {
        <div class="loading">
          <span class="material-icons rotating">sync</span>
          <span>Analyzing... / 分析中...</span>
        </div>
      } @else if (error) {
        <div class="error">
          <span class="material-icons">error_outline</span>
          {{ error }}
        </div>
      } @else if (peInfo) {
        <!-- File Info -->
        <div class="section">
          <h4><span class="material-icons">info</span> File Info / 文件信息</h4>
          <div class="info-grid">
            <div class="info-item">
              <span class="label">File Type / 文件类型:</span>
              <span class="value" [class.pb-exe]="peInfo.is_pb_exe">
                {{ peInfo.is_pb_exe ? 'PowerBuilder EXE' : 'EXE' }}
              </span>
            </div>
            <div class="info-item">
              <span class="label">Architecture / 架构:</span>
              <span class="value">{{ peInfo.is_64bit ? 'x64' : 'x86' }}</span>
            </div>
            <div class="info-item">
              <span class="label">Machine Type / 机器类型:</span>
              <span class="value">{{ peInfo.machine_type }}</span>
            </div>
            <div class="info-item">
              <span class="label">Timestamp / 时间戳:</span>
              <span class="value">{{ peInfo.timestamp || 'N/A' }}</span>
            </div>
          </div>
        </div>

        <!-- Resources -->
        <div class="section">
          <h4><span class="material-icons">inventory_2</span> Embedded Resources / 内嵌资源</h4>
          @if (peInfo.resources.length > 0) {
            <div class="resource-count">
              <span class="badge">{{ peInfo.embedded_pbl_count }}</span>
              <span>PBD(s) found / 发现 PBD</span>
            </div>
            <table class="resource-table">
              <thead>
                <tr>
                  <th>Name / 名称</th>
                  <th>Offset / 偏移</th>
                  <th>Size / 大小</th>
                  <th>Type / 类型</th>
                </tr>
              </thead>
              <tbody>
                @for (res of peInfo.resources; track res.name) {
                  <tr>
                    <td>{{ res.name }}</td>
                    <td>0x{{ res.offset.toString(16) }}</td>
                    <td>{{ formatSize(res.size) }}</td>
                    <td><span class="type-badge">{{ res.resource_type }}</span></td>
                  </tr>
                }
              </tbody>
            </table>
          } @else {
            <div class="no-resources">
              <span class="material-icons">check_circle</span>
              <span>No PBD resources embedded / 无内嵌 PBD 资源</span>
            </div>
          }
        </div>

        <!-- Actions -->
        <div class="actions">
          <button class="btn-secondary" (click)="onClose.emit()">
            <span class="material-icons">close</span>
            Close / 关闭
          </button>
          @if (peInfo.resources.length > 0) {
            <button class="btn-primary" (click)="onExtract.emit()">
              <span class="material-icons">download</span>
              Extract PBDs / 提取 PBD
            </button>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .pe-view { padding: 1rem; height: 100%; overflow-y: auto; }
    .pe-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem; color: #1e1e2e; }
    .pe-header h3 { margin: 0; font-size: 1.1rem; }
    .section { margin-bottom: 1.25rem; background: #fafafa; border-radius: 8px; padding: 1rem; }
    .section h4 { margin: 0 0 0.75rem; font-size: 0.9rem; color: #45475a; display: flex; align-items: center; gap: 0.4rem; }
    .section h4 .material-icons { font-size: 18px; color: #7c3aed; }
    .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; }
    .info-item { display: flex; flex-direction: column; gap: 0.15rem; }
    .info-item .label { font-size: 0.75rem; color: #6c7086; }
    .info-item .value { font-size: 0.85rem; color: #1e1e2e; font-weight: 500; }
    .info-item .value.pb-exe { color: #d20f39; }
    .resource-count { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.75rem; }
    .resource-count .badge { background: #d20f39; color: #fff; padding: 0.15rem 0.5rem; border-radius: 12px; font-size: 0.8rem; font-weight: 600; }
    .resource-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
    .resource-table th { text-align: left; padding: 0.4rem; background: #eef2f7; color: #45475a; font-weight: 600; }
    .resource-table td { padding: 0.4rem; border-bottom: 1px solid #eee; color: #1e1e2e; }
    .type-badge { background: #d0bdf4; color: #5e3a9e; padding: 0.1rem 0.4rem; border-radius: 4px; font-size: 0.7rem; font-weight: 500; }
    .no-resources { display: flex; align-items: center; gap: 0.4rem; color: #40a02b; font-size: 0.85rem; }
    .no-resources .material-icons { font-size: 18px; }
    .actions { display: flex; gap: 0.75rem; margin-top: 1rem; }
    .actions button { display: flex; align-items: center; gap: 0.3rem; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; font-size: 0.85rem; border: none; }
    .btn-secondary { background: #f5f5f5; color: #45475a; }
    .btn-secondary:hover { background: #eef2f7; }
    .btn-primary { background: #2563eb; color: #fff; }
    .btn-primary:hover { background: #1d4ed8; }
    .loading, .error { display: flex; align-items: center; gap: 0.5rem; padding: 2rem; justify-content: center; color: #6c7086; }
    .loading .rotating { animation: spin 1s linear infinite; }
    .error { color: #d20f39; }
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
  `]
})
export class PeViewComponent {
  @Input() filePath = '';
  @Input() set data(value: PeInfo | null) {
    this.peInfo = value;
    this.loading = false;
  }
  @Output() onClose = new EventEmitter<void>();
  @Output() onExtract = new EventEmitter<void>();

  peInfo: PeInfo | null = null;
  loading = true;
  error = '';

  formatSize(bytes: number): string {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  }
}