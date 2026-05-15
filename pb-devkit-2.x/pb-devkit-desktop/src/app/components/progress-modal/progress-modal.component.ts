import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

export interface ProgressInfo {
  current: number;
  total: number;
  message: string;
  currentFile?: string;
}

@Component({
  selector: 'app-progress-modal',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="modal-overlay" *ngIf="visible">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ title }}</h3>
          <button class="btn-close" (click)="onCancel()" *ngIf="showCancel">
            <span class="material-icons">close</span>
          </button>
        </div>
        
        <div class="modal-body">
          <div class="progress-info">
            <span class="progress-text">{{ progress.current }} / {{ progress.total }}</span>
            <span class="progress-percentage">{{ percentage }}%</span>
          </div>
          
          <div class="progress-bar-container">
            <div class="progress-bar" [style.width.%]="percentage"></div>
          </div>
          
          <div class="progress-message">{{ progress.message }}</div>
          
          <div class="current-file" *ngIf="progress.currentFile">
            <span class="material-icons" style="font-size:14px">insert_drive_file</span>
            {{ progress.currentFile }}
          </div>
          
          <div class="estimated-time" *ngIf="estimatedTime">
            预计剩余时间: {{ estimatedTime }}
          </div>
        </div>
        
        <div class="modal-footer">
          @if (showCancel) {
            <button class="btn-cancel" (click)="onCancel()">取消</button>
          }
          @if (completed) {
            <button class="btn-done" (click)="onDone()">完成</button>
          }
        </div>
      </div>
    </div>
  `,
  styles: [`
    .modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }
    
    .modal-content {
      background: var(--bg-primary, #1e1e1e);
      border-radius: 12px;
      width: 400px;
      max-width: 90vw;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
      border: 1px solid var(--border-color, #333);
    }
    
    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 20px;
      border-bottom: 1px solid var(--border-color, #333);
    }
    
    .modal-header h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary, #fff);
    }
    
    .btn-close {
      background: none;
      border: none;
      cursor: pointer;
      color: var(--text-secondary, #888);
      padding: 4px;
      border-radius: 4px;
    }
    
    .btn-close:hover {
      background: var(--bg-hover, #333);
    }
    
    .modal-body {
      padding: 20px;
    }
    
    .progress-info {
      display: flex;
      justify-content: space-between;
      margin-bottom: 8px;
    }
    
    .progress-text {
      font-size: 14px;
      color: var(--text-primary, #fff);
    }
    
    .progress-percentage {
      font-size: 14px;
      font-weight: 600;
      color: var(--accent-color, #4fc3f7);
    }
    
    .progress-bar-container {
      height: 8px;
      background: var(--bg-secondary, #333);
      border-radius: 4px;
      overflow: hidden;
      margin-bottom: 16px;
    }
    
    .progress-bar {
      height: 100%;
      background: linear-gradient(90deg, var(--accent-color, #4fc3f7), #66bb6a);
      border-radius: 4px;
      transition: width 0.3s ease;
    }
    
    .progress-message {
      font-size: 13px;
      color: var(--text-secondary, #aaa);
      margin-bottom: 8px;
    }
    
    .current-file {
      font-size: 12px;
      color: var(--text-secondary, #888);
      background: var(--bg-secondary, #2a2a2a);
      padding: 8px 12px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      gap: 8px;
      word-break: break-all;
    }
    
    .estimated-time {
      font-size: 12px;
      color: var(--text-secondary, #888);
      margin-top: 12px;
      text-align: center;
    }
    
    .modal-footer {
      padding: 16px 20px;
      border-top: 1px solid var(--border-color, #333);
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }
    
    .btn-cancel, .btn-done {
      padding: 8px 20px;
      border-radius: 6px;
      font-size: 14px;
      cursor: pointer;
      border: none;
      transition: all 0.2s;
    }
    
    .btn-cancel {
      background: var(--bg-secondary, #333);
      color: var(--text-primary, #fff);
    }
    
    .btn-cancel:hover {
      background: var(--bg-hover, #444);
    }
    
    .btn-done {
      background: var(--accent-color, #4fc3f7);
      color: #000;
    }
    
    .btn-done:hover {
      background: var(--accent-hover, #29b6f6);
    }
  `]
})
export class ProgressModalComponent {
  @Input() visible = false;
  @Input() title = '处理中...';
  @Input() progress: ProgressInfo = { current: 0, total: 0, message: '' };
  @Input() showCancel = true;
  @Input() completed = false;
  @Input() estimatedTime = '';
  
  @Output() cancel = new EventEmitter<void>();
  @Output() done = new EventEmitter<void>();
  
  get percentage(): number {
    if (this.progress.total === 0) return 0;
    return Math.round((this.progress.current / this.progress.total) * 100);
  }
  
  onCancel() {
    this.cancel.emit();
  }
  
  onDone() {
    this.done.emit();
  }
}