
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { sharedStyles } from './styles';

@customElement('eog-button')
export class EogButton extends LitElement {
    static styles = [
        sharedStyles,
        css`
      :host {
        display: inline-block;
      }
      
      .btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: var(--space-2);
        padding: var(--space-3) var(--space-6);
        font-size: var(--font-size-sm);
        font-weight: 500;
        line-height: 1.5;
        border-radius: var(--radius-lg);
        border: 1px solid transparent;
        cursor: pointer;
        transition: all 150ms ease;
        text-decoration: none;
        font-family: var(--font-family);
      }

      .btn:focus {
        outline: none;
        box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.3);
      }

      /* Primary - Black */
      .btn-primary {
        background-color: var(--color-primary);
        color: var(--color-text-white);
        border-color: var(--color-primary);
      }

      .btn-primary:hover {
        background-color: var(--color-primary-hover);
      }

      /* Secondary - White */
      .btn-secondary {
        background-color: var(--color-bg-card);
        color: var(--color-text-primary);
        border-color: var(--color-border);
      }

      .btn-secondary:hover {
        background-color: var(--color-bg-hover);
      }

      /* Success - Green */
      .btn-success {
        background-color: var(--color-success);
        color: var(--color-text-white);
      }
      
      .btn-success:hover {
        background-color: #059669;
      }

      /* Full Width */
      .w-full {
        width: 100%;
        display: flex;
      }
    `
    ];

    @property({ type: String }) variant: 'primary' | 'secondary' | 'success' = 'primary';
    @property({ type: Boolean }) block = false;
    @property({ type: String }) href = '';

    render() {
        const classes = `btn btn-${this.variant} ${this.block ? 'w-full' : ''}`;

        if (this.href) {
            return html`<a href="${this.href}" class="${classes}"><slot></slot></a>`;
        }

        return html`
      <button class="${classes}">
        <slot></slot>
      </button>
    `;
    }
}

declare global {
    interface HTMLElementTagNameMap {
        'eog-button': EogButton;
    }
}
