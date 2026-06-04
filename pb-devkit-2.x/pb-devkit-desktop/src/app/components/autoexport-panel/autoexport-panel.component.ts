import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { invoke } from '@tauri-apps/api/core';
import { open } from '@tauri-apps/plugin-dialog';

type Stage = 'idle' | 'scanning' | 'exporting' | 'done' | 'error';

interface ExportStep {
  label: string;
  status: 'pending' | 'running' | 'done' | 'error';
  detail: string;
}

@Component({
  selector: 'app-autoexport-panel',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="autoexport-panel">
      <div class="panel-header">
        <h3><span class="material-icons" style="vertical-align:middle">download</span> 一键导出</h3>
        @if (stage !== 'scanning' && stage !== 'exporting') {
          <button class="btn-close" (click)="onClose.emit()" title="关闭">
            <span class="material-icons">close</span>
          </button>
        }
      </div>

      <!-- Source / Output selection -->
      @if (stage === 'idle') {
        <div class="config-section">
          <div class="config-row">
            <label>源码目录</label>
            <div class="input-group">
              <input type="text" [value]="srcDir" readonly placeholder="选择 PB 源码目录..." />
              <button class="btn-browse" (click)="selectSrcDir()">
                <span class="material-icons" style="font-size:18px">folder_open</span>
              </button>
            </div>
          </div>
          <div class="config-row">
            <label>输出目录</label>
            <div class="input-group">
              <input type="text" [value]="outputDir" readonly placeholder="选择输出目录..." />
              <button class="btn-browse" (click)="selectOutputDir()">
                <span class="material-icons" style="font-size:18px">folder_open</span>
              </button>
            </div>
          </div>
          <button class="btn-run" (click)="doAutoExport()" [disabled]="!srcDir || !outputDir">
            <span class="material-icons" style="font-size:18px;vertical-align:middle">rocket_launch</span>
            开始导出
          </button>

          <!-- Quick actions row -->
          <div class="quick-row">
            <button class="btn-quick" (click)="doMigrateWeb()" [disabled]="!srcDir || !outputDir || migrating">
              <span class="material-icons" style="font-size:16px;vertical-align:middle">web</span>
              {{ migrating ? '转换中...' : '转 Web 项目' }}
            </button>
            <button class="btn-quick" (click)="doPackPbl()" [disabled]="!srcDir || !outputDir || packing">
              <span class="material-icons" style="font-size:16px;vertical-align:middle">inventory_2</span>
              {{ packing ? '打包中...' : '重打包 PBL' }}
            </button>
          </div>
          @if (quickMsg) {
            <div class="quick-msg" [class.quick-err]="quickMsgIsError">{{ quickMsg }}</div>
          }
        </div>
      }

      <!-- Progress -->
      @if (stage === 'scanning' || stage === 'exporting') {
        <div class="progress-section">
          <div class="progress-bar-wrapper">
            <div class="progress-bar" [style.width.%]="progressPct"></div>
          </div>
          <span class="progress-text">{{ progressPct }}%</span>
        </div>
        <div class="steps-list">
          @for (step of steps; track step.label) {
            <div class="step-item" [class.running]="step.status==='running'" [class.done]="step.status==='done'" [class.error]="step.status==='error'">
              <span class="step-icon">
                @if (step.status === 'running') { <span class="material-icons spin">sync</span> }
                @if (step.status === 'done') { <span class="material-icons">check_circle</span> }
                @if (step.status === 'error') { <span class="material-icons">cancel</span> }
                @if (step.status === 'pending') { <span class="material-icons">radio_button_unchecked</span> }
              </span>
              <span class="step-label">{{ step.label }}</span>
              @if (step.detail) { <span class="step-detail">{{ step.detail }}</span> }
            </div>
          }
        </div>
      }

      <!-- Done state -->
      @if (stage === 'done') {
        <div class="result-section">
          <div class="result-header ok">
            <span class="material-icons">check_circle</span>
            <span>导出完成！</span>
          </div>
          <div class="result-stats">
            <div class="stat">
              <span class="stat-value">{{ resultSrcCount }}</span>
              <span class="stat-label">源码文件</span>
            </div>
            <div class="stat">
              <span class="stat-value">{{ resultPblCount }}</span>
              <span class="stat-label">PBL 文件</span>
            </div>
          </div>
          <div class="result-path">
            <span class="material-icons" style="font-size:16px;vertical-align:middle">folder</span>
            {{ resultOutputDir }}
          </div>
          <div class="result-actions">
            <button class="btn-secondary" (click)="reset()">
              <span class="material-icons" style="font-size:16px;vertical-align:middle">refresh</span>
              重新导出
            </button>
          </div>
        </div>
      }

      <!-- Error state -->
      @if (stage === 'error') {
        <div class="result-section">
          <div class="result-header error">
            <span class="material-icons">cancel</span>
            <span>导出失败</span>
          </div>
          <p class="error-msg">{{ errorMsg }}</p>
          <div class="result-actions">
            <button class="btn-secondary" (click)="reset()">重试</button>
          </div>
        </div>
      }

      <!-- History -->
      @if (history.length > 0 && stage === 'idle') {
        <div class="history-section">
          <h4>操作历史</h4>
          @for (h of history; track h.time) {
            <div class="history-item" [class.hist-ok]="h.ok" [class.hist-err]="!h.ok">
              <span class="material-icons" style="font-size:14px">{{ h.ok ? 'check_circle' : 'cancel' }}</span>
              <span>{{ h.time }} — {{ h.summary }}</span>
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .autoexport-panel {
      display: flex;
      flex-direction: column;
      height: 100%;
      overflow-y: auto;
      background: #1e1e2e;
      color: #cdd6f4;
    }
    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.75rem 1rem;
      border-bottom: 1px solid #313244;
    }
    .panel-header h3 { margin: 0; font-size: 0.9rem; color: #cdd6f4; }
    .btn-close {
      background: none; border: none; color: #6c7086; cursor: pointer;
      padding: 4px; border-radius: 4px;
    }
    .btn-close:hover { color: #cdd6f4; background: #313244; }

    /* Config */
    .config-section {
      padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem;
    }
    .config-row { display: flex; flex-direction: column; gap: 0.3rem; }
    .config-row label { font-size: 0.78rem; color: #a6adc8; font-weight: 500; }
    .input-group { display: flex; gap: 0.4rem; }
    .input-group input {
      flex: 1; padding: 0.45rem 0.6rem; background: #181825; border: 1px solid #313244;
      border-radius: 6px; color: #cdd6f4; font-size: 0.8rem; outline: none;
    }
    .input-group input:focus { border-color: #cba6f7; }
    .btn-browse {
      padding: 0.45rem 0.6rem; background: #313244; border: 1px solid #45475a;
      border-radius: 6px; color: #cdd6f4; cursor: pointer;
    }
    .btn-browse:hover { background: #45475a; }
    .btn-run {
      margin-top: 0.5rem; padding: 0.6rem 1.2rem;
      background: #cba6f7; color: #1e1e2e; border: none; border-radius: 8px;
      cursor: pointer; font-size: 0.85rem; font-weight: 600; align-self: flex-start;
    }
    .btn-run:disabled { opacity: 0.4; cursor: not-allowed; }
    .btn-run:hover:not(:disabled) { background: #b4befe; }

    /* Progress */
    .progress-section {
      display: flex; align-items: center; gap: 0.75rem; padding: 0 1rem;
    }
    .progress-bar-wrapper {
      flex: 1; height: 6px; background: #313244; border-radius: 3px; overflow: hidden;
    }
    .progress-bar {
      height: 100%; background: linear-gradient(90deg, #cba6f7, #f5c2e7);
      border-radius: 3px; transition: width 0.3s ease;
    }
    .progress-text { font-size: 0.8rem; color: #a6adc8; min-width: 36px; text-align: right; }
    .steps-list {
      display: flex; flex-direction: column; gap: 0.3rem; padding: 0.75rem 1rem;
    }
    .step-item {
      display: flex; align-items: center; gap: 0.5rem; padding: 0.45rem 0.6rem;
      border-radius: 6px; font-size: 0.8rem;
    }
    .step-item.running { background: rgba(203, 166, 247, 0.1); color: #cba6f7; }
    .step-item.done { color: #a6e3a1; }
    .step-item.error { background: rgba(243, 139, 168, 0.1); color: #f38ba8; }
    .step-item.pending { color: #6c7086; }
    .step-icon { width: 20px; text-align: center; }
    .step-detail { margin-left: auto; font-size: 0.72rem; color: #6c7086; }
    .spin { animation: spin 1s linear infinite; }
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

    /* Result */
    .result-section { padding: 1rem; }
    .result-header {
      display: flex; align-items: center; gap: 0.4rem; font-size: 0.95rem; font-weight: 600;
      margin-bottom: 0.75rem;
    }
    .result-header.ok .material-icons { color: #a6e3a1; }
    .result-header.ok { color: #a6e3a1; }
    .result-header.error .material-icons { color: #f38ba8; }
    .result-header.error { color: #f38ba8; }
    .result-stats { display: flex; gap: 1rem; margin-bottom: 0.75rem; }
    .stat {
      background: #181825; border: 1px solid #313244; border-radius: 8px;
      padding: 0.6rem 1rem; text-align: center; min-width: 80px;
    }
    .stat-value { display: block; font-size: 1.2rem; font-weight: 700; color: #cba6f7; }
    .stat-label { font-size: 0.72rem; color: #6c7086; }
    .result-path {
      padding: 0.5rem 0.6rem; background: #181825; border-radius: 6px;
      font-size: 0.78rem; color: #a6adc8; word-break: break-all;
    }
    .error-msg { color: #f38ba8; font-size: 0.82rem; margin: 0 0 0.75rem; }
    .result-actions { margin-top: 0.75rem; }
    .btn-secondary {
      padding: 0.4rem 0.9rem; border: 1px solid #45475a; border-radius: 6px;
      background: transparent; color: #cdd6f4; cursor: pointer; font-size: 0.8rem;
    }
    .btn-secondary:hover { background: #313244; }

    /* Quick actions row */
    .quick-row {
      display: flex; gap: 0.5rem; margin-top: 0.5rem;
    }
    .btn-quick {
      flex: 1; padding: 0.45rem 0.6rem;
      background: #181825; border: 1px solid #45475a; border-radius: 6px;
      color: #a6adc8; cursor: pointer; font-size: 0.78rem; display: flex;
      align-items: center; justify-content: center; gap: 0.3rem;
    }
    .btn-quick:hover:not(:disabled) { background: #313244; color: #cdd6f4; border-color: #6c7086; }
    .btn-quick:disabled { opacity: 0.4; cursor: not-allowed; }
    .quick-msg {
      margin-top: 0.5rem; padding: 0.45rem 0.6rem; border-radius: 6px;
      font-size: 0.78rem; background: rgba(166, 227, 161, 0.1); color: #a6e3a1;
    }
    .quick-msg.quick-err {
      background: rgba(243, 139, 168, 0.1); color: #f38ba8;
    }

    /* History */
    .history-section {
      border-top: 1px solid #313244; padding: 0.75rem 1rem;
    }
    .history-section h4 { margin: 0 0 0.5rem; font-size: 0.8rem; color: #a6adc8; }
    .history-item {
      display: flex; align-items: center; gap: 0.4rem; padding: 0.3rem 0;
      font-size: 0.75rem;
    }
    .hist-ok { color: #a6adc8; }
    .hist-err { color: #f38ba8; }
  `]
})
export class AutoexportPanelComponent implements OnInit {
  @Input() projectPath?: string;
  @Output() onClose = new EventEmitter<void>();

  // Config
  srcDir = '';
  outputDir = '';

  // State
  stage: Stage = 'idle';
  steps: ExportStep[] = [];
  progressPct = 0;
  errorMsg = '';
  resultSrcCount = 0;
  resultPblCount = 0;
  resultOutputDir = '';

  // Operation history
  history: { time: string; summary: string; ok: boolean }[] = [];

  // Quick-action state
  migrating = false;
  packing = false;
  quickMsg = '';
  quickMsgIsError = false;

  ngOnInit() {
    if (this.projectPath) {
      this.srcDir = this.projectPath;
      this.outputDir = this.projectPath + '/exported_src';
    }
  }

  async selectSrcDir() {
    try {
      const dir = await open({ directory: true, multiple: false, title: '选择 PB 项目源码目录' });
      if (dir) this.srcDir = dir as string;
    } catch (_) { /* user cancelled */ }
  }

  async selectOutputDir() {
    try {
      const dir = await open({ directory: true, multiple: false, title: '选择导出目标目录' });
      if (dir) this.outputDir = dir as string;
    } catch (_) { /* user cancelled */ }
  }

  async doAutoExport() {
    if (!this.srcDir || !this.outputDir) return;

    this.stage = 'scanning';
    this.steps = [
      { label: '扫描项目结构', status: 'running', detail: '' },
      { label: '发现 PBL 文件', status: 'pending', detail: '' },
      { label: '导出源码 (.sr*)', status: 'pending', detail: '' },
      { label: '提取 DataWindow SQL', status: 'pending', detail: '' },
      { label: '生成索引文件', status: 'pending', detail: '' },
    ];
    this.progressPct = 0;
    this.errorMsg = '';

    try {
      // Step 1: scanning
      this._tick(1, 10);
      await this._delay(300);

      // Step 2: discover PBLs
      this.steps[0].status = 'done';
      this.steps[1].status = 'running';
      this._tick(2, 25);
      await this._delay(300);

      // Step 3: export
      this.steps[1].status = 'done';
      this.steps[2].status = 'running';
      this.stage = 'exporting';

      const result: any = await invoke('scan_project', {
        projectPath: this.srcDir,
        outputDir: this.outputDir,
      });

      this._tick(3, 60);
      this.steps[2].status = 'done';
      await this._delay(200);

      // Step 4: DW SQL
      this.steps[3].status = 'running';
      this._tick(4, 80);
      await this._delay(200);
      this.steps[3].status = 'done';

      // Step 5: index
      this.steps[4].status = 'running';
      this._tick(5, 100);
      await this._delay(150);
      this.steps[4].status = 'done';

      this.resultSrcCount = result?.source_count ?? 0;
      this.resultPblCount = result?.pbl_count ?? 0;
      this.resultOutputDir = this.outputDir;
      this.stage = 'done';

      this.history.unshift({
        time: new Date().toLocaleTimeString(),
        summary: `${this.resultSrcCount} 个源文件 → ${this.outputDir}`,
        ok: true,
      });
    } catch (e: any) {
      this.stage = 'error';
      this.errorMsg = String(e?.message ?? e);
      this.history.unshift({
        time: new Date().toLocaleTimeString(),
        summary: `失败: ${this.errorMsg}`,
        ok: false,
      });
    }
  }

  reset() {
    this.stage = 'idle';
    this.steps = [];
    this.progressPct = 0;
    this.errorMsg = '';
  }

  async doMigrateWeb() {
    if (!this.srcDir || !this.outputDir || this.migrating) return;
    this.migrating = true;
    this.quickMsg = '';
    this.quickMsgIsError = false;
    try {
      const result: any = await invoke('migrate_project', {
        projectPath: this.srcDir,
        outputDir: this.outputDir,
        template: 'angular',
      });
      const count = result?.source_count ?? '?';
      this.quickMsg = `✓ 已生成 Angular scaffold，${count} 个组件 → ${this.outputDir}`;
      this.history.unshift({
        time: new Date().toLocaleTimeString(),
        summary: `Web 迁移: ${count} 组件 → ${this.outputDir}`,
        ok: true,
      });
    } catch (e: any) {
      this.quickMsg = `✗ Web 迁移失败: ${String(e?.message ?? e)}`;
      this.quickMsgIsError = true;
      this.history.unshift({
        time: new Date().toLocaleTimeString(),
        summary: `Web 迁移失败: ${String(e?.message ?? e)}`,
        ok: false,
      });
    } finally {
      this.migrating = false;
      setTimeout(() => { this.quickMsg = ''; }, 6000);
    }
  }

  async doPackPbl() {
    if (!this.srcDir || !this.outputDir || this.packing) return;
    this.packing = true;
    this.quickMsg = '';
    this.quickMsgIsError = false;
    try {
      const result: any = await invoke('pack_to_pbl', {
        srcDir: this.srcDir,
        outputDir: this.outputDir,
      });
      const count = result?.packed_count ?? '?';
      const engine = result?.engine === 'python' ? '🐍 Python 引擎' : '📋 Manifest 模式';
      this.quickMsg = `✓ PBL 打包完成 (${engine}, ${count} 对象) → ${result?.pbl_path ?? this.outputDir}`;
      this.history.unshift({
        time: new Date().toLocaleTimeString(),
        summary: `PBL 重打包: ${count} 对象 (${engine})`,
        ok: true,
      });
    } catch (e: any) {
      this.quickMsg = `✗ 打包失败: ${String(e?.message ?? e)}`;
      this.quickMsgIsError = true;
      this.history.unshift({
        time: new Date().toLocaleTimeString(),
        summary: `PBL 打包失败: ${String(e?.message ?? e)}`,
        ok: false,
      });
    } finally {
      this.packing = false;
      setTimeout(() => { this.quickMsg = ''; }, 6000);
    }
  }

  private _tick(stepNum: number, pct: number) {
    this.progressPct = pct;
    // stepNum is 1-based; convert to 0-based index for array access
    const idx = stepNum - 1;
    if (idx >= 0 && idx < this.steps.length) {
      this.steps[idx].detail = `${pct}%`;
    }
  }

  private _delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
