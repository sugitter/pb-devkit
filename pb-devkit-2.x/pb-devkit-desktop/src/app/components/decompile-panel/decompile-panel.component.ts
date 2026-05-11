import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { open } from '@tauri-apps/plugin-dialog';
import { PblService, DecompileEntry, FileTypeResult, PeInfoResult } from '../../services/pbl.service';

type FilterType = 'all' | 'source' | 'compiled';

@Component({
  selector: 'app-decompile-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="decompile-panel">

      <!-- 文件信息头 -->
      <div class="panel-header">
        <div class="file-info">
          <span class="file-icon"><span class="material-icons">{{ fileIcon }}</span></span>
          <div class="file-details">
            <div class="file-name">{{ fileName }}</div>
            @if (fileTypeResult) {
              <div class="file-meta">
                {{ fileTypeResult.file_type.toUpperCase() }}
                @if (fileTypeResult.is_pb_exe) { · PB可执行文件 }
                · {{ formatSize(fileTypeResult.size) }}
              </div>
            }
          </div>
        </div>
        <div class="header-actions">
          <button class="btn-sm" (click)="exportAllEntries()" [disabled]="!entries.length || loading"
                  title="导出全部源码">
            <span class="material-icons" style="font-size:14px">download</span> 导出全部
          </button>
        </div>
      </div>

      <!-- PE 详细信息（仅 EXE/DLL） -->
      @if (peInfo) {
        <div class="pe-info-section">
          <div class="pe-header" (click)="showPeDetails = !showPeDetails">
            <span><span class="material-icons" style="font-size:14px;vertical-align:middle">computer</span> PE 分析</span>
            <span class="pe-toggle"><span class="material-icons">{{ showPeDetails ? 'expand_more' : 'chevron_right' }}</span></span>
          </div>
          @if (showPeDetails) {
            <div class="pe-details">
              <div class="pe-row">
                <span class="pe-label">架构</span>
                <span class="pe-value">{{ peInfo.is_64bit ? '64-bit' : '32-bit' }} ({{ peInfo.machine_type }})</span>
              </div>
              @if (peInfo.timestamp) {
                <div class="pe-row">
                  <span class="pe-label">编译时间</span>
                  <span class="pe-value">{{ peInfo.timestamp }}</span>
                </div>
              }
              <div class="pe-row">
                <span class="pe-label">PB 可执行</span>
                <span class="pe-value" [class.highlight]="peInfo.is_pb_exe">{{ peInfo.is_pb_exe ? '是' : '否' }}</span>
              </div>
              @if (peInfo.embedded_pbl_count > 0) {
                <div class="pe-row">
                  <span class="pe-label">嵌入 PBD</span>
                  <span class="pe-value highlight">{{ peInfo.embedded_pbl_count }} 个</span>
                </div>
              }
              @if (peInfo.resources.length > 0) {
                <div class="pe-resources">
                  <div class="pe-row"><span class="pe-label">嵌入资源</span></div>
                  @for (res of peInfo.resources; track res.name) {
                    <div class="resource-item">
                      <span class="res-name">{{ res.name }}</span>
                      <span class="res-meta">{{ res.resource_type }} · {{ formatSize(res.size) }}</span>
                    </div>
                  }
                </div>
              }
            </div>
          }
        </div>
      }

      <!-- 状态/操作区 -->
      @if (!entries.length && !loading && !error) {
        <div class="action-area">
          <button class="btn-primary" (click)="loadEntries()">
            <span class="material-icons" style="font-size:16px;vertical-align:middle">search</span> 分析文件
          </button>
          @if (filePath.toLowerCase().endsWith('.exe') || filePath.toLowerCase().endsWith('.dll')) {
            <button class="btn-secondary" (click)="extractEmbedded()">
              <span class="material-icons" style="font-size:16px;vertical-align:middle">inventory_2</span> 提取嵌入 PBD
            </button>
          }
        </div>
      }

      @if (loading) {
        <div class="loading-state">
          <div class="spinner"></div>
          <span>{{ loadingMsg }}</span>
        </div>
      }

      @if (error) {
        <div class="error-state">
          <span class="error-icon"><span class="material-icons" style="font-size:16px">warning</span></span>
          <span>{{ error }}</span>
          <button class="btn-dismiss" (click)="error = ''"><span class="material-icons" style="font-size:16px">close</span></button>
        </div>
      }

      @if (entries.length > 0) {
        <!-- 统计栏 -->
        <div class="stats-bar">
          <span class="stat" [class.active]="filter==='all'" (click)="filter='all'">
            全部 {{ entries.length }}
          </span>
          <span class="stat" [class.active]="filter==='source'" (click)="filter='source'">
            <span class="material-icons" style="font-size:14px">description</span> 源码 {{ sourceCount }}
          </span>
          <span class="stat" [class.active]="filter==='compiled'" (click)="filter='compiled'">
            <span class="material-icons" style="font-size:14px">build</span> 编译 {{ compiledCount }}
          </span>
        </div>

        <!-- 过滤框 -->
        <div class="filter-bar">
          <input [(ngModel)]="searchQuery" placeholder="过滤对象名..." class="filter-input" />
        </div>

        <!-- 条目列表 -->
        <div class="entries-list">
          @for (entry of filteredEntries; track entry.name) {
            <div class="entry-item"
                 [class.selected]="selectedEntry?.name === entry.name"
                 (click)="selectEntry(entry)">
              <span class="type-badge"><span class="material-icons" style="font-size:16px">{{ typeIcon(entry.entry_type) }}</span></span>
              <div class="entry-info">
                <span class="entry-name">{{ entry.name }}</span>
                <span class="entry-meta">
                  {{ entry.entry_type }}
                  @if (entry.size > 0) { · {{ formatSize(entry.size) }} }
                  @if (!entry.is_source) { · 仅编译 }
                </span>
              </div>
              @if (entry.is_source) {
                <button class="btn-view" (click)="viewEntry(entry, $event)">查看</button>
              } @else {
                <span class="compiled-badge">编译</span>
              }
            </div>
          }

          @if (filteredEntries.length === 0) {
            <div class="empty-state">暂无匹配对象</div>
          }
        </div>
      }

      <!-- 提取成功提示 -->
      @if (extractResult) {
        <div class="extract-result">
          <span class="material-icons" style="font-size:16px;color:#059669">check_circle</span> 已提取 {{ extractResult.pbd_count }} 个 PBD 到：
          <code>{{ extractResult.output_path }}</code>
        </div>
      }

    </div>
  `,
  styles: [`
    .decompile-panel { display: flex; flex-direction: column; height: 100%; background: #fff; font-size: 0.875rem; }

    /* 头部 */
    .panel-header { display: flex; align-items: center; justify-content: space-between; padding: 0.75rem 1rem; border-bottom: 1px solid #e5e7eb; gap: 0.75rem; }
    .file-info { display: flex; align-items: center; gap: 0.75rem; min-width: 0; }
    .file-icon { font-size: 1.5rem; flex-shrink: 0; }
    .file-details { min-width: 0; }
    .file-name { font-weight: 600; color: #111; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 180px; }
    .file-meta { font-size: 0.75rem; color: #6b7280; margin-top: 2px; }
    .header-actions { flex-shrink: 0; }

    /* PE 信息区 */
    .pe-info-section { border-bottom: 1px solid #e5e7eb; }
    .pe-header { display: flex; align-items: center; justify-content: space-between; padding: 0.5rem 1rem; background: #f0f9ff; cursor: pointer; font-size: 0.8rem; font-weight: 600; color: #1d4ed8; }
    .pe-header:hover { background: #e0f2fe; }
    .pe-toggle { font-size: 0.7rem; color: #6b7280; }
    .pe-details { padding: 0.5rem 1rem; }
    .pe-row { display: flex; align-items: baseline; gap: 0.5rem; padding: 0.2rem 0; font-size: 0.8rem; }
    .pe-label { color: #6b7280; min-width: 70px; flex-shrink: 0; }
    .pe-value { color: #111; font-family: monospace; }
    .pe-value.highlight { color: #059669; font-weight: 600; }
    .pe-resources { margin-top: 0.25rem; }
    .resource-item { display: flex; align-items: center; justify-content: space-between; padding: 0.2rem 0 0.2rem 1.5rem; font-size: 0.75rem; }
    .res-name { font-family: monospace; color: #7c3aed; }
    .res-meta { color: #9ca3af; font-size: 0.7rem; }

    /* 按钮 */
    .btn-sm { padding: 0.3rem 0.6rem; background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; font-size: 0.8rem; color: #374151; }
    .btn-sm:hover:not(:disabled) { background: #e5e7eb; }
    .btn-sm:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-primary { padding: 0.5rem 1.25rem; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.875rem; }
    .btn-primary:hover { background: #1d4ed8; }
    .btn-secondary { padding: 0.5rem 1.25rem; background: #f3f4f6; color: #374151; border: 1px solid #d1d5db; border-radius: 6px; cursor: pointer; font-size: 0.875rem; }
    .btn-secondary:hover { background: #e5e7eb; }
    .btn-dismiss { margin-left: auto; background: none; border: none; color: #dc2626; cursor: pointer; font-size: 0.9rem; }
    .btn-view { padding: 0.2rem 0.5rem; background: #eff6ff; border: 1px solid #bfdbfe; color: #2563eb; border-radius: 4px; font-size: 0.75rem; cursor: pointer; flex-shrink: 0; }
    .btn-view:hover { background: #dbeafe; }

    /* 操作区 */
    .action-area { display: flex; flex-direction: column; gap: 0.5rem; padding: 1.5rem 1rem; align-items: center; }

    /* 加载 */
    .loading-state { display: flex; align-items: center; gap: 0.75rem; padding: 2rem; justify-content: center; color: #6b7280; }
    .spinner { width: 20px; height: 20px; border: 2px solid #e5e7eb; border-top-color: #3b82f6; border-radius: 50%; animation: spin 0.8s linear infinite; flex-shrink: 0; }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* 错误 */
    .error-state { display: flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1rem; margin: 0.5rem; background: #fee2e2; color: #dc2626; border-radius: 6px; font-size: 0.8rem; }

    /* 统计栏 */
    .stats-bar { display: flex; gap: 0.5rem; padding: 0.5rem 1rem; background: #f9fafb; border-bottom: 1px solid #e5e7eb; }
    .stat { padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.8rem; cursor: pointer; color: #374151; }
    .stat:hover, .stat.active { background: #dbeafe; color: #1d4ed8; }

    /* 过滤框 */
    .filter-bar { padding: 0.5rem 1rem; border-bottom: 1px solid #e5e7eb; }
    .filter-input { width: 100%; padding: 0.4rem 0.75rem; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.875rem; box-sizing: border-box; }

    /* 列表 */
    .entries-list { flex: 1; overflow-y: auto; }
    .entry-item { display: flex; align-items: center; gap: 0.75rem; padding: 0.45rem 1rem; border-bottom: 1px solid #f3f4f6; cursor: pointer; }
    .entry-item:hover { background: #f9fafb; }
    .entry-item.selected { background: #eff6ff; }
    .type-badge { font-size: 1rem; flex-shrink: 0; width: 20px; text-align: center; }
    .entry-info { flex: 1; min-width: 0; }
    .entry-name { display: block; color: #111; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 0.875rem; }
    .entry-meta { display: block; font-size: 0.75rem; color: #9ca3af; }
    .compiled-badge { font-size: 0.7rem; color: #9ca3af; background: #f3f4f6; padding: 0.15rem 0.4rem; border-radius: 4px; flex-shrink: 0; }
    .empty-state { padding: 2rem; text-align: center; color: #9ca3af; }

    /* 提取结果 */
    .extract-result { margin: 0.75rem 1rem; padding: 0.75rem; background: #dcfce7; color: #166534; border-radius: 6px; font-size: 0.8rem; }
    .extract-result code { word-break: break-all; display: block; margin-top: 0.25rem; font-family: monospace; font-size: 0.75rem; color: #15803d; }
  `]
})
export class DecompilePanelComponent implements OnChanges {
  @Input() filePath = '';
  @Output() entrySelected = new EventEmitter<{ path: string; name: string; source: string }>();

  entries: DecompileEntry[] = [];
  selectedEntry: DecompileEntry | null = null;
  filter: FilterType = 'all';
  searchQuery = '';
  loading = false;
  loadingMsg = '分析中...';
  error = '';
  fileTypeResult: FileTypeResult | null = null;
  peInfo: PeInfoResult | null = null;
  showPeDetails = false;
  extractResult: { pbd_count: number; output_path?: string } | null = null;

  constructor(private pblService: PblService) {}

  ngOnChanges(changes: SimpleChanges) {
    if (changes['filePath'] && this.filePath) {
      this.reset();
      this.detectFileType();
      this.loadPeInfo();
    }
  }

  reset() {
    this.entries = [];
    this.selectedEntry = null;
    this.error = '';
    this.extractResult = null;
    this.fileTypeResult = null;
    this.peInfo = null;
    this.showPeDetails = false;
  }

  get fileName(): string {
    return this.filePath.split(/[\\/]/).pop() ?? this.filePath;
  }

  get fileIcon(): string {
    const name = this.fileName.toLowerCase();
    if (name.endsWith('.exe')) return 'settings';
    if (name.endsWith('.pbd')) return 'lock_open';
    if (name.endsWith('.dll')) return 'build';
    return 'folder';
  }

  get sourceCount(): number {
    return this.entries.filter(e => e.is_source).length;
  }

  get compiledCount(): number {
    return this.entries.filter(e => !e.is_source).length;
  }

  get filteredEntries(): DecompileEntry[] {
    let list = this.entries;
    if (this.filter === 'source') list = list.filter(e => e.is_source);
    if (this.filter === 'compiled') list = list.filter(e => !e.is_source);
    if (this.searchQuery.trim()) {
      const q = this.searchQuery.toLowerCase();
      list = list.filter(e => e.name.toLowerCase().includes(q));
    }
    return list;
  }

  async detectFileType() {
    try {
      this.fileTypeResult = await this.pblService.detectFileType(this.filePath);
    } catch {}
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
      const selected = await open({
        directory: true,
        multiple: false,
        title: '选择 PBD 提取输出目录'
      });
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

  selectEntry(entry: DecompileEntry) {
    this.selectedEntry = entry;
  }

  async viewEntry(entry: DecompileEntry, event: Event) {
    event.stopPropagation();
    try {
      const result = await this.pblService.decompileEntry(this.filePath, entry.name);
      if (result.success && result.source) {
        this.entrySelected.emit({ path: this.filePath, name: entry.name, source: result.source });
      } else {
        this.error = result.error ?? '反编译失败';
      }
    } catch (e: any) {
      this.error = e.message ?? '反编译失败';
    }
  }

  async exportAllEntries() {
    try {
      const selected = await open({
        directory: true,
        multiple: false,
        title: '选择源码导出目录'
      });
      if (!selected) return;

      this.loading = true;
      this.loadingMsg = '导出源码...';
      const msg = await this.pblService.decompileAll(this.filePath, selected as string);
      this.error = '';
      this.extractResult = { pbd_count: 0, output_path: msg };
    } catch (e: any) {
      this.error = e.message ?? '导出失败';
    } finally {
      this.loading = false;
    }
  }

  typeIcon(type: string): string {
    const icons: Record<string, string> = {
      window: 'window', datawindow: 'bar_chart', menu: 'menu', function: 'functions',
      structure: 'diamond', userobject: 'extension', application: 'rocket_launch',
      query: 'search', pipeline: 'link', project: 'assignment', proxy: 'sync',
      binary: 'pin', unknown: 'help'
    };
    return icons[type.toLowerCase()] ?? 'description';
  }

  formatSize(bytes: number): string {
    if (!bytes) return '0 B';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }
}
