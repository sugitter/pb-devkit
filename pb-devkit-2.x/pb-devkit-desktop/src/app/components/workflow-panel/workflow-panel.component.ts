import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { open } from '@tauri-apps/plugin-dialog';
import { PblService } from '../../services/pbl.service';

type WorkflowStep = 'idle' | 'export' | 'analyze' | 'report' | 'done' | 'error';

interface WorkflowStepInfo {
  id: WorkflowStep;
  label: string;
  icon: string;
}

@Component({
  selector: 'app-workflow-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="workflow-panel">
      <div class="wf-header">
        <h2><span class="material-icons" style="vertical-align:middle;margin-right:6px">account_tree</span> 工作流</h2>
        <p class="wf-subtitle">导出 → 分析 → 报告，一键执行</p>
      </div>

      <!-- 源选择 -->
      <div class="wf-section">
        <h4><span class="material-icons" style="font-size:16px;vertical-align:middle">input</span> 数据源</h4>
        <div class="wf-input-row">
          <input type="text" [(ngModel)]="sourcePath" readonly placeholder="选择 PBL 文件或项目目录" class="wf-input" />
          <button class="wf-browse" (click)="browseSource()">
            <span class="material-icons" style="font-size:16px">folder_open</span>
          </button>
        </div>
        <div class="wf-input-row">
          <input type="text" [(ngModel)]="outputDir" readonly placeholder="选择输出目录" class="wf-input" />
          <button class="wf-browse" (click)="browseOutput()">
            <span class="material-icons" style="font-size:16px">folder_open</span>
          </button>
        </div>
        <label class="wf-checkbox">
          <input type="checkbox" [(ngModel)]="applyFix" />
          <span>自动修复已知问题</span>
        </label>
      </div>

      <!-- 步骤进度 -->
      <div class="wf-section">
        <h4><span class="material-icons" style="font-size:16px;vertical-align:middle">timeline</span> 执行步骤</h4>
        <div class="wf-steps">
          @for (step of steps; track step.id) {
            <div class="wf-step" [class.active]="currentStep === step.id" [class.done]="isStepDone(step.id)" [class.pending]="!isStepDone(step.id) && currentStep !== step.id">
              <div class="step-indicator">
                @if (isStepDone(step.id)) {
                  <span class="material-icons" style="font-size:18px;color:#059669">check_circle</span>
                } @else if (currentStep === step.id) {
                  <div class="spinner-sm"></div>
                } @else {
                  <span class="step-dot"></span>
                }
              </div>
              <div class="step-info">
                <span class="step-icon"><span class="material-icons" style="font-size:16px">{{ step.icon }}</span></span>
                <span class="step-label">{{ step.label }}</span>
              </div>
            </div>
          }
        </div>
      </div>

      <!-- 执行按钮 -->
      <div class="wf-actions">
        <button class="wf-run" (click)="runWorkflow()" [disabled]="!sourcePath || !outputDir || running">
          <span class="material-icons" style="font-size:16px">play_arrow</span>
          {{ running ? '执行中...' : '执行工作流' }}
        </button>
        <button class="wf-reset" (click)="resetWorkflow()" [disabled]="running">
          <span class="material-icons" style="font-size:16px">refresh</span> 重置
        </button>
      </div>

      <!-- 结果 -->
      @if (workflowResult) {
        <div class="wf-section wf-result">
          <h4><span class="material-icons" style="font-size:16px;vertical-align:middle">assessment</span> 执行结果</h4>
          <div class="wf-result-grid">
            <div class="result-item">
              <span class="result-value">{{ workflowResult.exported_count }}</span>
              <span class="result-label">导出文件</span>
            </div>
            <div class="result-item">
              <span class="result-value">{{ workflowResult.analyzed_count }}</span>
              <span class="result-label">分析文件</span>
            </div>
            <div class="result-item">
              <span class="result-value">{{ workflowResult.issues_found }}</span>
              <span class="result-label">发现问题</span>
            </div>
          </div>
          @if (workflowResult.report_path) {
            <div class="result-path">
              <span class="material-icons" style="font-size:14px;color:#059669">description</span>
              <span>报告: {{ workflowResult.report_path }}</span>
            </div>
          }
          @if (workflowResult.message) {
            <div class="result-message">{{ workflowResult.message }}</div>
          }
        </div>
      }

      @if (error) {
        <div class="wf-error">
          <span class="material-icons" style="font-size:16px">error</span> {{ error }}
        </div>
      }
    </div>
  `,
  styles: [`
    .workflow-panel { display: flex; flex-direction: column; height: 100%; background: #fff; overflow-y: auto; }

    .wf-header { padding: 0.75rem 1rem; border-bottom: 1px solid #e5e7eb; flex-shrink: 0; }
    .wf-header h2 { margin: 0; font-size: 0.9rem; display: flex; align-items: center; }
    .wf-subtitle { margin: 0.2rem 0 0; font-size: 0.75rem; color: #6b7280; }

    .wf-section { padding: 0.75rem 1rem; border-bottom: 1px solid #e5e7eb; }
    .wf-section h4 { margin: 0 0 0.5rem; font-size: 0.82rem; color: #374151; display: flex; align-items: center; gap: 0.3rem; }

    .wf-input-row { display: flex; gap: 0.4rem; margin-bottom: 0.4rem; }
    .wf-input { flex: 1; padding: 0.4rem 0.6rem; border: 1px solid #d1d5db; border-radius: 4px; background: #fff; font-size: 0.8rem; color: #374151; }
    .wf-browse { padding: 0.4rem 0.6rem; background: #fff; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; color: #6b7280; display: flex; align-items: center; }
    .wf-browse:hover { background: #f3f4f6; }

    .wf-checkbox { display: flex; align-items: center; gap: 0.4rem; font-size: 0.8rem; color: #374151; cursor: pointer; margin-top: 0.3rem; }
    .wf-checkbox input { accent-color: #7c3aed; }

    /* 步骤进度 */
    .wf-steps { display: flex; flex-direction: column; gap: 0.5rem; }
    .wf-step { display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0.6rem; border-radius: 6px; border: 1px solid transparent; transition: all 0.15s; }
    .wf-step.active { background: #eff6ff; border-color: #93c5fd; }
    .wf-step.done { background: #f0fdf4; }
    .wf-step.pending { opacity: 0.6; }

    .step-indicator { width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
    .step-dot { width: 10px; height: 10px; border-radius: 50%; background: #d1d5db; }
    .spinner-sm { width: 16px; height: 16px; border: 2px solid #e5e7eb; border-top-color: #2563eb; border-radius: 50%; animation: spin 0.8s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }

    .step-info { display: flex; align-items: center; gap: 0.3rem; }
    .step-icon { color: #6b7280; }
    .step-label { font-size: 0.82rem; color: #374151; }
    .wf-step.active .step-label { color: #2563eb; font-weight: 500; }
    .wf-step.done .step-label { color: #059669; }

    /* 按钮 */
    .wf-actions { display: flex; gap: 0.5rem; padding: 0.75rem 1rem; border-bottom: 1px solid #e5e7eb; flex-shrink: 0; }
    .wf-run { flex: 1; padding: 0.55rem 1rem; background: #7c3aed; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 0.82rem; display: flex; align-items: center; justify-content: center; gap: 0.3rem; }
    .wf-run:hover { background: #6d28d9; }
    .wf-run:disabled { background: #d1d5db; cursor: not-allowed; }
    .wf-reset { padding: 0.55rem 1rem; background: #f3f4f6; color: #374151; border: 1px solid #d1d5db; border-radius: 6px; cursor: pointer; font-size: 0.82rem; display: flex; align-items: center; justify-content: center; gap: 0.3rem; }
    .wf-reset:hover { background: #e5e7eb; }

    /* 结果 */
    .wf-result-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; margin-bottom: 0.5rem; }
    .result-item { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; padding: 0.6rem; text-align: center; }
    .result-value { display: block; font-size: 1.3rem; font-weight: 700; color: #7c3aed; }
    .result-label { display: block; font-size: 0.72rem; color: #6b7280; margin-top: 0.15rem; }
    .result-path { display: flex; align-items: center; gap: 0.3rem; font-size: 0.78rem; color: #374151; padding: 0.3rem 0; word-break: break-all; }
    .result-message { padding: 0.4rem 0.6rem; background: #f0fdf4; color: #166534; border-radius: 4px; font-size: 0.8rem; margin-top: 0.3rem; }

    .wf-error { padding: 0.6rem 1rem; margin: 0.5rem; background: #fee2e2; color: #dc2626; border-radius: 6px; font-size: 0.82rem; display: flex; align-items: center; gap: 0.3rem; }
  `]
})
export class WorkflowPanelComponent {
  @Input() projectPath = '';
  @Output() workflowComplete = new EventEmitter<any>();

  sourcePath = '';
  outputDir = '';
  applyFix = false;
  running = false;
  error = '';
  currentStep: WorkflowStep = 'idle';
  workflowResult: any = null;

  steps: WorkflowStepInfo[] = [
    { id: 'export', label: '导出源码', icon: 'download' },
    { id: 'analyze', label: '代码分析', icon: 'analytics' },
    { id: 'report', label: '生成报告', icon: 'assessment' },
  ];

  constructor(private pblService: PblService) {}

  async browseSource() {
    try {
      const selected = await open({
        multiple: false,
        filters: [{ name: 'PB Files', extensions: ['pbl', 'pbd', 'exe', 'dll'] }],
        directory: true,
        title: '选择数据源'
      });
      if (selected) this.sourcePath = selected as string;
    } catch (e) {
      this.error = String(e);
    }
  }

  async browseOutput() {
    try {
      const selected = await open({
        directory: true,
        multiple: false,
        title: '选择输出目录'
      });
      if (selected) this.outputDir = selected as string;
    } catch (e) {
      this.error = String(e);
    }
  }

  isStepDone(stepId: WorkflowStep): boolean {
    const order: WorkflowStep[] = ['export', 'analyze', 'report'];
    const currentIdx = order.indexOf(this.currentStep);
    const stepIdx = order.indexOf(stepId);
    if (this.currentStep === 'done') return true;
    if (this.currentStep === 'error') return stepIdx < order.indexOf('report');
    return stepIdx < currentIdx;
  }

  async runWorkflow() {
    if (!this.sourcePath || !this.outputDir) return;

    this.running = true;
    this.error = '';
    this.workflowResult = null;

    try {
      this.currentStep = 'export';
      const result = await this.pblService.runWorkflow(this.sourcePath, this.outputDir, this.applyFix);

      this.currentStep = 'analyze';
      // 短暂延迟模拟步骤推进
      await new Promise(r => setTimeout(r, 300));

      this.currentStep = 'report';
      await new Promise(r => setTimeout(r, 300));

      this.workflowResult = result;
      this.currentStep = 'done';
      this.workflowComplete.emit(result);
    } catch (e: any) {
      this.currentStep = 'error';
      this.error = e?.message || String(e);
    } finally {
      this.running = false;
    }
  }

  resetWorkflow() {
    this.currentStep = 'idle';
    this.workflowResult = null;
    this.error = '';
    this.sourcePath = '';
    this.outputDir = '';
    this.applyFix = false;
  }
}
