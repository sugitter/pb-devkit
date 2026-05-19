import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PblService, SearchResult } from '../../services/pbl.service';

@Component({
  selector: 'app-search-regex-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="search-panel">
      <div class="search-header">
        <h3><span class="material-icons" style="vertical-align:middle">code</span> 正则搜索</h3>
      </div>

      <div class="search-form">
        <div class="search-input-row">
          <input [(ngModel)]="pattern" placeholder="输入正则表达式..." class="search-input"
                 (keyup.enter)="doSearch()" />
          <button class="btn-search" (click)="doSearch()" [disabled]="loading || !rootPath">
            搜索
          </button>
        </div>

        <div class="search-options">
          <label><input type="checkbox" [(ngModel)]="caseSensitive" /> 区分大小写</label>
          <div class="regex-help" title="常用正则示例">
            <span class="material-icons" style="font-size:16px">help_outline</span>
            <div class="regex-help-content">
              <strong>常用正则示例：</strong><br/>
              dw_.* - 以 dw_ 开头的对象<br/>
              {{ '\b' }}SELECT{{ '\b' }} - 完整的 SELECT 单词<br/>
              ^{{ '\s' }}*// - 行首注释<br/>
              {{ '\d' }}&lbrace;4{{ '\rbrace' }}-{{ '\d' }}&lbrace;2{{ '\rbrace' }}-{{ '\d' }}&lbrace;2{{ '\rbrace' }} - 日期格式<br/>
              (if|then|else|end if) - 条件关键字
            </div>
          </div>
        </div>
        @if (!rootPath) {
          <div class="hint">请先选择项目或 PBL 文件</div>
        }
        @if (regexError) {
          <div class="error-state">
            <span><span class="material-icons" style="font-size:16px">warning</span> {{ regexError }}</span>
          </div>
        }
      </div>

      @if (loading) {
        <div class="loading-state">
          <div class="spinner"></div>
          <span>正则搜索中...</span>
        </div>
      }

      @if (results && !loading) {
        <div class="results-summary">
          找到 <strong>{{ results.total_matches }}</strong> 个匹配，
          共 <strong>{{ results.files_count }}</strong> 个文件
        </div>

        <div class="results-list">
          @for (group of groupedResults; track group.file) {
            <div class="file-group">
              <div class="file-name" (click)="group.collapsed = !group.collapsed" (dblclick)="openFile(group.file)">
                <span class="material-icons" style="font-size:14px">{{ group.collapsed ? 'chevron_right' : 'expand_more' }}</span>
                <span>{{ getFileName(group.file) }}</span>
                <span class="match-count">{{ group.matches.length }}</span>
              </div>
              @if (!group.collapsed) {
                @for (match of group.matches; track match.line_number) {
                  <div class="match-item" (click)="openFile(group.file)" title="点击打开文件">
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
    .search-input { flex: 1; padding: 0.4rem 0.75rem; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.875rem; font-family: monospace; }
    .btn-search { padding: 0.4rem 1rem; background: #7c3aed; color: white; border: none; border-radius: 4px; cursor: pointer; }
    .btn-search:disabled { opacity: 0.5; cursor: not-allowed; }
    .search-options { display: flex; gap: 1rem; align-items: center; font-size: 0.8rem; color: #374151; }
    .search-options label { display: flex; align-items: center; gap: 0.25rem; cursor: pointer; }
    .hint { margin-top: 0.5rem; font-size: 0.75rem; color: #9ca3af; }
    .regex-help { position: relative; cursor: help; }
    .regex-help-content {
      display: none; position: absolute; left: 100%; top: 0; margin-left: 0.5rem;
      background: #fff; border: 1px solid #e5e7eb; border-radius: 6px; padding: 0.75rem;
      font-size: 0.75rem; width: 200px; z-index: 10; box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .regex-help:hover .regex-help-content { display: block; }
    .error-state { display: flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1rem; margin: 0.5rem; background: #fee2e2; color: #dc2626; border-radius: 6px; font-size: 0.8rem; }
    .loading-state { display: flex; align-items: center; gap: 0.75rem; padding: 1.5rem; justify-content: center; color: #6b7280; }
    .spinner { width: 18px; height: 18px; border: 2px solid #e5e7eb; border-top-color: #7c3aed; border-radius: 50%; animation: spin 0.8s linear infinite; flex-shrink: 0; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .results-summary { padding: 0.5rem 1rem; background: #f9fafb; font-size: 0.8rem; color: #374151; border-bottom: 1px solid #e5e7eb; }
    .results-list { flex: 1; overflow-y: auto; }
    .file-group { border-bottom: 1px solid #f3f4f6; }
    .file-name { display: flex; align-items: center; gap: 0.5rem; padding: 0.4rem 1rem; background: #f9fafb; cursor: pointer; font-size: 0.8rem; font-family: monospace; color: #374151; }
    .file-name:hover { background: #f3f4f6; }
    .match-count { margin-left: auto; background: #ede9fe; color: #7c3aed; padding: 0.1rem 0.4rem; border-radius: 10px; font-size: 0.7rem; }
    .match-item { display: flex; padding: 0.25rem 1rem 0.25rem 2rem; font-size: 0.8rem; font-family: monospace; gap: 0.75rem; cursor: pointer; }
    .match-item:hover { background: #f5f3ff; }
    .line-num { min-width: 40px; color: #9ca3af; text-align: right; }
    .line-content { color: #374151; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    :host ::ng-deep mark.highlight { background: #c4b5fd; color: #111; border-radius: 2px; }
  `]
})
export class SearchRegexPanelComponent {
  @Input() rootPath = '';
  @Output() fileSelected = new EventEmitter<string>();

  pattern = '';
  caseSensitive = false;
  loading = false;
  regexError = '';
  results: { total_matches: number; files_count: number; matches: SearchResult[] } | null = null;
  groupedResults: { file: string; matches: SearchResult[]; collapsed: boolean }[] = [];

  constructor(private pblService: PblService) {}

  async doSearch() {
    if (!this.rootPath || !this.pattern.trim()) return;

    // Validate regex
    try {
      new RegExp(this.pattern, this.caseSensitive ? 'g' : 'gi');
      this.regexError = '';
    } catch (e: any) {
      this.regexError = '无效的正则表达式: ' + (e.message || e);
      return;
    }

    this.loading = true;
    this.results = null;
    try {
      this.results = await this.pblService.searchWithRegex(
        this.rootPath, this.pattern, this.caseSensitive, []
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
      this.regexError = e.message ?? '搜索失败';
    }
    this.loading = false;
  }

  highlight(match: SearchResult): string {
    const line = this.escapeHtml(match.line_content);
    const p = this.escapeHtml(this.pattern);
    const flags = this.caseSensitive ? 'g' : 'gi';
    try {
      return line.replace(new RegExp(p, flags), '<mark class="highlight">$&</mark>');
    } catch { return line; }
  }

  escapeHtml(s: string): string {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  getFileName(path: string): string {
    return path.split(/[\\/]/).pop() ?? path;
  }

  /** 点击文件/匹配项时触发，跳转到 Explorer 并选中该 PBL */
  openFile(filePath: string) {
    this.fileSelected.emit(filePath);
  }
}