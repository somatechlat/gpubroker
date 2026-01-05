
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { sharedStyles } from './styles';

@customElement('eog-header')
export class EogHeader extends LitElement {
    static styles = [
        sharedStyles,
        css`
      :host {
        display: block;
        background-color: var(--color-bg-card);
        border-bottom: 1px solid var(--color-border);
      }

      .container {
        max-width: 80rem; /* 7xl */
        margin: 0 auto;
        padding: 0 var(--space-4);
      }

      @media (min-width: 640px) {
        .container { padding: 0 var(--space-6); }
      }
      @media (min-width: 1024px) {
        .container { padding: 0 var(--space-8); }
      }

      .nav-flex {
        display: flex;
        justify-content: space-between;
        height: 4rem; /* 16 */
      }

      .logo-area {
        display: flex;
      }

      .logo {
        flex-shrink: 0;
        display: flex;
        align-items: center;
      }

      .logo a {
        font-size: var(--font-size-xl);
        font-weight: 700;
        color: var(--color-text-primary);
        text-decoration: none;
      }

      .nav-links {
        display: none;
        margin-left: var(--space-6);
        gap: var(--space-8);
      }

      @media (min-width: 640px) {
        .nav-links { display: flex; }
      }

      .nav-item {
        display: inline-flex;
        align-items: center;
        padding: 0 var(--space-1);
        border-bottom: 2px solid transparent;
        font-size: var(--font-size-sm);
        font-weight: 500;
        color: var(--color-text-secondary);
        text-decoration: none;
      }

      .nav-item:hover {
        color: var(--color-text-primary);
      }

      .nav-item.active {
        border-color: #6366f1; /* indigo-500 */
        color: var(--color-text-primary);
      }

      .user-area {
        display: flex;
        align-items: center;
      }

      .avatar {
        height: 2rem;
        width: 2rem;
        border-radius: 9999px;
        background-color: #6366f1; /* indigo-500 */
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 700;
        margin-left: var(--space-3);
      }
    `
    ];

    @property({ type: String }) currentPath = '/';

    render() {
        return html`
      <div class="container">
        <div class="nav-flex">
          <div class="logo-area">
            <div class="logo">
              <a href="/">GPUBROKER</a>
            </div>
            <div class="nav-links">
              <a href="/" class="nav-item ${this.currentPath === '/' ? 'active' : ''}">
                Marketplace
              </a>
              <a href="/settings" class="nav-item ${this.currentPath === '/settings' ? 'active' : ''}">
                Settings
              </a>
            </div>
          </div>
          <div class="user-area">
            <div class="avatar">A</div>
          </div>
        </div>
      </div>
    `;
    }
}

declare global {
    interface HTMLElementTagNameMap {
        'eog-header': EogHeader;
    }
}
