import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PblService, SearchResult } from '../../services/pbl.service';

@Component({
  selector: 'app-search-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="search-panel">
      <div class="search-header">
        <h3><span class="material-icons" style="vertical-align:middle">search</span> 全文搜索</h3>
      </div>

      <div class="search-form">
        <div class="search-input-row">
          <input [(ngModel)]="query" placeholder="搜索 PowerScript 代码..." class="search-input"
                 (keyup.enter)="doSearch()" />
          <button class="btn-search" (click)="doSearch()" [disabled]="loading || !rootPath">
            搜索
          </button>
        </div>

        <div class="search-options">
          <label><input type="checkbox" [(ngModel)]="caseSensitive" /> 区分大小写</label>
          <label class="object-type-label">类型：
            <select [(ngModel)]="selectedType" class="type-select">
              <option value="">全部</option>
              <option value="window">Window</option>
              <option value="datawindow">DataWindow</option>
              <option value="menu">Menu</option>
              <option value="function">Function</option>
              <option value="userobject">UserObject</option>
              <option value="structure">Structure</option>
              <option value="application">Application</option>
            </select>
          </label>
        </div>
        @if (!rootPath) {
          <div class="hint">请先选择项目或 PBL 文件</div>
        }
      </div>

      @if (loading) {
        <div class="loading-state">
          <div class="spinner"></div>
          <span>{{ selectedType ? '按类型搜索中...' : '全文搜索中...' }}</span>
        </div>
      }

      @if (error) {
        <div class="error-state">
          <span><span class="material-icons" style="font-size:16px">warning</span> {{ error }}</span>
          <button class="btn-dismiss" (click)="error = ''"><span class="material-icons" style="font-size:16px">close</span></button>
        </div>
      }

      @if (typeResults) {
        <div class="results-summary">
          找到 <strong>{{ typeResults.length }}</strong> 个 {{ selectedType }} 类型对象
        </div>
        <div class="results-list">
          @for (name of typeResults; track name) {
            <div class="type-result-item">
              <span class="type-icon"><span class="material-icons" style="font-size:16px">{{ typeIcon(selectedType) }}</span></span>
              <span class="type-name">{{ name }}</span>
            </div>
          }
          @if (typeResults.length === 0) {
            <div class="empty-state">未找到匹配的对象</div>
          }
        </div>
      }

      @if (results && !typeResults) {
        <div class="results-summary">
          找到 <strong>{{ results.total_matches }}</strong> 个匹配，
          共 <strong>{{ results.files_count }}</strong> 个文件
        </div>

        <div class="results-list">
          @for (group of groupedResults; track group.file) {
            <div class="file-group">
              <div class="file-name" (click)="group.collapsed = !group.collapsed">
                <span class="material-icons" style="font-size:14px">{{ group.collapsed ? 'chevron_right' : 'expand_more' }}</span>
                <span>{{ getFileName(group.file) }}</span>
                <span class="match-count">{{ group.matches.length }}</span>
              </div>
              @if (!group.collapsed) {
                @for (match of group.matches; track match.line_number) {
                  <div class="match-item">
                    <span class="line-num">{{ match.line_number }}</span>
                    <span class="line-content" [innerHTML]="highlight(match)"></span>
                  </div>
                }
              }
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .search-panel { display: flex; flex-direction: column; height: 100%; }
    .search-header { padding: 0.75rem 1rem; border-bottom: 1px solid #e5e7eb; }
    .search-header h3 { margin: 0; font-size: 0.9rem; color: #374151; }
    .search-form { padding: 0.75rem 1rem; border-bottom: 1px solid #e5e7eb; }
    .search-input-row { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; }
    .search-input { flex: 1; padding: 0.4rem 0.75rem; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.875rem; }
    .btn-search { padding: 0.4rem 1rem; background: #2563eb; color: white; border: none; border-radius: 4px; cursor: pointer; }
    .btn-search:disabled { opacity: 0.5; cursor: not-allowed; }
    .search-options { display: flex; gap: 1rem; align-items: center; font-size: 0.8rem; color: #374151; }
    .search-options label { display: flex; align-items: center; gap: 0.25rem; cursor: pointer; }
    .type-select { padding: 0.2rem 0.4rem; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.8rem; }
    .hint { margin-top: 0.5rem; font-size: 0.75rem; color: #9ca3af; }
    .loading-state { display: flex; align-items: center; gap: 0.75rem; padding: 1.5rem; justify-content: center; color: #6b7280; }
    .spinner { width: 18px; height: 18px; border: 2px solid #e5e7eb; border-top-color: #3b82f6; border-radius: 50%; animation: spin 0.8s linear infinite; flex-shrink: 0; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .error-state { display: flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1rem; margin: 0.5rem; background: #fee2e2; color: #dc2626; border-radius: 6px; font-size: 0.8rem; }
    .btn-dismiss { margin-left: auto; background: none; border: none; color: #dc2626; cursor: pointer; font-size: 0.9rem; }
    .results-summary { padding: 0.5rem 1rem; background: #f9fafb; font-size: 0.8rem; color: #374151; border-bottom: 1px solid #e5e7eb; }
    .results-list { flex: 1; overflow-y: auto; }
    .file-group { border-bottom: 1px solid #f3f4f6; }
    .file-name { display: flex; align-items: center; gap: 0.5rem; padding: 0.4rem 1rem; background: #f9fafb; cursor: pointer; font-size: 0.8rem; font-family: monospace; color: #374151; }
    .file-name:hover { background: #f3f4f6; }
    .match-count { margin-left: auto; background: #dbeafe; color: #1d4ed8; padding: 0.1rem 0.4rem; border-radius: 10px; font-size: 0.7rem; }
    .match-item { display: flex; padding: 0.25rem 1rem 0.25rem 2rem; font-size: 0.8rem; font-family: monospace; gap: 0.75rem; }
    .match-item:hover { background: #eff6ff; }
    .line-num { min-width: 40px; color: #9ca3af; text-align: right; }
    .line-content { color: #374151; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    :host ::ng-deep mark.highlight { background: #fef08a; color: #111; border-radius: 2px; }
    .type-result-item { display: flex; align-items: center; gap: 0.5rem; padding: 0.4rem 1rem; border-bottom: 1px solid #f3f4f6; cursor: default; }
    .type-result-item:hover { background: #f9fafb; }
    .type-icon { font-size: 0.9rem; }
    .type-name { font-size: 0.85rem; font-family: monospace; color: #111; }
    .empty-state { padding: 2rem; text-align: center; color: #9ca3af; font-size: 0.85rem; }
  `]
})
export class SearchPanelComponent {
  @Input() rootPath = '';

  query = '';
  caseSensitive = false;
  selectedType = '';
  loading = false;
  error = '';
  results: { total_matches: number; files_count: number; matches: SearchResult[] } | null = null;
  typeResults: string[] | null = null;
  groupedResults: { file: string; matches: SearchResult[]; collapsed: boolean }[] = [];

  constructor(private pblService: PblService) {}

  async doSearch() {
    if (!this.rootPath) return;

    // If a type is selected without a query, do type-only search
    if (this.selectedType && !this.query.trim()) {
      await this.doTypeSearch();
      return;
    }

    // If both query and type are set, do full-text search first
    if (!this.query.trim()) return;

    this.loading = true;
    this.error = '';
    this.typeResults = null;
    try {
      this.results = await this.pblService.searchInFiles(
        this.rootPath, this.query, this.caseSensitive, []
      );
      const map = new Map<string, SearchResult[]>();
      for (const m of this.results.matches) {
        const arr = map.get(m.file) ?? [];
        arr.push(m);
        map.set(m.file, arr);
      }
      this.groupedResults = [...map.entries()].map(([file, matches]) => ({
        file, matches, collapsed: false
      }));
    } catch (e: any) {
      this.error = e.message ?? '搜索失败';
    }
    this.loading = false;
  }

  async doTypeSearch() {
    if (!this.selectedType || !this.rootPath) return;
    this.loading = true;
    this.error = '';
    this.results = null;
    try {
      this.typeResults = await this.pblService.searchByType(this.rootPath, this.selectedType);
    } catch (e: any) {
      this.error = e.message ?? '按类型搜索失败';
    }
    this.loading = false;
  }

  typeIcon(type: string): string {
    const icons: Record<string, string> = {
      window: 'window', datawindow: 'bar_chart', menu: 'menu', function: 'functions',
      structure: 'diamond', userobject: 'extension', application: 'rocket_launch'
    };
    return icons[type] ?? 'description';
  }

  highlight(match: SearchResult): string {
    const line = this.escapeHtml(match.line_content);
    const q = this.escapeHtml(this.query);
    const flags = this.caseSensitive ? 'g' : 'gi';
    try {
      return line.replace(new RegExp(q, flags), '<mark class="highlight">$&</mark>');
    } catch { return line; }
  }

  escapeHtml(s: string): string {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  getFileName(path: string): string {
    return path.split(/[\\/]/).pop() ?? path;
  }
}
