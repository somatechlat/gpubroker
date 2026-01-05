
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { sharedStyles } from './styles';

@customElement('eog-kpi-card')
export class EogKpiCard extends LitElement {
    static styles = [
        sharedStyles,
        css`
      :host {
        display: block;
      }
      
      .card {
        background-color: var(--color-bg-card);
        border-radius: var(--radius-lg);
        border: 1px solid var(--color-border);
        box-shadow: var(--shadow-card);
        padding: var(--space-6);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
      }

      .label {
        font-size: var(--font-size-sm);
        color: var(--color-text-secondary);
        margin-bottom: var(--space-2);
        font-weight: 500;
      }

      .value {
        font-size: var(--font-size-3xl);
        font-weight: 600;
        color: var(--color-text-primary);
        line-height: 1.2;
      }
      
      .loading {
        opacity: 0.5;
      }
    `
    ];

    @property({ type: String }) label = '';
    @property({ type: String }) value = '';
    @property({ type: Boolean }) loading = false;

    render() {
        return html`
      <div class="card">
        <div class="label">${this.label}</div>
        <div class="value ${this.loading ? 'loading' : ''}">
          ${this.loading ? '...' : this.value}
        </div>
      </div>
    `;
    }
}

declare global {
    interface HTMLElementTagNameMap {
        'eog-kpi-card': EogKpiCard;
    }
}
