import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PblService, DwInfo, DwAnalysisResult } from '../../services/pbl.service';

@Component({
  selector: 'app-dw-analyzer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="dw-analyzer">
      <div class="dw-header">
        <h3>📊 DataWindow 分析</h3>
        <button class="btn-analyze" (click)="analyze()" [disabled]="loading || !rootPath">
          分析
        </button>
      </div>

      @if (loading) {
        <div class="loading-state">
          <div class="spinner"></div>
          <span>分析中...</span>
        </div>
      }

      @if (error) {
        <div class="error-state">
          <span>⚠ {{ error }}</span>
          <button class="btn-dismiss" (click)="error = ''">✕</button>
        </div>
      }

      @if (result) {
        <div class="summary-cards">
          <div class="card">
            <div class="card-value">{{ result.total_count }}</div>
            <div class="card-label">DataWindow 总数</div>
          </div>
          <div class="card">
            <div class="card-value">{{ result.tables_found.length }}</div>
            <div class="card-label">涉及数据库表</div>
          </div>
        </div>

        @if (result.tables_found.length > 0) {
          <div class="section">
            <h4>数据库表</h4>
            <div class="tags">
              @for (t of result.tables_found; track t) {
                <span class="tag">🗃 {{ t }}</span>
              }
            </div>
          </div>
        }

        <div class="section">
          <h4>DataWindow 列表</h4>
          <div class="dw-list">
            @for (dw of result.datawindows; track dw.name) {
              <div class="dw-item" (click)="selectDw(dw)" [class.selected]="selectedDw?.name === dw.name">
                <div class="dw-name">📊 {{ dw.name }}</div>
                @if (dw.tables.length > 0) {
                  <div class="dw-tables">{{ dw.tables.join(', ') }}</div>
                }
              </div>
            }
          </div>
        </div>

        @if (selectedDw) {
          <div class="section dw-detail">
            <h4>{{ selectedDw.name }} 详情</h4>
            @if (selectedDw.style) {
              <div class="detail-row">
                <span class="detail-label">样式</span>
                <span class="detail-value">{{ selectedDw.style }}</span>
              </div>
            }
            @if (selectedDw.columns.length > 0) {
              <div class="detail-row">
                <span class="detail-label">列 ({{ selectedDw.columns.length }})</span>
              </div>
              <div class="column-tags">
                @for (col of selectedDw.columns; track col) {
                  <span class="col-tag">{{ col }}</span>
                }
              </div>
            }
          </div>
        }

        @if (selectedDw?.sql) {
          <div class="section sql-section">
            <div class="sql-header">
              <h4>SQL</h4>
              <button class="btn-copy" (click)="copySql()">📋 复制</button>
            </div>
            <pre class="sql-code">{{ selectedDw!.sql }}</pre>
          </div>
        } @else if (selectedDw && !selectedDw.sql && !sqlLoading) {
          <div class="section">
            <button class="btn-fetch-sql" (click)="fetchDwSql()">
              🔍 获取 SQL
            </button>
          </div>
        }

        @if (sqlLoading) {
          <div class="loading-state small">
            <div class="spinner"></div>
            <span>获取 SQL...</span>
          </div>
        }
      }

      @if (!result && !loading && !error) {
        <div class="empty-hint">
          <p>点击「分析」开始扫描 DataWindow 对象</p>
        </div>
      }
    </div>
  `,
  styles: [`
    .dw-analyzer { display: flex; flex-direction: column; height: 100%; overflow-y: auto; }
    .dw-header { display: flex; align-items: center; justify-content: space-between; padding: 0.75rem 1rem; border-bottom: 1px solid #e5e7eb; }
    .dw-header h3 { margin: 0; font-size: 0.9rem; color: #374151; }
    .btn-analyze { padding: 0.35rem 0.75rem; background: #7c3aed; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.8rem; }
    .btn-analyze:disabled { opacity: 0.5; cursor: not-allowed; }
    .loading-state { display: flex; align-items: center; gap: 0.75rem; padding: 1.5rem; justify-content: center; color: #6b7280; }
    .loading-state.small { padding: 0.75rem; }
    .spinner { width: 18px; height: 18px; border: 2px solid #e5e7eb; border-top-color: #7c3aed; border-radius: 50%; animation: spin 0.8s linear infinite; flex-shrink: 0; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .error-state { display: flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1rem; margin: 0.5rem; background: #fee2e2; color: #dc2626; border-radius: 6px; font-size: 0.8rem; }
    .btn-dismiss { margin-left: auto; background: none; border: none; color: #dc2626; cursor: pointer; font-size: 0.9rem; }
    .summary-cards { display: flex; gap: 1rem; padding: 1rem; }
    .card { flex: 1; background: #f9fafb; border-radius: 8px; padding: 1rem; text-align: center; border: 1px solid #e5e7eb; }
    .card-value { font-size: 2rem; font-weight: bold; color: #7c3aed; }
    .card-label { font-size: 0.75rem; color: #6b7280; margin-top: 0.25rem; }
    .section { padding: 0.75rem 1rem; border-top: 1px solid #f3f4f6; }
    .section h4 { margin: 0 0 0.5rem; font-size: 0.85rem; color: #374151; }
    .tags { display: flex; flex-wrap: wrap; gap: 0.5rem; }
    .tag { padding: 0.2rem 0.5rem; background: #ede9fe; color: #5b21b6; border-radius: 4px; font-size: 0.75rem; font-family: monospace; }
    .dw-list { max-height: 200px; overflow-y: auto; }
    .dw-item { padding: 0.4rem 0.5rem; cursor: pointer; border-radius: 4px; margin-bottom: 0.25rem; }
    .dw-item:hover { background: #f3f4f6; }
    .dw-item.selected { background: #ede9fe; }
    .dw-name { font-size: 0.875rem; font-family: monospace; color: #111; }
    .dw-tables { font-size: 0.75rem; color: #6b7280; margin-top: 0.15rem; }
    .dw-detail { background: #f9fafb; }
    .detail-row { display: flex; gap: 0.5rem; padding: 0.2rem 0; font-size: 0.8rem; }
    .detail-label { color: #6b7280; min-width: 60px; }
    .detail-value { color: #111; }
    .column-tags { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.25rem; }
    .col-tag { padding: 0.15rem 0.4rem; background: #dbeafe; color: #1d4ed8; border-radius: 4px; font-size: 0.7rem; font-family: monospace; }
    .sql-header { display: flex; align-items: center; justify-content: space-between; }
    .btn-copy { padding: 0.2rem 0.5rem; background: #f3f4f6; color: #374151; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; font-size: 0.7rem; }
    .btn-copy:hover { background: #e5e7eb; }
    .btn-fetch-sql { padding: 0.3rem 0.75rem; background: #7c3aed; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.8rem; }
    .btn-fetch-sql:hover { background: #6d28d9; }
    .sql-section { background: #f9fafb; margin: 0; padding: 1rem; border: 1px solid #e5e7eb; border-radius: 4px; }
    .sql-section h4 { color: #374151; }
    .sql-code { margin: 0; font-size: 0.8rem; color: #1f2937; font-family: 'Consolas', monospace; white-space: pre-wrap; word-break: break-all; background: #fafbfc; padding: 0.75rem; border-radius: 4px; border: 1px solid #e5e7eb; }
    .empty-hint { padding: 3rem 1rem; text-align: center; color: #9ca3af; }
    .empty-hint p { margin: 0; font-size: 0.85rem; }
  `]
})
export class DwAnalyzerComponent {
  @Input() rootPath = '';

  result: DwAnalysisResult | null = null;
  selectedDw: DwInfo | null = null;
  loading = false;
  sqlLoading = false;
  error = '';

  constructor(private pblService: PblService) {}

  async analyze() {
    if (!this.rootPath) return;
    this.loading = true;
    this.error = '';
    try {
      this.result = await this.pblService.analyzeDatawindows(this.rootPath);
      this.selectedDw = null;
    } catch (e: any) {
      this.error = e.message ?? '分析失败';
    }
    this.loading = false;
  }

  selectDw(dw: DwInfo) {
    this.selectedDw = dw;
  }

  async fetchDwSql() {
    if (!this.selectedDw) return;
    this.sqlLoading = true;
    try {
      const sql = await this.pblService.getDwSql(this.selectedDw.path);
      // Update the selectedDw's SQL
      this.selectedDw = { ...this.selectedDw, sql };
      // Also update the result's datawindows array
      if (this.result) {
        this.result = {
          ...this.result,
          datawindows: this.result.datawindows.map(dw =>
            dw.name === this.selectedDw!.name ? this.selectedDw! : dw
          )
        };
      }
    } catch (e: any) {
      this.error = e.message ?? '获取 SQL 失败';
    }
    this.sqlLoading = false;
  }

  async copySql() {
    if (!this.selectedDw?.sql) return;
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(this.selectedDw.sql);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = this.selectedDw.sql;
        textarea.style.position = 'fixed';
        textarea.style.left = '-9999px';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
    } catch {}
  }
}
