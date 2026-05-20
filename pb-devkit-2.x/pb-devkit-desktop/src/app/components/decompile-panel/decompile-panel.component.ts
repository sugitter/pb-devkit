import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { open } from '@tauri-apps/plugin-dialog';
import { PblService, DecompileEntry, FileTypeResult, PeInfoResult } from '../../services/pbl.service';

interface TypeGroup {
  typeName: string;
  icon: string;
  color: string;
  entries: DecompileEntry[];
  expanded: boolean;
}

@Component({
  selector: 'app-decompile-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="pbl-tree">

      <!-- 工具栏 -->
      <div class="tree-toolbar">
        <div class="tree-title">
          <span class="material-icons tree-title-icon">{{ fileIcon }}</span>
          <span class="tree-title-text" [title]="filePath">{{ fileName }}</span>
        </div>
        <div class="tree-actions">
          <button class="tbtn" (click)="expandAll()" title="展开全部"><span class="material-icons">unfold_more</span></button>
          <button class="tbtn" (click)="collapseAll()" title="折叠全部"><span class="material-icons">unfold_less</span></button>
          <button class="tbtn" (click)="exportAllEntries()" title="导出全部" [disabled]="loading || !entries.length">
            <span class="material-icons">download</span>
          </button>
        </div>
      </div>

      <!-- PE 折叠信息 -->
      @if (peInfo) {
        <div class="pe-section">
          <div class="pe-toggle-row" (click)="showPeDetails = !showPeDetails">
            <span class="material-icons" style="font-size:13px;color:#60a5fa">computer</span>
            <span class="pe-toggle-label">PE 信息</span>
            <span class="material-icons chevron-sm">{{ showPeDetails ? 'expand_more' : 'chevron_right' }}</span>
          </div>
          @if (showPeDetails) {
            <div class="pe-body">
              <div class="pe-row">
                <span class="pe-k">架构</span>
                <span class="pe-v">{{ peInfo.is_64bit ? '64-bit' : '32-bit' }}</span>
              </div>
              @if (peInfo.timestamp) {
                <div class="pe-row"><span class="pe-k">编译时间</span><span class="pe-v">{{ peInfo.timestamp }}</span></div>
              }
              <div class="pe-row">
                <span class="pe-k">PB 文件</span>
                <span class="pe-v" [class.pv-yes]="peInfo.is_pb_exe">{{ peInfo.is_pb_exe ? '是' : '否' }}</span>
              </div>
              @if (peInfo.embedded_pbl_count > 0) {
                <div class="pe-row">
                  <span class="pe-k">嵌入 PBD</span>
                  <span class="pe-v pv-yes">{{ peInfo.embedded_pbl_count }} 个</span>
                </div>
              }
            </div>
          }
        </div>
      }

      <!-- 搜索框 -->
      <div class="tree-search">
        <span class="material-icons search-ic">search</span>
        <input [(ngModel)]="searchQuery" (ngModelChange)="rebuildGroups()" placeholder="过滤对象..." class="search-input" />
        @if (searchQuery) {
          <button class="search-clear" (click)="searchQuery=''; rebuildGroups()">
            <span class="material-icons">close</span>
          </button>
        }
      </div>

      <!-- 统计 -->
      @if (entries.length > 0 && !loading) {
        <div class="tree-stats">
          <span class="badge badge-src"><span class="material-icons">description</span> {{ sourceCount }}</span>
          <span class="badge badge-bin"><span class="material-icons">lock</span> {{ compiledCount }}</span>
          <span class="badge badge-all">共 {{ entries.length }}</span>
        </div>
      }

      <!-- 加载 -->
      @if (loading) {
        <div class="tree-loading">
          <div class="spinner"></div><span>{{ loadingMsg }}</span>
        </div>
      }

      <!-- 错误 -->
      @if (error) {
        <div class="tree-msg">
          {{ error }}
          <button class="msg-close" (click)="error=''"><span class="material-icons">close</span></button>
        </div>
      }

      <!-- 提取按钮（未分析时） -->
      @if (!entries.length && !loading && !error) {
        <div class="tree-action-area">
          <button class="btn-primary" (click)="loadEntries()">
            <span class="material-icons">search</span> 分析文件
          </button>
          @if (filePath.toLowerCase().endsWith('.exe') || filePath.toLowerCase().endsWith('.dll')) {
            <button class="btn-secondary" (click)="extractEmbedded()">
              <span class="material-icons">inventory_2</span> 提取嵌入 PBD
            </button>
          }
        </div>
      }

      <!-- 提取成功 -->
      @if (extractResult) {
        <div class="extract-ok">
          <span class="material-icons" style="font-size:14px">check_circle</span>
          已提取 {{ extractResult.pbd_count }} 个 PBD
          @if (extractResult.output_path) { → {{ extractResult.output_path }} }
        </div>
      }

      <!-- 树体 -->
      @if (!loading && groups.length > 0) {
        <div class="tree-body">
          @for (group of groups; track group.typeName) {
            <div class="tree-group-row" (click)="toggleGroup(group)">
              <span class="material-icons chevron">{{ group.expanded ? 'expand_more' : 'chevron_right' }}</span>
              <span class="material-icons type-ic" [style.color]="group.color">{{ group.icon }}</span>
              <span class="group-label">{{ group.typeName }}</span>
              <span class="group-count">{{ group.entries.length }}</span>
            </div>
            @if (group.expanded) {
              @for (entry of group.entries; track entry.name) {
                <div class="tree-leaf"
                     [class.selected]="selectedEntry?.name === entry.name"
                     (click)="selectEntry(entry)"
                     (dblclick)="onDblClick(entry)">
                  <span class="leaf-indent"></span>
                  <span class="material-icons leaf-ic"
                        [style.color]="entry.is_source ? '#4ade80' : '#f59e0b'">
                    {{ entry.is_source ? 'article' : 'lock' }}
                  </span>
                  <span class="leaf-name" [title]="entry.name">{{ entry.name }}</span>
                  @if (entry.is_source) {
                    <button class="btn-code" (click)="viewEntry(entry, $event)" title="查看源码">
                      <span class="material-icons">code</span>
                    </button>
                  }
                </div>
              }
            }
          }
        </div>
      }

      @if (!loading && entries.length > 0 && groups.length === 0) {
        <div class="tree-empty">
          <span class="material-icons" style="font-size:28px;color:#45475a">search_off</span>
          <p>无匹配对象</p>
        </div>
      }

    </div>
  `,
  styles: [`
    .pbl-tree {
      display: flex; flex-direction: column; height: 100%;
      background: #1e1e2e; color: #cdd6f4; font-size: 0.82rem; overflow: hidden;
    }

    /* 工具栏 */
    .tree-toolbar {
      display: flex; align-items: center; justify-content: space-between;
      padding: 0.3rem 0.4rem 0.3rem 0.6rem;
      border-bottom: 1px solid #313244; flex-shrink: 0; gap: 0.3rem;
    }
    .tree-title { display: flex; align-items: center; gap: 0.3rem; min-width: 0; flex: 1; }
    .tree-title-icon { font-size: 14px; color: #fbbf24; flex-shrink: 0; }
    .tree-title-text {
      font-size: 0.75rem; font-weight: 600; color: #cdd6f4;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .tree-actions { display: flex; gap: 1px; flex-shrink: 0; }
    .tbtn {
      width: 22px; height: 22px; border: none; background: transparent;
      cursor: pointer; border-radius: 3px; color: #6c7086;
      display: flex; align-items: center; justify-content: center;
    }
    .tbtn .material-icons { font-size: 14px; }
    .tbtn:hover:not(:disabled) { background: #313244; color: #cdd6f4; }
    .tbtn:disabled { opacity: 0.35; cursor: not-allowed; }

    /* PE 信息 */
    .pe-section { border-bottom: 1px solid #313244; flex-shrink: 0; }
    .pe-toggle-row {
      display: flex; align-items: center; gap: 0.3rem;
      padding: 0.25rem 0.5rem; cursor: pointer; background: #181825;
    }
    .pe-toggle-row:hover { background: #313244; }
    .pe-toggle-label { flex: 1; font-size: 0.72rem; font-weight: 600; color: #6c7086; text-transform: uppercase; letter-spacing: 0.05em; }
    .chevron-sm { font-size: 13px; color: #6c7086; }
    .pe-body { padding: 0.2rem 0.5rem; background: #181825; }
    .pe-row { display: flex; gap: 0.5rem; padding: 0.15rem 0; font-size: 0.72rem; }
    .pe-k { color: #6c7086; min-width: 60px; flex-shrink: 0; }
    .pe-v { color: #a6adc8; font-family: monospace; }
    .pv-yes { color: #4ade80; font-weight: 600; }

    /* 搜索 */
    .tree-search {
      display: flex; align-items: center; gap: 0.3rem;
      padding: 0.28rem 0.5rem; border-bottom: 1px solid #313244; flex-shrink: 0;
    }
    .search-ic { font-size: 13px; color: #45475a; flex-shrink: 0; }
    .search-input {
      flex: 1; background: #181825; border: 1px solid #313244; border-radius: 3px;
      color: #cdd6f4; font-size: 0.76rem; padding: 0.18rem 0.4rem; outline: none;
    }
    .search-input::placeholder { color: #45475a; }
    .search-input:focus { border-color: #7c3aed; }
    .search-clear {
      background: none; border: none; cursor: pointer; color: #6c7086;
      display: flex; align-items: center; padding: 1px;
    }
    .search-clear .material-icons { font-size: 13px; }

    /* 统计 */
    .tree-stats {
      display: flex; gap: 0.3rem; padding: 0.2rem 0.5rem;
      border-bottom: 1px solid #313244; flex-shrink: 0; background: #181825;
    }
    .badge { display: flex; align-items: center; gap: 0.2rem; padding: 0.08rem 0.4rem; border-radius: 10px; font-size: 0.68rem; }
    .badge .material-icons { font-size: 10px; }
    .badge-src { background: #14532d; color: #86efac; }
    .badge-bin { background: #451a03; color: #fcd34d; }
    .badge-all { background: #1e1b4b; color: #a5b4fc; font-weight: 600; }

    /* 加载/消息 */
    .tree-loading {
      display: flex; align-items: center; gap: 0.5rem;
      padding: 1.5rem; justify-content: center; color: #6c7086;
    }
    .spinner {
      width: 14px; height: 14px; border: 2px solid #313244;
      border-top-color: #cba6f7; border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .tree-msg {
      display: flex; align-items: center; gap: 0.4rem;
      margin: 0.25rem 0.4rem; padding: 0.3rem 0.5rem;
      border-radius: 4px; font-size: 0.74rem;
      background: #7f1d1d; color: #fecaca;
    }
    .msg-close { margin-left: auto; background: none; border: none; cursor: pointer; color: #fca5a5; display: flex; align-items: center; }
    .msg-close .material-icons { font-size: 13px; }

    /* 操作区 */
    .tree-action-area {
      display: flex; flex-direction: column; gap: 0.5rem;
      padding: 1.5rem 1rem; align-items: center;
    }
    .btn-primary {
      padding: 0.4rem 1rem; background: #2563eb; color: white;
      border: none; border-radius: 5px; cursor: pointer; font-size: 0.8rem;
      display: flex; align-items: center; gap: 0.3rem;
    }
    .btn-primary:hover { background: #1d4ed8; }
    .btn-secondary {
      padding: 0.4rem 1rem; background: #313244; color: #cdd6f4;
      border: 1px solid #45475a; border-radius: 5px; cursor: pointer; font-size: 0.8rem;
      display: flex; align-items: center; gap: 0.3rem;
    }
    .btn-secondary:hover { background: #45475a; }

    .extract-ok {
      display: flex; align-items: center; gap: 0.3rem;
      margin: 0.3rem 0.4rem; padding: 0.3rem 0.5rem;
      border-radius: 4px; font-size: 0.72rem;
      background: #14532d; color: #bbf7d0;
    }

    /* 树体 */
    .tree-body { flex: 1; overflow-y: auto; }
    .tree-group-row {
      display: flex; align-items: center; gap: 0.2rem;
      padding: 0.26rem 0.4rem; cursor: pointer; user-select: none;
      border-bottom: 1px solid #181825;
    }
    .tree-group-row:hover { background: #313244; }
    .chevron { font-size: 14px; color: #6c7086; flex-shrink: 0; }
    .type-ic { font-size: 14px; flex-shrink: 0; }
    .group-label { flex: 1; font-size: 0.76rem; font-weight: 600; color: #a6adc8; }
    .group-count { font-size: 0.66rem; color: #6c7086; background: #313244; padding: 0.06rem 0.3rem; border-radius: 8px; }

    .tree-leaf {
      display: flex; align-items: center; gap: 0.2rem;
      padding: 0.2rem 0.4rem; cursor: pointer; border-bottom: 1px solid #181825;
    }
    .tree-leaf:hover { background: #2a2a3e; }
    .tree-leaf.selected { background: #2a2a3e; border-left: 2px solid #cba6f7; }
    .leaf-indent { width: 20px; flex-shrink: 0; }
    .leaf-ic { font-size: 13px; flex-shrink: 0; }
    .leaf-name { flex: 1; font-size: 0.79rem; color: #cdd6f4; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .tree-leaf.selected .leaf-name { color: #cba6f7; }

    .btn-code {
      background: none; border: none; cursor: pointer; color: #45475a;
      display: flex; align-items: center; padding: 1px; border-radius: 3px;
      opacity: 0; transition: opacity 0.1s;
    }
    .tree-leaf:hover .btn-code,
    .tree-leaf.selected .btn-code { opacity: 1; }
    .btn-code .material-icons { font-size: 13px; }
    .btn-code:hover { color: #cba6f7; background: #313244; }

    .tree-empty {
      flex: 1; display: flex; flex-direction: column;
      align-items: center; justify-content: center; color: #45475a;
    }
    .tree-empty p { margin: 0.3rem 0 0; font-size: 0.78rem; }
  `]
})
export class DecompilePanelComponent implements OnChanges {
  @Input() filePath = '';
  @Output() entrySelected = new EventEmitter<{ path: string; name: string; source: string; error?: string }>();

  entries: DecompileEntry[] = [];
  groups: TypeGroup[] = [];
  selectedEntry: DecompileEntry | null = null;
  searchQuery = '';
  loading = false;
  loadingMsg = '分析中...';
  error = '';
  fileTypeResult: FileTypeResult | null = null;
  peInfo: PeInfoResult | null = null;
  showPeDetails = false;
  extractResult: { pbd_count: number; output_path?: string } | null = null;

  private expandMap = new Map<string, boolean>();

  constructor(private pblService: PblService) {}

  ngOnChanges(changes: SimpleChanges) {
    if (changes['filePath'] && this.filePath) {
      this.reset();
      this.detectFileType();
      this.loadPeInfo();
      this.loadEntries();
    }
  }

  reset() {
    this.entries = [];
    this.groups = [];
    this.selectedEntry = null;
    this.error = '';
    this.extractResult = null;
    this.fileTypeResult = null;
    this.peInfo = null;
    this.showPeDetails = false;
    this.expandMap.clear();
    this.searchQuery = '';
  }

  get fileName(): string { return this.filePath.split(/[\\/]/).pop() ?? this.filePath; }

  get fileIcon(): string {
    const n = this.fileName.toLowerCase();
    if (n.endsWith('.exe')) return 'settings';
    if (n.endsWith('.pbd')) return 'lock_open';
    if (n.endsWith('.dll')) return 'build';
    return 'folder';
  }

  get sourceCount(): number { return this.entries.filter(e => e.is_source).length; }
  get compiledCount(): number { return this.entries.filter(e => !e.is_source).length; }

  rebuildGroups() {
    let list = this.entries;
    if (this.searchQuery.trim()) {
      const q = this.searchQuery.toLowerCase();
      list = list.filter(e => e.name.toLowerCase().includes(q));
    }
    const map = new Map<string, DecompileEntry[]>();
    for (const e of list) {
      const tn = e.entry_type || 'unknown';
      if (!map.has(tn)) map.set(tn, []);
      map.get(tn)!.push(e);
    }
    const result: TypeGroup[] = [];
    for (const [typeName, entries] of map) {
      const expanded = this.expandMap.has(typeName) ? this.expandMap.get(typeName)! : true;
      result.push({ typeName, icon: this.typeIcon(typeName), color: this.typeColor(typeName), entries, expanded });
    }
    result.sort((a, b) => b.entries.length - a.entries.length);
    this.groups = result;
  }

  toggleGroup(group: TypeGroup) {
    group.expanded = !group.expanded;
    this.expandMap.set(group.typeName, group.expanded);
  }

  expandAll() { for (const g of this.groups) { g.expanded = true; this.expandMap.set(g.typeName, true); } }
  collapseAll() { for (const g of this.groups) { g.expanded = false; this.expandMap.set(g.typeName, false); } }

  selectEntry(entry: DecompileEntry) { this.selectedEntry = entry; }

  async onDblClick(entry: DecompileEntry) {
    if (!entry.is_source) return;
    await this.decompileAndShow(entry);
  }

  async viewEntry(entry: DecompileEntry, event: Event) {
    event.stopPropagation();
    await this.decompileAndShow(entry);
  }

  private async decompileAndShow(entry: DecompileEntry) {
    try {
      const result = await this.pblService.decompileEntry(this.filePath, entry.name);
      if (result.success && result.source) {
        this.entrySelected.emit({ path: this.filePath, name: entry.name, source: result.source });
      } else {
        const errMsg = result.error ?? '反编译失败';
        this.error = errMsg;
        this.entrySelected.emit({ path: this.filePath, name: entry.name, source: '', error: errMsg });
        setTimeout(() => { this.error = ''; }, 4000);
      }
    } catch (e: any) {
      const errMsg = e.message ?? '反编译失败';
      this.error = errMsg;
      this.entrySelected.emit({ path: this.filePath, name: entry.name, source: '', error: errMsg });
      setTimeout(() => { this.error = ''; }, 4000);
    }
  }

  async detectFileType() {
    try { this.fileTypeResult = await this.pblService.detectFileType(this.filePath); } catch {}
  }

  async loadPeInfo() {
    const ext = this.filePath.toLowerCase();
    if (!ext.endsWith('.exe') && !ext.endsWith('.dll')) return;
    try {
      this.peInfo = await this.pblService.analyzePe(this.filePath);
      this.showPeDetails = true;
    } catch {}
  }

  async loadEntries() {
    if (!this.filePath) return;
    this.loading = true;
    this.loadingMsg = '分析条目...';
    this.error = '';
    try {
      const result = await this.pblService.listDecompileEntries(this.filePath);
      if (result.success) {
        this.entries = result.entries;
        this.rebuildGroups();
      } else {
        this.error = result.error ?? '无法解析文件';
      }
    } catch (e: any) {
      this.error = e.message ?? '分析失败';
    } finally {
      this.loading = false;
    }
  }

  async extractEmbedded() {
    try {
      const selected = await open({ directory: true, multiple: false, title: '选择 PBD 提取输出目录' });
      if (!selected) return;
      this.loading = true;
      this.loadingMsg = '提取嵌入 PBD...';
      const result = await this.pblService.extractPbdFromExe(this.filePath, selected as string);
      if (result.success) {
        this.extractResult = { pbd_count: result.pbd_count, output_path: result.output_path };
      } else {
        this.error = result.error ?? '提取失败';
      }
    } catch (e: any) {
      this.error = e.message ?? '提取失败';
    } finally {
      this.loading = false;
    }
  }

  async exportAllEntries() {
    try {
      const selected = await open({ directory: true, multiple: false, title: '选择源码导出目录' });
      if (!selected) return;
      this.loading = true;
      this.loadingMsg = '导出源码...';
      const msg = await this.pblService.decompileAll(this.filePath, selected as string);
      this.extractResult = { pbd_count: 0, output_path: msg };
    } catch (e: any) {
      this.error = e.message ?? '导出失败';
    } finally {
      this.loading = false;
    }
  }

  typeIcon(type: string): string {
    const m: Record<string, string> = {
      window: 'web_asset', datawindow: 'table_chart', menu: 'menu',
      function: 'functions', structure: 'schema', userobject: 'widgets',
      application: 'rocket_launch', query: 'manage_search',
      pipeline: 'account_tree', project: 'folder_special',
      proxy: 'swap_horiz', binary: 'memory', unknown: 'help_outline'
    };
    return m[type.toLowerCase()] ?? 'description';
  }

  typeColor(type: string): string {
    const m: Record<string, string> = {
      window: '#60a5fa', datawindow: '#a78bfa', menu: '#34d399',
      function: '#fbbf24', structure: '#f87171', userobject: '#22d3ee',
      application: '#c084fc', query: '#818cf8', pipeline: '#2dd4bf',
      project: '#6366f1', proxy: '#8b5cf6', binary: '#9ca3af', unknown: '#6b7280'
    };
    return m[type.toLowerCase()] ?? '#6b7280';
  }

  formatSize(bytes: number): string {
    if (!bytes) return '0 B';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }
}
