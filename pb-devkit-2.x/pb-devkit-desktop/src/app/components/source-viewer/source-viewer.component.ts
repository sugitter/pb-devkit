import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-source-viewer',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="source-viewer">
      <div class="viewer-header">
        <div class="file-tab">
          <span class="tab-icon">📝</span>
          <span class="tab-name">{{ entryName }}</span>
        </div>
        <div class="viewer-actions">
          <button class="btn-action" (click)="copySource()" title="复制代码">📋 复制</button>
          <button class="btn-action" (click)="toggleWrap()" title="折行">↩ 折行</button>
        </div>
      </div>

      @if (source) {
        <div class="code-container" [class.wrap]="wordWrap">
          <div class="line-numbers">
            @for (line of lines; track $index) {
              <div class="line-num">{{ $index + 1 }}</div>
            }
          </div>
          <pre class="code-content" #codeEl>{{ source }}</pre>
        </div>
        <div class="status-bar">
          <span>{{ lines.length }} 行</span>
          <span>{{ source.length }} 字符</span>
          @if (copied) {
            <span class="copied-msg">✓ 已复制</span>
          }
        </div>
      } @else if (!entryName) {
        <div class="empty-state">
          <div class="empty-icon">📄</div>
          <p>选择一个 PBL 对象查看源码</p>
        </div>
      } @else {
        <div class="empty-state">
          <div class="empty-icon">🔒</div>
          <p>此对象为编译对象，无法查看源码</p>
        </div>
      }
    </div>
  `,
  styles: [`
    .source-viewer { display: flex; flex-direction: column; height: 100%; background: #1e1e2e; color: #cdd6f4; }
    .viewer-header { display: flex; align-items: center; justify-content: space-between; padding: 0 1rem; background: #181825; border-bottom: 1px solid #313244; height: 40px; }
    .file-tab { display: flex; align-items: center; gap: 0.5rem; font-size: 0.875rem; }
    .tab-icon { font-size: 1rem; }
    .tab-name { color: #cba6f7; font-family: monospace; }
    .viewer-actions { display: flex; gap: 0.5rem; }
    .btn-action { padding: 0.25rem 0.5rem; background: #313244; border: none; border-radius: 4px; color: #cdd6f4; cursor: pointer; font-size: 0.75rem; }
    .btn-action:hover { background: #45475a; }
    .code-container { flex: 1; display: flex; overflow: auto; font-family: 'Consolas', 'JetBrains Mono', monospace; font-size: 0.85rem; line-height: 1.6; }
    .line-numbers { min-width: 40px; text-align: right; padding: 1rem 0.5rem; color: #585b70; background: #181825; user-select: none; }
    .line-num { height: 1.6em; }
    .code-content { flex: 1; margin: 0; padding: 1rem; overflow-x: auto; white-space: pre; color: #cdd6f4; background: transparent; }
    .wrap .code-content { white-space: pre-wrap; word-break: break-all; }
    .status-bar { display: flex; gap: 1.5rem; padding: 0.25rem 1rem; background: #181825; border-top: 1px solid #313244; font-size: 0.75rem; color: #6c7086; }
    .copied-msg { color: #a6e3a1; }
    .empty-state { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #585b70; }
    .empty-icon { font-size: 3rem; margin-bottom: 1rem; }
    .empty-state p { font-size: 0.875rem; }
  `]
})
export class SourceViewerComponent implements OnChanges {
  @Input() entryName = '';
  @Input() source = '';

  wordWrap = false;
  copied = false;
  lines: string[] = [];

  ngOnChanges(changes: SimpleChanges) {
    if (changes['source']) {
      this.lines = this.source ? this.source.split('\n') : [];
    }
  }

  toggleWrap() { this.wordWrap = !this.wordWrap; }

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