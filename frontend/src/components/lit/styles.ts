
import { css } from 'lit';

export const sharedStyles = css`
  :host {
    /* Typography */
    --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    --font-size-xs: 0.75rem;
    --font-size-sm: 0.875rem;
    --font-size-base: 1rem;
    --font-size-lg: 1.125rem;
    --font-size-xl: 1.25rem;
    --font-size-2xl: 1.5rem;
    --font-size-3xl: 1.875rem;
    --font-size-4xl: 2.25rem;

    /* Colors - Light Theme */
    --color-bg: #f8f9fa;
    --color-bg-card: #ffffff;
    --color-bg-sidebar: #ffffff;
    --color-bg-input: #ffffff;
    --color-bg-hover: #f3f4f6;

    /* Text Colors */
    --color-text-primary: #111827;
    --color-text-secondary: #6b7280;
    --color-text-muted: #9ca3af;
    --color-text-white: #ffffff;

    /* Border Colors */
    --color-border: #e5e7eb;
    --color-border-focus: #10b981;
    --color-border-input: #d1d5db;

    /* Status Colors */
    --color-success: #10b981;
    --color-success-text: #059669;
    --color-error: #ef4444;
    --color-error-text: #dc2626;
    --color-warning: #f59e0b;
    --color-info: #3b82f6;

    /* Brand Colors */
    --color-primary: #111827;
    --color-primary-hover: #1f2937;
    --color-accent: #10b981;

    /* Shadows */
    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    --shadow-card: 0 1px 3px rgba(0, 0, 0, 0.08);

    /* Border Radius */
    --radius-sm: 0.25rem;
    --radius-md: 0.5rem;
    --radius-lg: 0.75rem;
    --radius-xl: 1rem;
    --radius-full: 9999px;

    /* Spacing */
    --space-1: 0.25rem;
    --space-2: 0.5rem;
    --space-3: 0.75rem;
    --space-4: 1rem;
    --space-6: 1.5rem;
    --space-8: 2rem;
  }

  /* Reset */
  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }

  /* Typography Utilities */
  h1 { font-size: var(--font-size-4xl); font-weight: 600; color: var(--color-text-primary); }
  h2 { font-size: var(--font-size-3xl); font-weight: 600; color: var(--color-text-primary); }
  h3 { font-size: var(--font-size-2xl); font-weight: 600; color: var(--color-text-primary); }
  p { font-size: var(--font-size-base); color: var(--color-text-secondary); line-height: 1.5; }

  .text-sm { font-size: var(--font-size-sm); }
  .text-xs { font-size: var(--font-size-xs); }
  .text-muted { color: var(--color-text-muted); }

  /* Flex Utilities */
  .flex { display: flex; }
  .flex-col { flex-direction: column; }
  .items-center { align-items: center; }
  .justify-between { justify-content: space-between; }
  .gap-2 { gap: var(--space-2); }
  .gap-4 { gap: var(--space-4); }

  /* Grid Utilities */
  .grid { display: grid; gap: var(--space-6); }
  .grid-cols-1 { grid-template-columns: repeat(1, 1fr); }
  
  @media (min-width: 768px) {
    .grid-cols-2 { grid-template-columns: repeat(2, 1fr); }
    .grid-cols-3 { grid-template-columns: repeat(3, 1fr); }
  }
`;
