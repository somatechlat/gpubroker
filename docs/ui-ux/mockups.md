# GPUBROKER UI/UX Mockups & Design System

Reference Design Specifications - Not Final Implementation

This document consolidates all UI/UX elements, components, data structures, and interface specifications found throughout the GPUBROKER codebase for design reference.

---

## Design Philosophy

### Core Principles
- **Truth**: Only real data from actual provider APIs
- **Simplicity**: Clean, uncluttered interfaces with clear hierarchy
- **Elegance**: Beautiful, modern design with smooth interactions
- **Performance**: Fast loading, real-time updates, responsive design
- **Accessibility**: WCAG 2.1 AA compliance, keyboard navigation

### Visual Identity
- **Modern SaaS Aesthetic**: Clean lines, generous whitespace, subtle shadows
- **Data-Driven Design**: Charts, graphs, and metrics prominently displayed
- **Professional**: Enterprise-ready with consumer-friendly usability
- **Trust & Reliability**: Consistent branding, clear status indicators

---

## Color System

### Primary Palette
```css
primary: {
  50: '#eff6ff',   /* Ultra light - backgrounds */
  100: '#dbeafe',  /* Light - hover states */
  200: '#bfdbfe',  /* Subtle - borders */
  300: '#93c5fd',  /* Muted - secondary text */
  400: '#60a5fa',  /* Medium - interactive elements */
  500: '#3b82f6',  /* Base - primary buttons, links */
  600: '#2563eb',  /* Dark - button hover */
  700: '#1d4ed8',  /* Darker - active states */
  800: '#1e40af',  /* Very dark - headings */
  900: '#1e3a8a'   /* Darkest - emphasis */
}
```

### Semantic Colors
```css
success: {
  50: '#f0fdf4' → 900: '#14532d'  /* Green spectrum */
}
warning: {
  50: '#fffbeb' → 900: '#78350f'  /* Amber spectrum */
}
secondary: {
  50: '#fef2f2' → 900: '#7f1d1d'  /* Red spectrum */
}
```

### Neutral Palette
```css
gray: {
  50: '#f9fafb',   /* Background light */
  100: '#f3f4f6',  /* Background subtle */
  200: '#e5e7eb',  /* Border light */
  300: '#d1d5db',  /* Border default */
  400: '#9ca3af',  /* Text muted */
  500: '#6b7280',  /* Text secondary */
  600: '#4b5563',  /* Text default */
  700: '#374151',  /* Text emphasis */
  800: '#1f2937',  /* Text strong */
  900: '#111827'   /* Text maximum */
}
```

---

## Component System

### Base Components
```css
/* Buttons */
.btn-primary {
  @apply bg-primary-600 hover:bg-primary-700 text-white 
         font-medium py-2 px-4 rounded-lg transition-colors duration-200;
}

.btn-secondary {
  @apply bg-gray-200 hover:bg-gray-300 text-gray-900 
         font-medium py-2 px-4 rounded-lg transition-colors duration-200;
}

/* Cards */
.card {
  @apply bg-white dark:bg-gray-800 rounded-xl shadow-sm 
         border border-gray-200 dark:border-gray-700 p-6;
}

/* Input Fields */
.input-field {
  @apply w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm 
         focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500;
}
```

### Animation System
```css
/* Entrance Animations */
.animate-fade-in { animation: fadeIn 0.5s ease-in-out; }
.animate-slide-up { animation: slideUp 0.3s ease-out; }
.animate-pulse-slow { animation: pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite; }

/* Loading States */
.spinner {
  @apply inline-block w-4 h-4 border-2 border-current border-r-transparent rounded-full;
  animation: spin 1s linear infinite;
}
```

---

## Responsive Layout System

### Breakpoints
```javascript
screens: {
  'sm': '640px',   // Mobile landscape
  'md': '768px',   // Tablet portrait
  'lg': '1024px',  // Tablet landscape / Small desktop
  'xl': '1280px',  // Desktop
  '2xl': '1536px'  // Large desktop
}
```

---

## Data Models for UI

### Core Data Structures
```typescript
// GPU Offer Interface (from Provider Service)
interface GPUOffer {
  id: string
  provider: string
  gpu_type: string
  gpu_memory_gb: number
  cpu_cores: number
  ram_gb: number
  storage_gb: number
  price_per_hour: number
  region: string
  availability: 'available' | 'limited' | 'unavailable'
  sla_uptime?: number
  compliance_tags: string[]
  last_updated: Date
}

// KPI Metrics Interface (from KPI Service)
interface GPUMetrics {
  gpu_type: string
  provider: string
  avg_price_per_hour: number
  cost_per_token?: number
  cost_per_gflop?: number
  availability_score: number
  reliability_score: number
  performance_score: number
  region: string
  last_updated: Date
}

// Provider Status Interface
interface ProviderStatus {
  provider: string
  status: 'healthy' | 'degraded' | 'down'
  last_check: Date
  response_time_ms: number
  error_message?: string
}

// Market Insights Interface
interface MarketInsights {
  total_providers: number
  total_offers: number
  cheapest_gpu_offer: {
    provider: string
    gpu_type: string
    price_per_hour: number
    region: string
  }
  most_expensive_gpu_offer: {
    provider: string
    gpu_type: string
    price_per_hour: number
    region: string
  }
  avg_market_price: number
  price_trend_7d: number
  demand_hotspots: string[]
  supply_constraints: string[]
  generated_at: Date
}

// User Interface (from Auth Service)
interface User {
  id: string
  email: string
  full_name: string
  organization?: string
  is_active: boolean
  created_at: Date
}
```

---

## Dark Mode Implementation

### Theme System
```css
/* Dark mode color overrides */
.dark {
  --bg-primary: #111827;
  --bg-secondary: #1f2937;
  --bg-tertiary: #374151;
  --text-primary: #f9fafb;
  --text-secondary: #d1d5db;
  --text-muted: #9ca3af;
  --border-primary: #374151;
  --border-secondary: #4b5563;
}

/* Component dark mode styles */
.card {
  @apply bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700;
}

.btn-secondary {
  @apply bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100;
}

.input-field {
  @apply bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600 
         text-gray-900 dark:text-gray-100;
}
```

---

*Document Version: 1.0*
*Last Updated: December 2025*
