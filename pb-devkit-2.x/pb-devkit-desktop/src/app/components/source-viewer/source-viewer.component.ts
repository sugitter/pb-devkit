import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

// PowerScript 语法高亮器（纯前端，无外部依赖）
function highlightPowerScript(code: string): string {
  // 先把整个代码转义 HTML，再逐步还原高亮
  const escapeHtml = (s: string) =>
    s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  // 按行高亮，避免跨行的正则问题
  const lines = code.split('\n');
  const highlighted = lines.map(rawLine => {
    // 先整体转义
    let line = escapeHtml(rawLine);

    // 1. 行注释 // ... （必须最先做，避免注释内容被误着色）
    //    只处理不在字符串内的 //（简化：只处理行首或 // 出现的位置）
    const commentIdx = rawLine.indexOf('//');
    if (commentIdx >= 0) {
      // 判断 // 是否在字符串内（简化判断：数奇数个引号在前面则在字符串中，跳过）
      const before = rawLine.slice(0, commentIdx);
      const dqCount = (before.match(/"/g) ?? []).length;
      if (dqCount % 2 === 0) {
        // 不在字符串内，是注释
        const codePart = escapeHtml(rawLine.slice(0, commentIdx));
        const commentPart = escapeHtml(rawLine.slice(commentIdx));
        line = applyKeywordsAndStrings(codePart) + `<span class="ps-comment">${commentPart}</span>`;
        return line;
      }
    }

    line = applyKeywordsAndStrings(line);
    return line;
  });

  return highlighted.join('\n');
}

function applyKeywordsAndStrings(line: string): string {
  // 2. 字符串（双引号，已转义 &quot; 或 "）
  line = line.replace(/"([^"]*)"/g, '<span class="ps-string">&quot;$1&quot;</span>');

  // 3. PowerScript 关键字（大小写不敏感，加 \b 边界）
  const keywords = [
    'if', 'then', 'else', 'elseif', 'end if',
    'for', 'to', 'step', 'next',
    'do', 'while', 'until', 'loop',
    'choose case', 'case', 'end choose',
    'return', 'exit',
    'function', 'end function',
    'subroutine', 'end subroutine',
    'event', 'end event',
    'on', 'end on',
    'try', 'catch', 'finally', 'end try', 'throw',
    'not', 'and', 'or',
    'true', 'false',
    'null',
    'this', 'super', 'parent',
    'string', 'integer', 'long', 'double', 'boolean', 'date', 'time', 'datetime',
    'any', 'blob', 'char', 'decimal', 'real', 'uint', 'ulong',
    'datastore', 'datawindow', 'window', 'menu',
    'create', 'destroy',
    'open', 'close',
    'messagebox',
    'type', 'end type',
    'variables', 'end variables',
    'forward', 'end forward',
    'prototypes', 'end prototypes',
    'global type', 'end global',
    'shared variables',
    'local', 'global', 'shared', 'protected', 'private', 'public',
    'constant', 'ref',
    'readonly', 'indirect',
    'using', 'commit', 'rollback',
    'connect', 'disconnect',
    'select', 'insert', 'update', 'delete', 'where', 'from', 'into',
  ];

  // 按长度降序排列，避免短词提前匹配（如 "if" 匹配了 "elseif"）
  keywords.sort((a, b) => b.length - a.length);

  for (const kw of keywords) {
    // 将关键字中空格替换为 \s+ 匹配
    const pattern = kw.replace(/\s+/g, '\\s+');
    const regex = new RegExp(`(?<![\\w])${pattern}(?![\\w])`, 'gi');
    line = line.replace(regex, m => `<span class="ps-keyword">${m}</span>`);
  }

  // 4. 数字
  line = line.replace(/(?<![a-zA-Z_])(\d+\.?\d*)/g,
    '<span class="ps-number">$1</span>');

  return line;
}

@Component({
  selector: 'app-source-viewer',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="source-viewer">
      <div class="viewer-header">
        <div class="file-tab">
          <span class="tab-icon"><span class="material-icons">description</span></span>
          <span class="tab-name">{{ entryName }}</span>
        </div>
        <div class="viewer-actions">
          <button class="btn-action" [class.active]="highlightEnabled" (click)="toggleHighlight()" title="语法高亮">
            <span class="material-icons" style="font-size:14px">palette</span> 高亮
          </button>
          <button class="btn-action" (click)="copySource()" title="复制代码">
            <span class="material-icons" style="font-size:14px">content_copy</span> 复制
          </button>
          <button class="btn-action" (click)="toggleWrap()" title="折行">
            <span class="material-icons" style="font-size:14px">wrap_text</span> 折行
          </button>
        </div>
      </div>

      @if (hasSource) {
        <div class="code-container" [class.wrap]="wordWrap">
          <div class="line-numbers">
            @for (line of lines; track $index) {
              <div class="line-num">{{ $index + 1 }}</div>
            }
          </div>
          @if (highlightEnabled) {
            <pre class="code-content highlighted" [innerHTML]="highlightedSource"></pre>
          } @else {
            <pre class="code-content">{{ source }}</pre>
          }
        </div>
        <div class="status-bar">
          <span>{{ lines.length }} 行</span>
          <span>{{ source.length }} 字符</span>
          @if (copied) {
            <span class="copied-msg"><span class="material-icons" style="font-size:14px">check</span> 已复制</span>
          }
        </div>
      } @else if (!entryName) {
        <div class="empty-state">
          <div class="empty-icon"><span class="material-icons mi-xl">description</span></div>
          <p>双击左侧对象查看源码</p>
        </div>
      } @else if (loadError) {
        <div class="empty-state">
          <div class="empty-icon"><span class="material-icons mi-xl" style="color:#f87171">error_outline</span></div>
          <p style="color:#f87171">{{ loadError }}</p>
        </div>
      } @else {
        <div class="empty-state">
          <div class="empty-icon"><span class="material-icons mi-xl">hourglass_empty</span></div>
          <p>加载中...</p>
        </div>
      }
    </div>
  `,
  styles: [`
    .source-viewer { display: flex; flex-direction: column; height: 100%; background: #1e1e2e; color: #cdd6f4; }
    .viewer-header { display: flex; align-items: center; justify-content: space-between; padding: 0 1rem; background: #181825; border-bottom: 1px solid #313244; height: 40px; flex-shrink: 0; }
    .file-tab { display: flex; align-items: center; gap: 0.5rem; font-size: 0.875rem; }
    .tab-icon .material-icons { font-size: 16px; color: #89b4fa; }
    .tab-name { color: #89b4fa; font-family: monospace; font-weight: 500; }
    .viewer-actions { display: flex; gap: 0.35rem; }
    .btn-action { padding: 0.2rem 0.5rem; background: #313244; border: 1px solid #45475a; border-radius: 4px; color: #a6adc8; cursor: pointer; font-size: 0.72rem; display: flex; align-items: center; gap: 0.2rem; }
    .btn-action:hover { background: #45475a; color: #cdd6f4; }
    .btn-action.active { background: #cba6f7; border-color: #cba6f7; color: #1e1e2e; }
    .code-container { flex: 1; display: flex; overflow: auto; font-family: 'Consolas', 'JetBrains Mono', 'Courier New', monospace; font-size: 0.84rem; line-height: 1.65; }
    .line-numbers { min-width: 44px; text-align: right; padding: 1rem 0.5rem; color: #45475a; background: #181825; user-select: none; border-right: 1px solid #313244; flex-shrink: 0; }
    .line-num { height: 1.65em; }
    .code-content { flex: 1; margin: 0; padding: 1rem; overflow-x: auto; white-space: pre; color: #cdd6f4; background: #1e1e2e; }
    .wrap .code-content { white-space: pre-wrap; word-break: break-all; }
    .status-bar { display: flex; gap: 1.5rem; padding: 0.25rem 1rem; background: #181825; border-top: 1px solid #313244; font-size: 0.72rem; color: #6c7086; flex-shrink: 0; }
    .copied-msg { color: #a6e3a1; font-weight: 500; }
    .empty-state { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #6c7086; }
    .empty-icon { font-size: 3rem; margin-bottom: 1rem; }
    .empty-state p { font-size: 0.875rem; }
    /* PowerScript 语法高亮色（Catppuccin Mocha 风格） */
    :host ::ng-deep .ps-keyword { color: #cba6f7; font-weight: 600; }
    :host ::ng-deep .ps-string { color: #a6e3a1; }
    :host ::ng-deep .ps-comment { color: #6c7086; font-style: italic; }
    :host ::ng-deep .ps-number { color: #fab387; }
  `]
})
export class SourceViewerComponent implements OnChanges {
  @Input() entryName = '';
  @Input() source = '';
  @Input() loadError = '';

  wordWrap = false;
  copied = false;
  highlightEnabled = true;
  lines: string[] = [];
  highlightedSource = '';

  /** source 非 null 且非 undefined 时认为有源码（空字符串也算有，表示文件内容为空） */
  get hasSource(): boolean {
    return this.source !== null && this.source !== undefined && this.source.length > 0;
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['source']) {
      this.lines = this.source ? this.source.split('\n') : [];
      this.rebuildHighlight();
    }
  }

  toggleWrap() { this.wordWrap = !this.wordWrap; }

  toggleHighlight() {
    this.highlightEnabled = !this.highlightEnabled;
    if (this.highlightEnabled) this.rebuildHighlight();
  }

  rebuildHighlight() {
    this.highlightedSource = this.source ? highlightPowerScript(this.source) : '';
  }

  async copySource() {
    if (!this.source) return;
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(this.source);
      } else {
        // Fallback for Tauri webview
        const textarea = document.createElement('textarea');
        textarea.value = this.source;
        textarea.style.position = 'fixed';
        textarea.style.left = '-9999px';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      this.copied = true;
      setTimeout(() => (this.copied = false), 2000);
    } catch {}
  }
}