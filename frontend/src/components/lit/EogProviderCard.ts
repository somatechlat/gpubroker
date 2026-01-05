
import { LitElement, html, css, PropertyValueMap } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { sharedStyles } from './styles';

@customElement('eog-provider-card')
export class EogProviderCard extends LitElement {
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
        transition: background-color 300ms ease;
      }

      .price-flash {
        background-color: #d1fae5; /* green-100 */
      }

      .flex-between {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
      }

      .provider-name {
        font-size: var(--font-size-sm);
        font-weight: 500;
        color: var(--color-text-secondary);
      }

      .gpu-model {
        font-size: var(--font-size-lg);
        font-weight: 700;
        color: var(--color-text-primary);
        margin-top: var(--space-2);
      }

      .price {
        margin-top: var(--space-2);
        font-size: var(--font-size-sm);
        color: var(--color-text-secondary);
      }

      .btn-primary {
        background-color: var(--color-primary);
        color: var(--color-text-white);
        border: none;
        padding: var(--space-2) var(--space-4);
        border-radius: var(--radius-md);
        font-weight: 500;
        cursor: pointer;
        font-size: var(--font-size-sm);
      }

      .btn-primary:hover {
        background-color: var(--color-primary-hover);
      }
    `
    ];

    @property({ type: String }) name = '';
    @property({ type: String }) gpu = '';
    @property({ type: String }) price = '';
    @property({ type: Boolean }) flash = false;

    private _handleBook() {
        this.dispatchEvent(new CustomEvent('book', {
            bubbles: true,
            composed: true,
            detail: { gpu: this.gpu, price: this.price }
        }));
    }

    render() {
        return html`
      <div class="card ${this.flash ? 'price-flash' : ''}">
        <div class="flex-between">
          <div>
            <div class="provider-name">${this.name}</div>
            <div class="gpu-model">${this.gpu || '—'}</div>
            <div class="price">${this.price || 'Price N/A'}</div>
          </div>
          <div>
            <button class="btn-primary" @click="${this._handleBook}">Book</button>
          </div>
        </div>
      </div>
    `;
    }
}

declare global {
    interface HTMLElementTagNameMap {
        'eog-provider-card': EogProviderCard;
    }
}
