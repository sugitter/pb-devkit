import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { invoke } from '@tauri-apps/api/core';
import { open } from '@tauri-apps/plugin-dialog';

interface ReviewSection {
  name: string;
  score: number;
  max_score: number;
  findings: string[];
}

interface ReviewResult {
  project_dir: string;
  total_score: number;
  sections: ReviewSection[];
  report_path: string;
  elapsed_ms: number;
  error?: string;
}

@Component({
  selector: 'app-review-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="review-panel">
      <!-- 头部 -->
      <div class="panel-header">
        <span class="material-icons header-icon">fact_check</span>
        <div class="header-text">
          <h2>项目评审</h2>
          <p>综合评估 PB 项目质量，生成评审报告（100 分制）</p>
        </div>
      </div>

      <!-- 配置区 -->
      <div class="config-section">
        <div class="config-row">
          <label>项目目录</label>
          <div class="dir-input-group">
            <input class="dir-input" [value]="projectDir" readonly placeholder="选择 PB 项目目录..." />
            <button class="dir-btn" (click)="pickProjectDir()">
              <span class="material-icons">folder_open</span>
            </button>
          </div>
        </div>
        <div class="config-row">
          <label>报告输出目录</label>
          <div class="dir-input-group">
            <input class="dir-input" [value]="outputDir" readonly placeholder="默认：与项目目录相同..." />
            <button class="dir-btn" (click)="pickOutputDir()">
              <span class="material-icons">folder_open</span>
            </button>
          </div>
        </div>
        <div class="config-actions">
          <button class="run-btn" (click)="runReview()" [disabled]="!projectDir || running">
            @if (running) {
              <div class="btn-spinner"></div> 评审中...
            } @else {
              <span class="material-icons">play_arrow</span> 开始评审
            }
          </button>
        </div>
      </div>

      <!-- 错误提示 -->
      @if (errorMsg) {
        <div class="error-bar">
          <span class="material-icons">error</span> {{ errorMsg }}
        </div>
      }

      <!-- 评审结果 -->
      @if (result) {
        <!-- 总评分卡 -->
        <div class="score-hero">
          <div class="score-ring" [class]="scoreClass(result.total_score)">
            <span class="score-num">{{ result.total_score }}</span>
            <span class="score-unit">/ 100</span>
          </div>
          <div class="score-meta">
            <div class="score-label">综合评分</div>
            <div class="score-grade" [class]="scoreClass(result.total_score)">{{ scoreGrade(result.total_score) }}</div>
            <div class="score-time">耗时 {{ result.elapsed_ms }} ms</div>
          </div>
          @if (result.report_path) {
            <div class="report-path">
              <span class="material-icons">description</span>
              <span>{{ result.report_path }}</span>
            </div>
          }
        </div>

        <!-- 维度雷达 / 条形图 -->
        <div class="sections-grid">
          @for (section of result.sections; track section.name) {
            <div class="section-card" [class]="sectionClass(section.score, section.max_score)">
              <div class="section-header">
                <span class="material-icons section-icon">{{ sectionIcon(section.name) }}</span>
                <span class="section-name">{{ section.name }}</span>
                <span class="section-score">{{ section.score }} / {{ section.max_score }}</span>
              </div>
              <!-- 进度条 -->
              <div class="section-bar-bg">
                <div class="section-bar-fill" [style.width.%]="(section.score / section.max_score) * 100" [class]="sectionClass(section.score, section.max_score)"></div>
              </div>
              <!-- 发现 -->
              @if (section.findings.length > 0) {
                <ul class="section-findings">
                  @for (f of section.findings; track $index) {
                    <li>{{ f }}</li>
                  }
                </ul>
              } @else {
                <p class="section-ok"><span class="material-icons">check_circle</span> 无问题</p>
              }
            </div>
          }
        </div>
      }

      <!-- 空状态 -->
      @if (!result && !running && !errorMsg) {
        <div class="empty-state">
          <span class="material-icons empty-icon">fact_check</span>
          <p>选择项目目录后点击「开始评审」</p>
          <p class="empty-hint">评审维度：项目结构 · 规模统计 · 代码质量 · DataWindow · 迁移评估</p>
        </div>
      }
    </div>
  `,
  styles: [`
    .review-panel {
      display: flex;
      flex-direction: column;
      height: 100%;
      overflow-y: auto;
      background: #f9fafb;
      font-family: system-ui, sans-serif;
    }

    /* ── 头部 ── */
    .panel-header {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 1rem 1.25rem;
      background: #fff;
      border-bottom: 1px solid #e5e7eb;
      flex-shrink: 0;
    }
    .header-icon { font-size: 28px; color: #7c3aed; }
    .header-text h2 { margin: 0; font-size: 1rem; color: #111827; }
    .header-text p { margin: 0.15rem 0 0; font-size: 0.78rem; color: #6b7280; }

    /* ── 配置 ── */
    .config-section {
      background: #fff;
      border-bottom: 1px solid #e5e7eb;
      padding: 0.75rem 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      flex-shrink: 0;
    }
    .config-row {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .config-row label {
      font-size: 0.8rem;
      color: #374151;
      font-weight: 500;
      width: 100px;
      flex-shrink: 0;
    }
    .dir-input-group { display: flex; flex: 1; gap: 0.4rem; min-width: 0; }
    .dir-input {
      flex: 1;
      padding: 0.35rem 0.6rem;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      font-size: 0.8rem;
      background: #f9fafb;
      color: #374151;
      min-width: 0;
    }
    .dir-btn {
      padding: 0.3rem 0.5rem;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      background: #f3f4f6;
      cursor: pointer;
      color: #6b7280;
      display: flex;
      align-items: center;
    }
    .dir-btn:hover { background: #e5e7eb; color: #111827; }
    .dir-btn .material-icons { font-size: 18px; }
    .config-actions { display: flex; gap: 0.75rem; margin-top: 0.25rem; }
    .run-btn {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.45rem 1.2rem;
      background: #7c3aed;
      color: #fff;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.82rem;
      font-weight: 500;
    }
    .run-btn:hover:not(:disabled) { background: #6d28d9; }
    .run-btn:disabled { opacity: 0.6; cursor: not-allowed; }
    .run-btn .material-icons { font-size: 18px; }
    .btn-spinner { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0; }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* ── 错误 ── */
    .error-bar {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.6rem 1.25rem;
      background: #fef2f2;
      color: #b91c1c;
      font-size: 0.82rem;
      border-bottom: 1px solid #fecaca;
      flex-shrink: 0;
    }
    .error-bar .material-icons { font-size: 18px; }

    /* ── 评分 hero ── */
    .score-hero {
      display: flex;
      align-items: center;
      gap: 1.5rem;
      padding: 1.25rem 1.5rem;
      background: #fff;
      border-bottom: 1px solid #e5e7eb;
      flex-shrink: 0;
      flex-wrap: wrap;
    }
    .score-ring {
      width: 80px;
      height: 80px;
      border-radius: 50%;
      border: 5px solid;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .score-ring.grade-a { border-color: #059669; }
    .score-ring.grade-b { border-color: #2563eb; }
    .score-ring.grade-c { border-color: #d97706; }
    .score-ring.grade-d { border-color: #dc2626; }
    .score-num { font-size: 1.5rem; font-weight: 700; line-height: 1; }
    .score-ring.grade-a .score-num { color: #059669; }
    .score-ring.grade-b .score-num { color: #2563eb; }
    .score-ring.grade-c .score-num { color: #d97706; }
    .score-ring.grade-d .score-num { color: #dc2626; }
    .score-unit { font-size: 0.65rem; color: #9ca3af; }
    .score-meta { display: flex; flex-direction: column; gap: 0.2rem; }
    .score-label { font-size: 0.78rem; color: #6b7280; }
    .score-grade { font-size: 1.1rem; font-weight: 700; }
    .score-grade.grade-a { color: #059669; }
    .score-grade.grade-b { color: #2563eb; }
    .score-grade.grade-c { color: #d97706; }
    .score-grade.grade-d { color: #dc2626; }
    .score-time { font-size: 0.72rem; color: #9ca3af; }
    .report-path {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.4rem 0.8rem;
      background: #f3f4f6;
      border-radius: 6px;
      font-size: 0.75rem;
      color: #6b7280;
      max-width: 400px;
      overflow: hidden;
    }
    .report-path .material-icons { font-size: 15px; color: #7c3aed; flex-shrink: 0; }
    .report-path span:last-child { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    /* ── 维度卡片 ── */
    .sections-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 1rem;
      padding: 1rem 1.25rem;
    }
    .section-card {
      background: #fff;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      padding: 0.85rem 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }
    .section-card.grade-a { border-left: 3px solid #059669; }
    .section-card.grade-b { border-left: 3px solid #2563eb; }
    .section-card.grade-c { border-left: 3px solid #d97706; }
    .section-card.grade-d { border-left: 3px solid #dc2626; }
    .section-header {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .section-icon { font-size: 18px; color: #6b7280; }
    .section-name { flex: 1; font-size: 0.85rem; font-weight: 600; color: #111827; }
    .section-score { font-size: 0.8rem; font-weight: 600; color: #374151; }
    .section-bar-bg { height: 6px; background: #f3f4f6; border-radius: 3px; overflow: hidden; }
    .section-bar-fill { height: 100%; border-radius: 3px; transition: width 0.4s ease; }
    .section-bar-fill.grade-a { background: #059669; }
    .section-bar-fill.grade-b { background: #2563eb; }
    .section-bar-fill.grade-c { background: #d97706; }
    .section-bar-fill.grade-d { background: #dc2626; }
    .section-findings {
      margin: 0;
      padding-left: 1rem;
      font-size: 0.76rem;
      color: #4b5563;
      display: flex;
      flex-direction: column;
      gap: 0.2rem;
    }
    .section-ok {
      margin: 0;
      font-size: 0.76rem;
      color: #059669;
      display: flex;
      align-items: center;
      gap: 0.3rem;
    }
    .section-ok .material-icons { font-size: 14px; }

    /* ── 空状态 ── */
    .empty-state {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 3rem;
      text-align: center;
      color: #9ca3af;
    }
    .empty-icon { font-size: 52px; color: #d1d5db; margin-bottom: 0.75rem; }
    .empty-state p { margin: 0.2rem 0; font-size: 0.85rem; }
    .empty-hint { font-size: 0.75rem !important; color: #d1d5db; }
  `]
})
export class ReviewPanelComponent {
  projectDir = '';
  outputDir = '';
  running = false;
  errorMsg = '';
  result: ReviewResult | null = null;

  async pickProjectDir() {
    const dir = await open({ directory: true, multiple: false, title: '选择 PB 项目目录' });
    if (dir) this.projectDir = dir as string;
  }

  async pickOutputDir() {
    const dir = await open({ directory: true, multiple: false, title: '选择报告输出目录' });
    if (dir) this.outputDir = dir as string;
  }

  async runReview() {
    if (!this.projectDir) return;
    this.running = true;
    this.errorMsg = '';
    this.result = null;

    try {
      const res = await invoke<ReviewResult>('run_review', {
        projectDir: this.projectDir,
        outputDir: this.outputDir || this.projectDir,
      });
      if (res.error) {
        this.errorMsg = res.error;
      } else {
        this.result = res;
      }
    } catch (e: any) {
      this.errorMsg = e?.toString() ?? '评审失败，请检查项目目录';
    } finally {
      this.running = false;
    }
  }

  scoreClass(score: number): string {
    if (score >= 85) return 'grade-a';
    if (score >= 70) return 'grade-b';
    if (score >= 50) return 'grade-c';
    return 'grade-d';
  }

  scoreGrade(score: number): string {
    if (score >= 85) return '优秀 A';
    if (score >= 70) return '良好 B';
    if (score >= 50) return '一般 C';
    return '较差 D';
  }

  sectionClass(score: number, max: number): string {
    const pct = max > 0 ? score / max : 1;
    if (pct >= 0.85) return 'grade-a';
    if (pct >= 0.70) return 'grade-b';
    if (pct >= 0.50) return 'grade-c';
    return 'grade-d';
  }

  sectionIcon(name: string): string {
    if (name.includes('结构') || name.includes('struct')) return 'account_tree';
    if (name.includes('统计') || name.includes('stat')) return 'bar_chart';
    if (name.includes('质量') || name.includes('quality')) return 'verified';
    if (name.includes('DataWindow') || name.includes('dw')) return 'table_chart';
    if (name.includes('迁移') || name.includes('migrat')) return 'rocket_launch';
    return 'check_circle';
  }
}
