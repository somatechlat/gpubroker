# Design Document: GPUBROKER Landing Page

## Overview

Static marketing landing page for GPUBROKER at `gpubroker.live`. Dark theme with green accents, fully responsive, optimized for conversion.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GPUBROKER LANDING PAGE                        │
│                    (Static Site - S3/CloudFront)                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                     index.html                           │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │  Navigation (sticky)                             │    │    │
│  │  │  - Logo | Features | Pricing | How It Works     │    │    │
│  │  │  - Login | CTA Button                           │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │  Hero Section                                    │    │    │
│  │  │  - Headline + Subheadline                       │    │    │
│  │  │  - Primary CTA + Secondary CTA                  │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │  Features Section (4 cards)                      │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │  Pricing Section (5 plans)                       │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │  How It Works (4 steps)                          │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │  Footer                                          │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  css/styles.css                                          │    │
│  │  - CSS Variables (colors, spacing, typography)          │    │
│  │  - Mobile-first responsive design                       │    │
│  │  - Dark theme with green accents                        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  js/main.js                                              │    │
│  │  - Smooth scrolling                                     │    │
│  │  - Mobile menu toggle                                   │    │
│  │  - Analytics tracking                                   │    │
│  │  - Scroll animations                                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │  admin.gpubroker.live/checkout │
              │  ?plan={trial|basic|pro|corp|  │
              │         enterprise}            │
              └───────────────────────────────┘
```

## Design System

### Color Palette
```css
:root {
  /* Primary Colors */
  --color-bg-primary: #0a0a0a;        /* Main background */
  --color-bg-secondary: #111111;      /* Card backgrounds */
  --color-bg-tertiary: #1a1a1a;       /* Elevated surfaces */
  
  /* Accent Colors */
  --color-accent-primary: #00ff88;    /* Primary green */
  --color-accent-secondary: #00cc6a;  /* Darker green */
  --color-accent-glow: rgba(0, 255, 136, 0.2);
  
  /* Text Colors */
  --color-text-primary: #ffffff;
  --color-text-secondary: #a0a0a0;
  --color-text-muted: #666666;
  
  /* Status Colors */
  --color-success: #00ff88;
  --color-warning: #ffaa00;
  --color-error: #ff4444;
  
  /* Border */
  --color-border: #2a2a2a;
}
```

### Typography
```css
:root {
  --font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-size-xs: 0.75rem;    /* 12px */
  --font-size-sm: 0.875rem;   /* 14px */
  --font-size-base: 1rem;     /* 16px */
  --font-size-lg: 1.125rem;   /* 18px */
  --font-size-xl: 1.25rem;    /* 20px */
  --font-size-2xl: 1.5rem;    /* 24px */
  --font-size-3xl: 2rem;      /* 32px */
  --font-size-4xl: 2.5rem;    /* 40px */
  --font-size-5xl: 3rem;      /* 48px */
}
```

### Spacing
```css
:root {
  --spacing-xs: 0.25rem;   /* 4px */
  --spacing-sm: 0.5rem;    /* 8px */
  --spacing-md: 1rem;      /* 16px */
  --spacing-lg: 1.5rem;    /* 24px */
  --spacing-xl: 2rem;      /* 32px */
  --spacing-2xl: 3rem;     /* 48px */
  --spacing-3xl: 4rem;     /* 64px */
}
```

## Component Specifications

### Navigation
- Fixed position, transparent on top, solid on scroll
- Logo (left), menu links (center), CTA (right)
- Mobile: hamburger menu with slide-in drawer
- Height: 72px desktop, 64px mobile

### Hero Section
- Full viewport height (100vh)
- Centered content with gradient overlay
- Animated background (subtle grid pattern)
- Primary CTA: Green button with glow effect
- Secondary CTA: Ghost button (outline)

### Features Section
- 4 feature cards in 2x2 grid (desktop), 1 column (mobile)
- Each card: icon (SVG), title, description
- Hover effect: subtle lift and border glow
- Icons: GPU, AI Brain, Analytics Chart, Multi-Cloud

### Pricing Section
- 5 plan cards in horizontal scroll (mobile) or flex row (desktop)
- Pro plan highlighted with "Popular" badge
- Each card: plan name, price, token count, features list, CTA
- CTA links to: `https://admin.gpubroker.live/checkout?plan={plan}`

### How It Works Section
- 4 steps in horizontal timeline (desktop), vertical (mobile)
- Each step: number badge, icon, title, description
- Connecting line between steps
- Steps: Choose Plan → Pay with PayPal → Activate Pod → Start Using

### Footer
- Dark background with subtle border top
- 3 columns: Company info, Links, Contact
- Copyright at bottom
- Social icons (if applicable)

## File Structure

```
gpubrokerlandingpage/
├── index.html              # Main HTML file
├── css/
│   └── styles.css          # All styles (mobile-first)
├── js/
│   └── main.js             # Interactivity
├── images/
│   ├── logo.svg            # GPUBROKER logo
│   ├── favicon.ico         # Favicon
│   └── og-image.png        # Open Graph image
└── README.md               # Deployment instructions
```

## SEO & Meta

```html
<title>GPUBROKER - GPU Brokerage Platform with AI Agents</title>
<meta name="description" content="Access GPU computing power with intelligent AI agents. Real-time analytics, multi-provider support, and automated optimization.">
<meta property="og:title" content="GPUBROKER - GPU Brokerage Platform">
<meta property="og:description" content="Access GPU computing power with intelligent AI agents.">
<meta property="og:image" content="https://gpubroker.live/images/og-image.png">
<meta property="og:url" content="https://gpubroker.live">
```

## Analytics Events

```javascript
// Track CTA clicks
gtag('event', 'cta_click', {
  'event_category': 'engagement',
  'event_label': 'hero_primary'
});

// Track plan selection
gtag('event', 'select_plan', {
  'event_category': 'conversion',
  'event_label': plan_name,
  'value': plan_price
});

// Track scroll depth
gtag('event', 'scroll_depth', {
  'event_category': 'engagement',
  'event_label': '50%'
});
```

## Responsive Breakpoints

```css
/* Mobile first */
/* Default: 320px - 767px */

/* Tablet */
@media (min-width: 768px) { }

/* Desktop */
@media (min-width: 1024px) { }

/* Large Desktop */
@media (min-width: 1440px) { }
```

## Performance Targets

- First Contentful Paint: < 1.5s
- Largest Contentful Paint: < 2.5s
- Time to Interactive: < 3s
- Lighthouse Score: > 90 (Performance, Accessibility, SEO)
- Total page size: < 500KB

## Deployment

- Host: AWS S3 + CloudFront
- Domain: gpubroker.live
- SSL: AWS Certificate Manager
- Cache: 1 year for static assets, 1 hour for HTML
