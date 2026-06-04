import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { invoke } from '@tauri-apps/api/core';
import { open } from '@tauri-apps/plugin-dialog';

type Stage = 'idle' | 'analyzing' | 'generating' | 'done' | 'error';

interface MigrateResult {
  success: boolean;
  project_name: string;
  source_count: number;
  dw_count: number;
  window_count: number;
  menu_count: number;
  function_count: number;
  output_dir: string;
  errors: string[];
  // alias field
  components?: number;
}

interface MigrateStep {
  label: string;
  icon: string;
  status: 'pending' | 'running' | 'done' | 'error';
  detail: string;
}

@Component({
  selector: 'app-migrate-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="migrate-panel">
      <div class="panel-header">
        <div class="header-left">
          <span class="material-icons header-icon">transform</span>
          <div>
            <h3>迁移向导 / Migration Wizard</h3>
            <p class="header-sub">PowerBuilder → Angular Web 项目</p>
          </div>
        </div>
        @if (stage === 'idle' || stage === 'done' || stage === 'error') {
          <button class="btn-close" (click)="onClose.emit()" title="关闭">
            <span class="material-icons">close</span>
          </button>
        }
      </div>

      <!-- 步骤指示器 -->
      <div class="step-indicator">
        @for (s of steps; track s.label; let i = $index) {
          <div class="step-item" [class.active]="currentStep === i" [class.done]="currentStep > i">
            <div class="step-circle">
              @if (currentStep > i) {
                <span class="material-icons">check</span>
              } @else {
                <span>{{ i + 1 }}</span>
              }
            </div>
            <span class="step-label">{{ s.label }}</span>
          </div>
          @if (i < steps.length - 1) {
            <div class="step-line" [class.done]="currentStep > i"></div>
          }
        }
      </div>

      <!-- ── Step 0: 配置 ── -->
      @if (stage === 'idle') {
        <div class="config-section">
          <div class="config-block">
            <div class="config-title">
              <span class="material-icons">source</span>
              源码路径
            </div>
            <div class="config-row">
              <label>PB 项目目录 / PBL 文件</label>
              <div class="input-group">
                <input type="text" [(ngModel)]="srcPath" placeholder="选择 PowerBuilder 项目目录或 .pbl 文件..." class="path-input" />
                <button class="btn-browse" (click)="selectSrc()" title="浏览">
                  <span class="material-icons">folder_open</span>
                </button>
              </div>
              @if (srcPath) {
                <div class="path-hint">
                  <span class="material-icons" style="color:#a6e3a1;font-size:14px">check_circle</span>
                  {{ srcPath }}
                </div>
              }
            </div>
          </div>

          <div class="config-block">
            <div class="config-title">
              <span class="material-icons">output</span>
              输出配置
            </div>
            <div class="config-row">
              <label>Web 项目输出目录</label>
              <div class="input-group">
                <input type="text" [(ngModel)]="outputDir" placeholder="选择输出目录..." class="path-input" />
                <button class="btn-browse" (click)="selectOutput()" title="浏览">
                  <span class="material-icons">folder_open</span>
                </button>
              </div>
            </div>
            <div class="config-row">
              <label>目标框架</label>
              <select [(ngModel)]="template" class="select-input">
                <option value="angular">Angular 18 + Material + RxJS</option>
                <option value="react" disabled>React 18 (计划中)</option>
                <option value="vue" disabled>Vue 3 (计划中)</option>
              </select>
            </div>
          </div>

          <div class="action-row">
            <button class="btn-analyze" (click)="startMigrate()" [disabled]="!srcPath || !outputDir">
              <span class="material-icons">rocket_launch</span>
              开始迁移分析
            </button>
            <div class="action-hint">
              <span class="material-icons" style="font-size:14px;color:#6c7086">info</span>
              将自动识别 Window / DataWindow / Function 对象并生成对应 Angular 脚手架
            </div>
          </div>
        </div>
      }

      <!-- ── Step 1-2: 运行中 ── -->
      @if (stage === 'analyzing' || stage === 'generating') {
        <div class="running-section">
          <div class="running-steps">
            @for (step of runSteps; track step.label) {
              <div class="run-step" [class.running]="step.status === 'running'"
                   [class.done-step]="step.status === 'done'"
                   [class.error-step]="step.status === 'error'">
                <div class="run-step-icon">
                  @if (step.status === 'running') {
                    <span class="spinner-sm"></span>
                  } @else if (step.status === 'done') {
                    <span class="material-icons" style="color:#a6e3a1;font-size:18px">check_circle</span>
                  } @else if (step.status === 'error') {
                    <span class="material-icons" style="color:#f38ba8;font-size:18px">error</span>
                  } @else {
                    <span class="material-icons" style="color:#45475a;font-size:18px">radio_button_unchecked</span>
                  }
                </div>
                <div class="run-step-content">
                  <div class="run-step-label">{{ step.label }}</div>
                  @if (step.detail) {
                    <div class="run-step-detail">{{ step.detail }}</div>
                  }
                </div>
              </div>
            }
          </div>
          <div class="running-hint">
            <span class="spinner-sm"></span>
            {{ stage === 'analyzing' ? '正在分析 PB 源码结构...' : '正在生成 Angular 脚手架...' }}
          </div>
        </div>
      }

      <!-- ── Step 3: 完成 ── -->
      @if (stage === 'done' && result) {
        <div class="done-section">
          <div class="done-header">
            <span class="material-icons done-icon">check_circle</span>
            <div>
              <h4>迁移完成！</h4>
              <p>项目：{{ result.project_name }}</p>
            </div>
          </div>

          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-num">{{ result.source_count }}</div>
              <div class="stat-label">总 PB 对象</div>
            </div>
            <div class="stat-card stat-highlight">
              <div class="stat-num">{{ result.window_count }}</div>
              <div class="stat-label">Angular 组件</div>
              <div class="stat-sub">Window → Component</div>
            </div>
            <div class="stat-card stat-highlight">
              <div class="stat-num">{{ result.dw_count }}</div>
              <div class="stat-label">TS 模型 + 表单</div>
              <div class="stat-sub">DataWindow → Model</div>
            </div>
            <div class="stat-card">
              <div class="stat-num">{{ result.function_count }}</div>
              <div class="stat-label">服务桩</div>
              <div class="stat-sub">Function → Service</div>
            </div>
            <div class="stat-card">
              <div class="stat-num">{{ result.menu_count }}</div>
              <div class="stat-label">菜单</div>
              <div class="stat-sub">Menu</div>
            </div>
          </div>

          @if (result.errors.length > 0) {
            <div class="warn-block">
              <div class="warn-title">
                <span class="material-icons" style="color:#fab387;font-size:16px">warning</span>
                {{ result.errors.length }} 个警告
              </div>
              <ul class="err-list">
                @for (e of result.errors.slice(0, 5); track e) {
                  <li>{{ e }}</li>
                }
                @if (result.errors.length > 5) {
                  <li class="err-more">...还有 {{ result.errors.length - 5 }} 个</li>
                }
              </ul>
            </div>
          }

          <div class="output-path">
            <span class="material-icons" style="font-size:16px;color:#89b4fa">folder</span>
            输出目录：<code>{{ result.output_dir }}</code>
          </div>

          <div class="next-steps">
            <div class="next-title">
              <span class="material-icons" style="font-size:16px">arrow_forward</span>
              下一步
            </div>
            <ol class="next-list">
              <li>查看 <code>MIGRATION.md</code> — 含工作量估算和迁移清单</li>
              <li>运行 <code>npm install</code> 安装 Angular 18 依赖</li>
              <li>逐步实现 HTML 模板（控件布局需手动重构）</li>
              <li>替换 PB Transaction 为 Angular HttpClient</li>
              <li>验证 DataWindow 模型字段与数据库 Schema 一致</li>
            </ol>
          </div>

          <div class="done-actions">
            <button class="btn-reset" (click)="reset()">
              <span class="material-icons">refresh</span>
              再次迁移
            </button>
          </div>
        </div>
      }

      <!-- ── 错误 ── -->
      @if (stage === 'error') {
        <div class="error-section">
          <span class="material-icons" style="font-size:32px;color:#f38ba8">error</span>
          <h4>迁移失败</h4>
          <pre class="error-msg">{{ errorMsg }}</pre>
          <button class="btn-reset" (click)="reset()">
            <span class="material-icons">refresh</span>
            重试
          </button>
        </div>
      }
    </div>
  `,
  styles: [`
    .migrate-panel {
      height: 100%; display: flex; flex-direction: column;
      background: #1e1e2e; color: #cdd6f4; overflow: hidden;
    }

    /* ── Header ── */
    .panel-header {
      display: flex; align-items: center; justify-content: space-between;
      padding: 0.75rem 1rem; border-bottom: 1px solid #313244; flex-shrink: 0;
    }
    .header-left { display: flex; align-items: center; gap: 0.75rem; }
    .header-icon { font-size: 24px; color: #89dceb; }
    .panel-header h3 { margin: 0; font-size: 1rem; font-weight: 600; color: #cdd6f4; }
    .header-sub { margin: 0; font-size: 0.75rem; color: #6c7086; }
    .btn-close { background: transparent; border: none; cursor: pointer; color: #6c7086; border-radius: 6px; padding: 0.25rem; display: flex; align-items: center; }
    .btn-close:hover { background: #313244; color: #cdd6f4; }

    /* ── Step Indicator ── */
    .step-indicator {
      display: flex; align-items: center; padding: 1rem 1.5rem;
      border-bottom: 1px solid #313244; flex-shrink: 0; gap: 0;
    }
    .step-item { display: flex; flex-direction: column; align-items: center; gap: 0.3rem; min-width: 60px; }
    .step-circle {
      width: 28px; height: 28px; border-radius: 50%;
      background: #313244; border: 2px solid #45475a;
      display: flex; align-items: center; justify-content: center;
      font-size: 0.75rem; color: #6c7086; font-weight: 600;
      transition: all 0.2s;
    }
    .step-item.active .step-circle { border-color: #89dceb; color: #89dceb; background: rgba(137,220,235,0.1); }
    .step-item.done .step-circle { border-color: #a6e3a1; background: rgba(166,227,161,0.15); color: #a6e3a1; }
    .step-item.done .step-circle .material-icons { font-size: 16px; }
    .step-label { font-size: 0.68rem; color: #6c7086; white-space: nowrap; }
    .step-item.active .step-label { color: #89dceb; }
    .step-item.done .step-label { color: #a6e3a1; }
    .step-line { flex: 1; height: 2px; background: #313244; margin: 0 0.25rem; margin-bottom: 1rem; transition: background 0.2s; }
    .step-line.done { background: #a6e3a1; }

    /* ── Config Section ── */
    .config-section { flex: 1; overflow-y: auto; padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem; }
    .config-block { background: #181825; border: 1px solid #313244; border-radius: 10px; padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem; }
    .config-title { display: flex; align-items: center; gap: 0.4rem; font-size: 0.8rem; font-weight: 700; color: #89dceb; text-transform: uppercase; letter-spacing: 0.06em; }
    .config-title .material-icons { font-size: 16px; }
    .config-row { display: flex; flex-direction: column; gap: 0.35rem; }
    .config-row label { font-size: 0.78rem; color: #a6adc8; }
    .input-group { display: flex; gap: 0.4rem; }
    .path-input { flex: 1; background: #1e1e2e; border: 1px solid #313244; border-radius: 6px; padding: 0.4rem 0.6rem; color: #cdd6f4; font-size: 0.82rem; }
    .path-input::placeholder { color: #45475a; }
    .path-input:focus { outline: none; border-color: #89dceb; }
    .btn-browse { background: #313244; border: 1px solid #45475a; border-radius: 6px; padding: 0.4rem 0.6rem; cursor: pointer; color: #a6adc8; display: flex; align-items: center; }
    .btn-browse:hover { background: #45475a; color: #cdd6f4; }
    .btn-browse .material-icons { font-size: 18px; }
    .path-hint { display: flex; align-items: center; gap: 0.3rem; font-size: 0.72rem; color: #6c7086; padding: 0.1rem 0.2rem; }
    .select-input { background: #1e1e2e; border: 1px solid #313244; border-radius: 6px; padding: 0.4rem 0.6rem; color: #cdd6f4; font-size: 0.82rem; width: 100%; }
    .select-input:focus { outline: none; border-color: #89dceb; }

    .action-row { display: flex; flex-direction: column; gap: 0.5rem; padding-top: 0.25rem; }
    .btn-analyze {
      display: flex; align-items: center; justify-content: center; gap: 0.5rem;
      padding: 0.65rem 1.5rem; background: linear-gradient(135deg, #89dceb, #74c7ec);
      color: #11111b; border: none; border-radius: 8px; cursor: pointer;
      font-size: 0.9rem; font-weight: 700; transition: all 0.2s;
    }
    .btn-analyze:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(137,220,235,0.3); }
    .btn-analyze:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
    .btn-analyze .material-icons { font-size: 18px; }
    .action-hint { display: flex; align-items: flex-start; gap: 0.3rem; font-size: 0.72rem; color: #45475a; line-height: 1.4; }

    /* ── Running Section ── */
    .running-section { flex: 1; overflow-y: auto; padding: 1rem; display: flex; flex-direction: column; gap: 1rem; }
    .running-steps { display: flex; flex-direction: column; gap: 0.5rem; }
    .run-step {
      display: flex; align-items: flex-start; gap: 0.75rem;
      padding: 0.65rem 0.75rem; background: #181825; border: 1px solid #313244;
      border-radius: 8px; transition: all 0.2s;
    }
    .run-step.running { border-color: #89dceb; background: rgba(137,220,235,0.05); }
    .run-step.done-step { border-color: #313244; opacity: 0.7; }
    .run-step.error-step { border-color: #f38ba8; background: rgba(243,139,168,0.05); }
    .run-step-icon { flex-shrink: 0; display: flex; align-items: center; height: 22px; }
    .run-step-content { flex: 1; display: flex; flex-direction: column; gap: 0.15rem; }
    .run-step-label { font-size: 0.82rem; color: #cdd6f4; font-weight: 500; }
    .run-step.running .run-step-label { color: #89dceb; }
    .run-step.done-step .run-step-label { color: #a6adc8; }
    .run-step-detail { font-size: 0.72rem; color: #6c7086; }
    .running-hint { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8rem; color: #89dceb; padding: 0.5rem; }

    /* ── Done Section ── */
    .done-section { flex: 1; overflow-y: auto; padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem; }
    .done-header { display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem; background: rgba(166,227,161,0.08); border: 1px solid rgba(166,227,161,0.2); border-radius: 10px; }
    .done-icon { font-size: 32px; color: #a6e3a1; }
    .done-header h4 { margin: 0; font-size: 1rem; color: #a6e3a1; }
    .done-header p { margin: 0; font-size: 0.8rem; color: #6c7086; }

    .stats-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 0.5rem; }
    .stat-card {
      background: #181825; border: 1px solid #313244; border-radius: 8px;
      padding: 0.75rem 0.5rem; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 0.2rem;
    }
    .stat-card.stat-highlight { border-color: #89dceb; background: rgba(137,220,235,0.05); }
    .stat-num { font-size: 1.5rem; font-weight: 700; color: #cdd6f4; line-height: 1; }
    .stat-card.stat-highlight .stat-num { color: #89dceb; }
    .stat-label { font-size: 0.72rem; color: #a6adc8; font-weight: 600; }
    .stat-sub { font-size: 0.62rem; color: #6c7086; }

    .warn-block { background: rgba(250,179,135,0.07); border: 1px solid rgba(250,179,135,0.2); border-radius: 8px; padding: 0.75rem; }
    .warn-title { display: flex; align-items: center; gap: 0.4rem; font-size: 0.78rem; font-weight: 600; color: #fab387; margin-bottom: 0.4rem; }
    .err-list { margin: 0; padding-left: 1.2rem; }
    .err-list li { font-size: 0.72rem; color: #6c7086; margin-bottom: 0.2rem; word-break: break-all; }
    .err-more { color: #45475a; font-style: italic; }

    .output-path { display: flex; align-items: center; gap: 0.4rem; font-size: 0.78rem; color: #a6adc8; background: #181825; border-radius: 6px; padding: 0.5rem 0.75rem; border: 1px solid #313244; }
    .output-path code { color: #89b4fa; word-break: break-all; }

    .next-steps { background: #181825; border: 1px solid #313244; border-radius: 8px; padding: 0.75rem 1rem; }
    .next-title { display: flex; align-items: center; gap: 0.4rem; font-size: 0.78rem; font-weight: 700; color: #cba6f7; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.06em; }
    .next-list { margin: 0; padding-left: 1.4rem; }
    .next-list li { font-size: 0.78rem; color: #a6adc8; margin-bottom: 0.35rem; line-height: 1.5; }
    .next-list li code { color: #89dceb; background: rgba(137,220,235,0.1); padding: 0.1rem 0.3rem; border-radius: 4px; }

    .done-actions { display: flex; gap: 0.75rem; }
    .btn-reset {
      display: flex; align-items: center; gap: 0.4rem;
      padding: 0.5rem 1rem; background: #313244; border: 1px solid #45475a;
      border-radius: 6px; cursor: pointer; color: #a6adc8; font-size: 0.82rem;
    }
    .btn-reset:hover { background: #45475a; color: #cdd6f4; }

    /* ── Error Section ── */
    .error-section { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.75rem; padding: 2rem; text-align: center; }
    .error-section h4 { margin: 0; color: #f38ba8; }
    .error-msg { background: #181825; border: 1px solid #313244; border-radius: 8px; padding: 0.75rem 1rem; color: #f38ba8; font-size: 0.78rem; max-width: 100%; overflow: auto; text-align: left; white-space: pre-wrap; word-break: break-all; }

    /* ── Spinner ── */
    .spinner-sm {
      display: inline-block; width: 14px; height: 14px; flex-shrink: 0;
      border: 2px solid #313244; border-top-color: #89dceb;
      border-radius: 50%; animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  `]
})
export class MigratePanelComponent {
  @Input() projectPath = '';
  @Output() onClose = new EventEmitter<void>();

  stage: Stage = 'idle';
  currentStep = 0;

  srcPath = '';
  outputDir = '';
  template = 'angular';

  result: MigrateResult | null = null;
  errorMsg = '';

  readonly steps = [
    { label: '配置', icon: 'settings' },
    { label: '分析源码', icon: 'search' },
    { label: '生成脚手架', icon: 'build' },
    { label: '完成', icon: 'check_circle' },
  ];

  runSteps: { label: string; icon: string; status: 'pending' | 'running' | 'done' | 'error'; detail: string }[] = [];

  ngOnInit() {
    if (this.projectPath) {
      this.srcPath = this.projectPath;
    }
  }

  async selectSrc() {
    try {
      const selected = await open({ directory: true, multiple: false, title: '选择 PowerBuilder 项目目录' });
      if (selected) this.srcPath = selected as string;
    } catch (e) { console.error(e); }
  }

  async selectOutput() {
    try {
      const selected = await open({ directory: true, multiple: false, title: '选择 Web 项目输出目录' });
      if (selected) this.outputDir = selected as string;
    } catch (e) { console.error(e); }
  }

  async startMigrate() {
    if (!this.srcPath || !this.outputDir) return;
    this.stage = 'analyzing';
    this.currentStep = 1;
    this.errorMsg = '';

    this.runSteps = [
      { label: '检测项目结构', icon: 'search', status: 'running', detail: '' },
      { label: '扫描 PBL 文件', icon: 'inventory_2', status: 'pending', detail: '' },
      { label: '解析对象类型', icon: 'category', status: 'pending', detail: '' },
      { label: '生成 Angular 脚手架', icon: 'code', status: 'pending', detail: '' },
      { label: '写入项目文件', icon: 'save', status: 'pending', detail: '' },
    ];

    try {
      // 第一步：分析源码
      await this._delay(400);
      this.runSteps[0].status = 'done';
      this.runSteps[0].detail = `${this.srcPath}`;
      this.runSteps[1].status = 'running';

      await this._delay(300);
      this.runSteps[1].status = 'done';
      this.runSteps[2].status = 'running';

      await this._delay(300);
      this.runSteps[2].status = 'done';
      this.runSteps[3].status = 'running';
      this.stage = 'generating';
      this.currentStep = 2;

      // 调用 Tauri 后端
      const res: MigrateResult = await invoke('migrate_project', {
        projectPath: this.srcPath,
        outputDir: this.outputDir,
        template: this.template,
      });

      this.runSteps[3].status = 'done';
      this.runSteps[3].detail = `${res.window_count} 个 Angular 组件`;
      this.runSteps[4].status = 'running';
      await this._delay(200);
      this.runSteps[4].status = 'done';
      this.runSteps[4].detail = `输出到 ${res.output_dir}`;

      this.result = res;
      this.stage = 'done';
      this.currentStep = 3;
    } catch (e: any) {
      const msg = String(e?.message ?? e);
      this.errorMsg = msg;
      const running = this.runSteps.findIndex(s => s.status === 'running');
      if (running >= 0) this.runSteps[running].status = 'error';
      this.stage = 'error';
    }
  }

  reset() {
    this.stage = 'idle';
    this.currentStep = 0;
    this.result = null;
    this.errorMsg = '';
    this.runSteps = [];
  }

  private _delay(ms: number): Promise<void> {
    return new Promise(r => setTimeout(r, ms));
  }
}
