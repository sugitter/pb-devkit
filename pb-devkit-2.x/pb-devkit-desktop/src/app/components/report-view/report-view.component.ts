import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

export interface ReportData {
  project_name: string;
  project_path: string;
  total_pbls: number;
  total_entries: number;
  object_counts: Record<string, number>;
  search_results?: Array<{ path: string; matches: number }>;
}

@Component({
  selector: 'app-report-view',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="report-view">
      <div class="report-header">
        <span class="material-icons mi-lg">assessment</span>
        <h3>Project Report / 项目报告</h3>
      </div>

      @if (loading) {
        <div class="loading">
          <span class="material-icons rotating">sync</span>
          <span>Generating report... / 生成报告中...</span>
        </div>
      } @else if (error) {
        <div class="error">
          <span class="material-icons">error_outline</span>
          {{ error }}
        </div>
      } @else if (report) {
        <!-- Project Summary -->
        <div class="section">
          <h4><span class="material-icons">folder</span> Project Summary / 项目概览</h4>
          <div class="info-grid">
            <div class="info-item">
              <span class="label">Project / 项目:</span>
              <span class="value">{{ report.project_name }}</span>
            </div>
            <div class="info-item">
              <span class="label">Path / 路径:</span>
              <span class="value path">{{ report.project_path }}</span>
            </div>
          </div>
        </div>

        <!-- Statistics -->
        <div class="section">
          <h4><span class="material-icons">bar_chart</span> Statistics / 统计</h4>
          <div class="stats-grid">
            <div class="stat-card">
              <span class="stat-value">{{ report.total_pbls }}</span>
              <span class="stat-label">PBL Files / PBL 文件</span>
            </div>
            <div class="stat-card">
              <span class="stat-value">{{ report.total_entries }}</span>
              <span class="stat-label">Total Objects / 总对象数</span>
            </div>
          </div>
        </div>

        <!-- Object Distribution -->
        <div class="section">
          <h4><span class="material-icons">category</span> Object Distribution / 对象分布</h4>
          @if (report.object_counts && (report.object_counts | keyvalue).length > 0) {
            <div class="object-list">
              @for (item of report.object_counts | keyvalue; track item.key) {
                <div class="object-item">
                  <span class="obj-type">{{ item.key }}</span>
                  <div class="obj-bar" [style.width.%]="getPercent(item.value)"></div>
                  <span class="obj-count">{{ item.value }}</span>
                </div>
              }
            </div>
          } @else {
            <div class="no-data">No object data / 无对象数据</div>
          }
        </div>

        <!-- Search Results -->
        @if (report.search_results && report.search_results.length > 0) {
          <div class="section">
            <h4><span class="material-icons">search</span> Search Results / 搜索结果</h4>
            <div class="search-results">
              @for (result of report.search_results; track result.path) {
                <div class="search-item">
                  <span class="file-path">{{ result.path }}</span>
                  <span class="match-count">{{ result.matches }} matches</span>
                </div>
              }
            </div>
          </div>
        }

        <!-- Actions -->
        <div class="actions">
          <button class="btn-secondary" (click)="onClose.emit()">
            <span class="material-icons">close</span>
            Close / 关闭
          </button>
          <button class="btn-primary" (click)="onExport.emit()">
            <span class="material-icons">download</span>
            Export JSON / 导出 JSON
          </button>
        </div>
      }
    </div>
  `,
  styles: [`
    .report-view { padding: 1rem; height: 100%; overflow-y: auto; }
    .report-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem; color: #1e1e2e; }
    .report-header h3 { margin: 0; font-size: 1.1rem; }
    .section { margin-bottom: 1.25rem; background: #fafafa; border-radius: 8px; padding: 1rem; }
    .section h4 { margin: 0 0 0.75rem; font-size: 0.9rem; color: #45475a; display: flex; align-items: center; gap: 0.4rem; }
    .section h4 .material-icons { font-size: 18px; color: #7c3aed; }
    .info-grid { display: grid; grid-template-columns: 1fr; gap: 0.5rem; }
    .info-item { display: flex; flex-direction: column; gap: 0.15rem; }
    .info-item .label { font-size: 0.75rem; color: #6c7086; }
    .info-item .value { font-size: 0.85rem; color: #1e1e2e; font-weight: 500; }
    .info-item .value.path { font-size: 0.75rem; word-break: break-all; }
    .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
    .stat-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; text-align: center; }
    .stat-value { display: block; font-size: 1.75rem; font-weight: 700; color: #7c3aed; }
    .stat-label { font-size: 0.75rem; color: #6c7086; }
    .object-list { display: flex; flex-direction: column; gap: 0.4rem; }
    .object-item { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8rem; }
    .obj-type { min-width: 100px; color: #45475a; }
    .obj-bar { height: 8px; background: linear-gradient(90deg, #7c3aed, #a855f7); border-radius: 4px; min-width: 4px; }
    .obj-count { min-width: 40px; text-align: right; color: #1e1e2e; font-weight: 500; }
    .no-data { color: #9ca3af; font-size: 0.85rem; text-align: center; padding: 1rem; }
    .search-results { display: flex; flex-direction: column; gap: 0.35rem; max-height: 200px; overflow-y: auto; }
    .search-item { display: flex; justify-content: space-between; align-items: center; padding: 0.4rem 0.5rem; background: #fff; border-radius: 4px; font-size: 0.8rem; }
    .search-item .file-path { color: #1e1e2e; }
    .search-item .match-count { color: #d20f39; font-weight: 500; }
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
export class ReportViewComponent {
  @Input() set data(value: ReportData | null) {
    this.report = value;
    this.loading = false;
  }
  @Output() onClose = new EventEmitter<void>();
  @Output() onExport = new EventEmitter<void>();

  report: ReportData | null = null;
  loading = true;
  error = '';

  getPercent(count: number): number {
    if (!this.report || this.report.total_entries === 0) return 0;
    return Math.min(100, (count / this.report.total_entries) * 100);
  }
}