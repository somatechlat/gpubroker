⚠️ **WARNING: REAL IMPLEMENTATION ONLY** ⚠️

> **We do NOT mock, bypass, or invent data. We use ONLY real servers, real APIs, and real data. This codebase follows principles of truth, simplicity, and elegance in every line of code.**

---

# 🎨 GPUBROKER UI/UX MOCKUPS & DESIGN SYSTEM

**Reference Design Specifications** - *Not Final Implementation*

This document consolidates all UI/UX elements, components, data structures, and interface specifications found throughout the GPUBROKER codebase for design reference.

---

## 🎯 **DESIGN PHILOSOPHY**

### **Core Principles**
- **Truth**: Only real data from actual provider APIs
- **Simplicity**: Clean, uncluttered interfaces with clear hierarchy
- **Elegance**: Beautiful, modern design with smooth interactions
- **Performance**: Fast loading, real-time updates, responsive design
- **Accessibility**: WCAG 2.1 AA compliance, keyboard navigation

### **Visual Identity**
- **Modern SaaS Aesthetic**: Clean lines, generous whitespace, subtle shadows
- **Data-Driven Design**: Charts, graphs, and metrics prominently displayed
- **Professional**: Enterprise-ready with consumer-friendly usability
- **Trust & Reliability**: Consistent branding, clear status indicators

---

## 🎨 **COLOR SYSTEM**

### **Primary Palette**
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

### **Semantic Colors**
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

### **Neutral Palette**
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

## 🧩 **COMPONENT SYSTEM**

### **Base Components**
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

### **Animation System**
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

/* Keyframes */
@keyframes fadeIn {
  '0%': { opacity: '0' }
  '100%': { opacity: '1' }
}

@keyframes slideUp {
  '0%': { transform: 'translateY(10px)', opacity: '0' }
  '100%': { transform: 'translateY(0)', opacity: '1' }
}
```

---

## 📱 **RESPONSIVE LAYOUT SYSTEM**

### **Breakpoints**
```javascript
// Tailwind CSS Responsive Design
screens: {
  'sm': '640px',   // Mobile landscape
  'md': '768px',   // Tablet portrait
  'lg': '1024px',  // Tablet landscape / Small desktop
  'xl': '1280px',  // Desktop
  '2xl': '1536px'  // Large desktop
}
```

### **Grid System**
```jsx
// Main Dashboard Layout
<div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
  {/* Sidebar - 1/4 width on large screens */}
  <div className="lg:col-span-1">
    <FilterPanel />
  </div>
  
  {/* Main Content - 3/4 width on large screens */}
  <div className="lg:col-span-3">
    <ProviderGrid />
  </div>
</div>

// Provider Cards Grid
<div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
  {providers.map(provider => (
    <ProviderCard key={provider.id} provider={provider} />
  ))}
</div>
```

---

## 🏗️ **PAGE LAYOUTS & STRUCTURE**

### **1. Dashboard Layout**
```jsx
// Main Dashboard Structure
export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <DashboardHeader />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* KPI Overview Section */}
        <section className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
            Market Overview
          </h2>
          <KPIOverview />
        </section>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Filter Sidebar */}
          <aside className="lg:col-span-1">
            <div className="sticky top-4">
              <FilterPanel />
            </div>
          </aside>

          {/* Provider Grid */}
          <main className="lg:col-span-3">
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                  GPU Offers
                </h2>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  Real-time pricing from multiple providers
                </span>
              </div>
              <ProviderGrid />
            </div>
          </main>
        </div>
      </main>
    </div>
  )
}
```

### **2. Authentication Layout**
```jsx
// Auth Page Structure (Login/Register)
<div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
  <div className="max-w-md w-full space-y-8">
    <div className="text-center">
      <h2 className="mt-6 text-3xl font-bold text-gray-900 dark:text-white">
        Sign in to GPUBROKER
      </h2>
      <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
        Access real-time GPU marketplace
      </p>
    </div>
    <form className="mt-8 space-y-6">
      {/* Form fields */}
    </form>
  </div>
</div>
```

---

## 🃏 **COMPONENT SPECIFICATIONS**

### **1. Provider Card Component**
```typescript
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

// Component Structure
<div className="card hover:shadow-md transition-shadow duration-200">
  {/* Provider Header */}
  <div className="flex justify-between items-start mb-4">
    <div className="flex items-center space-x-3">
      <img src={providerLogo} className="w-8 h-8 rounded" />
      <div>
        <h3 className="font-semibold text-gray-900 dark:text-white">
          {offer.provider}
        </h3>
        <p className="text-sm text-gray-500">{offer.region}</p>
      </div>
    </div>
    <AvailabilityBadge status={offer.availability} />
  </div>

  {/* GPU Specifications */}
  <div className="space-y-2 mb-4">
    <div className="flex justify-between">
      <span className="text-sm text-gray-600">GPU</span>
      <span className="font-medium">{offer.gpu_type}</span>
    </div>
    <div className="flex justify-between">
      <span className="text-sm text-gray-600">Memory</span>
      <span className="font-medium">{offer.gpu_memory_gb} GB</span>
    </div>
    <div className="flex justify-between">
      <span className="text-sm text-gray-600">RAM</span>
      <span className="font-medium">{offer.ram_gb} GB</span>
    </div>
  </div>

  {/* KPI Badges */}
  <div className="flex flex-wrap gap-2 mb-4">
    <KPIBadge label="Cost/Token" value="$0.0001" />
    <KPIBadge label="Cost/GFLOP" value="$0.002" />
    <KPIBadge label="Uptime" value="99.2%" />
  </div>

  {/* Pricing & Actions */}
  <div className="flex justify-between items-center">
    <div>
      <span className="text-2xl font-bold text-gray-900 dark:text-white">
        ${offer.price_per_hour}
      </span>
      <span className="text-sm text-gray-500">/hour</span>
    </div>
    <button className="btn-primary">
      Rent Now
    </button>
  </div>
</div>
```

### **2. KPI Overview Component**
```tsx
// Market Overview Dashboard
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
  {/* Total Providers */}
  <div className="card text-center">
    <div className="text-3xl font-bold text-primary-600 mb-2">23</div>
    <div className="text-sm text-gray-600">Active Providers</div>
  </div>

  {/* Total Offers */}
  <div className="card text-center">
    <div className="text-3xl font-bold text-success-600 mb-2">530</div>
    <div className="text-sm text-gray-600">GPU Offers</div>
  </div>

  {/* Average Price */}
  <div className="card text-center">
    <div className="text-3xl font-bold text-warning-600 mb-2">$1.75</div>
    <div className="text-sm text-gray-600">Avg Price/Hour</div>
  </div>

  {/* Price Trend */}
  <div className="card text-center">
    <div className="text-3xl font-bold text-secondary-600 mb-2">-2.3%</div>
    <div className="text-sm text-gray-600">7-Day Trend</div>
  </div>
</div>

// Real-Time Price Chart
<div className="card">
  <h3 className="text-lg font-semibold mb-4">Price Trends</h3>
  <ResponsiveContainer width="100%" height={300}>
    <LineChart data={priceData}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey="timestamp" />
      <YAxis />
      <Tooltip />
      <Line type="monotone" dataKey="price" stroke="#3b82f6" strokeWidth={2} />
    </LineChart>
  </ResponsiveContainer>
</div>
```

### **3. Filter Panel Component**
```tsx
// Advanced Filtering Sidebar
<div className="card space-y-6">
  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
    Filters
  </h3>

  {/* Provider Selection */}
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-2">
      Providers
    </label>
    <div className="space-y-2">
      {providers.map(provider => (
        <label key={provider.id} className="flex items-center">
          <input type="checkbox" className="mr-2" />
          <span className="text-sm">{provider.name}</span>
        </label>
      ))}
    </div>
  </div>

  {/* GPU Type Filter */}
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-2">
      GPU Type
    </label>
    <select className="input-field">
      <option value="">All GPUs</option>
      <option value="A100">NVIDIA A100</option>
      <option value="V100">NVIDIA V100</option>
      <option value="RTX 4090">RTX 4090</option>
      <option value="H100">NVIDIA H100</option>
    </select>
  </div>

  {/* Price Range Slider */}
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-2">
      Price Range ($/hour)
    </label>
    <div className="space-y-2">
      <input type="range" min="0" max="10" step="0.1" className="w-full" />
      <div className="flex justify-between text-xs text-gray-500">
        <span>$0</span>
        <span>$10</span>
      </div>
    </div>
  </div>

  {/* Region Filter */}
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-2">
      Region
    </label>
    <select className="input-field">
      <option value="">All Regions</option>
      <option value="us-east">US East</option>
      <option value="us-west">US West</option>
      <option value="eu-west">EU West</option>
      <option value="ap-southeast">Asia Pacific</option>
    </select>
  </div>

  {/* Compliance Tags */}
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-2">
      Compliance
    </label>
    <div className="space-y-2">
      <label className="flex items-center">
        <input type="checkbox" className="mr-2" />
        <span className="text-sm">GDPR Compliant</span>
      </label>
      <label className="flex items-center">
        <input type="checkbox" className="mr-2" />
        <span className="text-sm">SOC 2 Certified</span>
      </label>
      <label className="flex items-center">
        <input type="checkbox" className="mr-2" />
        <span className="text-sm">HIPAA Ready</span>
      </label>
    </div>
  </div>

  {/* Apply Filters Button */}
  <button className="btn-primary w-full">
    Apply Filters
  </button>
</div>
```

### **4. Header Component**
```tsx
// Main Navigation Header
<header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
  <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div className="flex justify-between items-center h-16">
      {/* Logo */}
      <div className="flex items-center space-x-4">
        <img src="/logo.svg" alt="GPUBROKER" className="h-8 w-auto" />
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">
          GPUBROKER
        </h1>
      </div>

      {/* Navigation Links */}
      <nav className="hidden md:flex space-x-8">
        <a href="/dashboard" className="text-gray-700 hover:text-primary-600">
          Dashboard
        </a>
        <a href="/analytics" className="text-gray-700 hover:text-primary-600">
          Analytics
        </a>
        <a href="/providers" className="text-gray-700 hover:text-primary-600">
          Providers
        </a>
      </nav>

      {/* User Menu */}
      <div className="flex items-center space-x-4">
        {/* AI Assistant Button */}
        <button className="p-2 text-gray-400 hover:text-primary-600">
          <BotIcon className="h-5 w-5" />
        </button>

        {/* Notifications */}
        <button className="p-2 text-gray-400 hover:text-primary-600 relative">
          <BellIcon className="h-5 w-5" />
          <span className="absolute top-0 right-0 h-2 w-2 bg-red-500 rounded-full"></span>
        </button>

        {/* Theme Toggle */}
        <button className="p-2 text-gray-400 hover:text-primary-600">
          <SunIcon className="h-5 w-5 hidden dark:block" />
          <MoonIcon className="h-5 w-5 block dark:hidden" />
        </button>

        {/* User Profile */}
        <div className="relative">
          <button className="flex items-center space-x-2 text-gray-700 dark:text-gray-200">
            <img src="/avatar.jpg" className="h-8 w-8 rounded-full" />
            <span className="text-sm font-medium">John Doe</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</header>
```

---

## 📊 **DATA VISUALIZATION COMPONENTS**

### **1. Real-Time Price Charts**
```tsx
// Price Trend Visualization with D3/Recharts
<ResponsiveContainer width="100%" height={400}>
  <LineChart data={priceHistoryData}>
    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
    <XAxis 
      dataKey="timestamp" 
      tick={{ fontSize: 12, fill: '#6b7280' }}
      tickFormatter={(value) => format(new Date(value), 'MMM dd')}
    />
    <YAxis 
      tick={{ fontSize: 12, fill: '#6b7280' }}
      tickFormatter={(value) => `$${value}`}
    />
    <Tooltip 
      contentStyle={{
        backgroundColor: '#1f2937',
        border: 'none',
        borderRadius: '8px',
        color: '#ffffff'
      }}
      labelFormatter={(value) => format(new Date(value), 'PPP')}
      formatter={(value, name) => [`$${value}`, `${name} Price/Hour`]}
    />
    <Legend />
    <Line 
      type="monotone" 
      dataKey="runpod_price" 
      stroke="#3b82f6" 
      strokeWidth={2}
      name="RunPod"
    />
    <Line 
      type="monotone" 
      dataKey="vastai_price" 
      stroke="#10b981" 
      strokeWidth={2}
      name="Vast.ai"
    />
    <Line 
      type="monotone" 
      dataKey="coreweave_price" 
      stroke="#f59e0b" 
      strokeWidth={2}
      name="CoreWeave"
    />
  </LineChart>
</ResponsiveContainer>
```

### **2. Market Heat Map**
```tsx
// GPU Availability Heat Map
<div className="card">
  <h3 className="text-lg font-semibold mb-4">GPU Availability by Region</h3>
  <div className="grid grid-cols-4 gap-2">
    {regions.map(region => (
      <div key={region.id} className="text-center">
        <div 
          className={`w-full h-16 rounded-lg flex items-center justify-center text-white font-medium ${
            region.availability > 80 ? 'bg-green-500' :
            region.availability > 50 ? 'bg-yellow-500' : 'bg-red-500'
          }`}
        >
          {region.availability}%
        </div>
        <p className="text-xs mt-1 text-gray-600">{region.name}</p>
      </div>
    ))}
  </div>
</div>
```

### **3. Provider Performance Radar Chart**
```tsx
// Multi-dimensional Provider Analysis
<ResponsiveContainer width="100%" height={300}>
  <RadarChart data={providerMetrics}>
    <PolarGrid />
    <PolarAngleAxis dataKey="metric" tick={{ fontSize: 12 }} />
    <PolarRadiusAxis angle={30} domain={[0, 100]} tickCount={6} />
    <Radar
      name="RunPod"
      dataKey="runpod"
      stroke="#3b82f6"
      fill="#3b82f6"
      fillOpacity={0.1}
      strokeWidth={2}
    />
    <Radar
      name="Vast.ai"
      dataKey="vastai"
      stroke="#10b981"
      fill="#10b981"
      fillOpacity={0.1}
      strokeWidth={2}
    />
    <Legend />
  </RadarChart>
</ResponsiveContainer>
```

---

## 🤖 **AI ASSISTANT INTERFACE**

### **GPUAgenticHelper Component**
```tsx
// Floating AI Assistant
<div className="fixed bottom-6 right-6 z-50">
  {/* Trigger Button */}
  <button 
    onClick={toggleAssistant}
    className="bg-primary-600 hover:bg-primary-700 text-white p-3 rounded-full shadow-lg transition-colors"
  >
    <BotIcon className="h-6 w-6" />
  </button>

  {/* Chat Interface */}
  {isOpen && (
    <div className="absolute bottom-16 right-0 w-96 h-96 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex justify-between items-center">
          <h3 className="font-semibold text-gray-900 dark:text-white">
            AI Assistant
          </h3>
          <button onClick={toggleAssistant} className="text-gray-400 hover:text-gray-600">
            <XIcon className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4">
        {messages.map(message => (
          <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-xs p-3 rounded-lg ${
              message.role === 'user' 
                ? 'bg-primary-600 text-white' 
                : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
            }`}>
              {message.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 dark:bg-gray-700 p-3 rounded-lg">
              <div className="spinner"></div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <form onSubmit={sendMessage} className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          aria-label="Ask about GPU recommendations…"
            className="flex-1 input-field text-sm"
          />
          <button type="submit" className="btn-primary text-sm">
            Send
          </button>
        </form>
      </div>
    </div>
  )}
</div>
```

---

## 📱 **MOBILE RESPONSIVENESS**

### **Mobile-First Approach**
```tsx
// Responsive Provider Grid
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
  {/* Cards automatically adapt */}
</div>

// Mobile Navigation
<div className="md:hidden">
  <button onClick={toggleMobileMenu} className="p-2">
    <MenuIcon className="h-6 w-6" />
  </button>
  
  {isMobileMenuOpen && (
    <div className="absolute top-16 left-0 right-0 bg-white shadow-lg">
      <nav className="p-4 space-y-4">
        <a href="/dashboard" className="block text-gray-700">Dashboard</a>
        <a href="/analytics" className="block text-gray-700">Analytics</a>
        <a href="/providers" className="block text-gray-700">Providers</a>
      </nav>
    </div>
  )}
</div>

// Mobile-Optimized Cards
<div className="card">
  {/* Stacked layout on mobile */}
  <div className="space-y-4 sm:space-y-0 sm:flex sm:justify-between sm:items-center">
    <div className="text-center sm:text-left">
      <h3 className="font-semibold">{provider.name}</h3>
      <p className="text-sm text-gray-500">{gpu.type}</p>
    </div>
    <div className="text-center sm:text-right">
      <div className="text-lg font-bold">${price}/hr</div>
      <button className="btn-primary w-full sm:w-auto mt-2 sm:mt-0">
        Rent Now
      </button>
    </div>
  </div>
</div>
```

---

## 🌙 **DARK MODE IMPLEMENTATION**

### **Theme System**
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

### **Theme Toggle Logic**
```tsx
// Theme Context
const ThemeContext = createContext({
  theme: 'light',
  toggleTheme: () => {}
})

// Theme Provider
export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState('light')
  
  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light'
    setTheme(newTheme)
    localStorage.setItem('theme', newTheme)
    document.documentElement.classList.toggle('dark', newTheme === 'dark')
  }
  
  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}
```

---

## 🔒 **AUTHENTICATION INTERFACES**

### **Login Form**
```tsx
<form className="space-y-6" onSubmit={handleLogin}>
  <div>
    <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
      Email Address
    </label>
    <input
      type="email"
      required
      className="input-field mt-1"
      aria-label="Enter your email"
      value={email}
      onChange={(e) => setEmail(e.target.value)}
    />
  </div>

  <div>
    <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
      Password
    </label>
    <div className="relative mt-1">
      <input
        type={showPassword ? 'text' : 'password'}
        required
        className="input-field"
        aria-label="Enter your password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <button
        type="button"
        className="absolute inset-y-0 right-0 pr-3 flex items-center"
        onClick={() => setShowPassword(!showPassword)}
      >
        {showPassword ? <EyeOffIcon className="h-5 w-5" /> : <EyeIcon className="h-5 w-5" />}
      </button>
    </div>
  </div>

  <div className="flex items-center justify-between">
    <label className="flex items-center">
      <input type="checkbox" className="mr-2" />
      <span className="text-sm text-gray-600 dark:text-gray-400">Remember me</span>
    </label>
    <a href="/forgot-password" className="text-sm text-primary-600 hover:text-primary-500">
      Forgot password?
    </a>
  </div>

  <button type="submit" className="btn-primary w-full" disabled={isLoading}>
    {isLoading ? (
      <div className="flex items-center justify-center">
        <div className="spinner mr-2"></div>
        Signing in...
      </div>
    ) : (
      'Sign in'
    )}
  </button>
</form>
```

---

## 📊 **DATA MODELS FOR UI**

### **Core Data Structures**
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

## 🎛️ **STATE MANAGEMENT**

### **Zustand Store Structure**
```typescript
// Main App State
interface AppState {
  // User & Auth
  user: User | null
  isAuthenticated: boolean
  token: string | null
  
  // Providers & Offers
  providers: Provider[]
  offers: GPUOffer[]
  selectedProvider: string | null
  
  // Filters
  filters: {
    providers: string[]
    gpuTypes: string[]
    priceRange: [number, number]
    regions: string[]
    complianceTags: string[]
  }
  
  // UI State
  theme: 'light' | 'dark'
  sidebarOpen: boolean
  assistantOpen: boolean
  loading: {
    offers: boolean
    providers: boolean
    kpis: boolean
  }
  
  // Actions
  setUser: (user: User | null) => void
  setOffers: (offers: GPUOffer[]) => void
  updateFilters: (filters: Partial<AppState['filters']>) => void
  toggleTheme: () => void
  toggleSidebar: () => void
  toggleAssistant: () => void
}

// Create Store
const useAppStore = create<AppState>((set, get) => ({
  // Initial state
  user: null,
  isAuthenticated: false,
  token: null,
  providers: [],
  offers: [],
  selectedProvider: null,
  filters: {
    providers: [],
    gpuTypes: [],
    priceRange: [0, 10],
    regions: [],
    complianceTags: []
  },
  theme: 'light',
  sidebarOpen: false,
  assistantOpen: false,
  loading: {
    offers: false,
    providers: false,
    kpis: false
  },
  
  // Actions
  setUser: (user) => set({ user, isAuthenticated: !!user }),
  setOffers: (offers) => set({ offers }),
  updateFilters: (newFilters) => set(state => ({
    filters: { ...state.filters, ...newFilters }
  })),
  toggleTheme: () => set(state => ({
    theme: state.theme === 'light' ? 'dark' : 'light'
  })),
  toggleSidebar: () => set(state => ({ sidebarOpen: !state.sidebarOpen })),
  toggleAssistant: () => set(state => ({ assistantOpen: !state.assistantOpen }))
}))
```

---

## 🔄 **API INTEGRATION PATTERNS**

### **React Query Hooks**
```typescript
// Custom Hooks for API Integration
export function useOffers(filters?: FilterParams) {
  return useQuery({
    queryKey: ['offers', filters],
    queryFn: () => api.offers.getAll(filters),
    staleTime: 30000, // 30 seconds
    refetchInterval: 60000, // 1 minute
    refetchOnWindowFocus: false
  })
}

export function useProviders() {
  return useQuery({
    queryKey: ['providers'],
    queryFn: () => api.providers.getAll(),
    staleTime: 300000, // 5 minutes
    refetchOnWindowFocus: false
  })
}

export function useKPIs(gpuType: string) {
  return useQuery({
    queryKey: ['kpis', gpuType],
    queryFn: () => api.kpis.getGPUMetrics(gpuType),
    staleTime: 60000, // 1 minute
    enabled: !!gpuType
  })
}

export function useMarketInsights() {
  return useQuery({
    queryKey: ['market-insights'],
    queryFn: () => api.insights.getMarket(),
    staleTime: 120000, // 2 minutes
    refetchInterval: 300000 // 5 minutes
  })
}

// Mutations for User Actions
export function useRentGPU() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (params: RentGPUParams) => api.rentals.create(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['offers'] })
      toast.success('GPU rental initiated successfully!')
    },
    onError: (error) => {
      toast.error(`Rental failed: ${error.message}`)
    }
  })
}
```

### **Real-Time Updates**
```typescript
// WebSocket Connection for Live Updates
export function useRealtimeOffers() {
  const { setOffers } = useAppStore()
  
  useEffect(() => {
    const ws = new WebSocket(process.env.NEXT_PUBLIC_WS_URL + '/offers')
    
    ws.onmessage = (event) => {
      const updatedOffers = JSON.parse(event.data)
      setOffers(updatedOffers)
    }
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      toast.error('Lost real-time connection. Prices may be outdated.')
    }
    
    return () => {
      ws.close()
    }
  }, [setOffers])
}
```

---

## 📱 **TECHNOLOGY STACK SPECIFICATIONS**

### **Frontend Dependencies**
```json
{
  "dependencies": {
    "next": "14.1.0",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "typescript": "5.3.3",
    "tailwindcss": "3.4.1",
    "@headlessui/react": "1.7.18",
    "@heroicons/react": "2.0.18",
    "d3": "7.8.5",
    "recharts": "2.10.3",
    "lucide-react": "0.317.0",
    "clsx": "2.1.0",
    "framer-motion": "10.18.0",
    "zustand": "4.4.7",
    "@tanstack/react-query": "5.17.9",
    "axios": "1.6.5",
    "date-fns": "3.2.0",
    "react-hot-toast": "2.4.1",
    "react-hook-form": "7.49.2",
    "zod": "3.22.4"
  }
}
```

### **Performance Optimizations**
```typescript
// Code Splitting & Lazy Loading
const ProviderGrid = lazy(() => import('@/components/providers/ProviderGrid'))
const KPIOverview = lazy(() => import('@/components/kpi/KPIOverview'))
const AIAssistant = lazy(() => import('@/components/ai/AIAssistant'))

// Memoized Components
const MemoizedProviderCard = memo(ProviderCard, (prevProps, nextProps) => 
  prevProps.offer.id === nextProps.offer.id && 
  prevProps.offer.price_per_hour === nextProps.offer.price_per_hour
)

// Virtual Scrolling for Large Lists
import { FixedSizeList as List } from 'react-window'

function VirtualizedOfferList({ offers }) {
  const Row = ({ index, style }) => (
    <div style={style}>
      <ProviderCard offer={offers[index]} />
    </div>
  )
  
  return (
    <List
      height={600}
      itemCount={offers.length}
      itemSize={280}
      width="100%"
    >
      {Row}
    </List>
  )
}
```

---

## 🎨 **DESIGN TOKENS & VARIABLES**

### **Spacing System**
```css
/* Tailwind Spacing Scale */
.space-1 { margin: 0.25rem; }    /* 4px */
.space-2 { margin: 0.5rem; }     /* 8px */
.space-3 { margin: 0.75rem; }    /* 12px */
.space-4 { margin: 1rem; }       /* 16px */
.space-6 { margin: 1.5rem; }     /* 24px */
.space-8 { margin: 2rem; }       /* 32px */
.space-12 { margin: 3rem; }      /* 48px */
.space-16 { margin: 4rem; }      /* 64px */
```

### **Typography System**
```css
/* Font Sizes */
.text-xs { font-size: 0.75rem; }     /* 12px */
.text-sm { font-size: 0.875rem; }    /* 14px */
.text-base { font-size: 1rem; }      /* 16px */
.text-lg { font-size: 1.125rem; }    /* 18px */
.text-xl { font-size: 1.25rem; }     /* 20px */
.text-2xl { font-size: 1.5rem; }     /* 24px */
.text-3xl { font-size: 1.875rem; }   /* 30px */

/* Font Weights */
.font-normal { font-weight: 400; }
.font-medium { font-weight: 500; }
.font-semibold { font-weight: 600; }
.font-bold { font-weight: 700; }

/* Line Heights */
.leading-tight { line-height: 1.25; }
.leading-normal { line-height: 1.5; }
.leading-relaxed { line-height: 1.625; }
```

### **Shadow System**
```css
/* Elevation Shadows */
.shadow-sm { box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05); }
.shadow { box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1); }
.shadow-md { box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1); }
.shadow-lg { box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1); }
.shadow-xl { box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1); }
```

---

## 🔧 **BUILD & DEPLOYMENT CONFIG**

### **Next.js Configuration**
```javascript
// next.config.js
const nextConfig = {
  experimental: {
    appDir: true,
  },
  images: {
    domains: ['localhost', 'api.runpod.io', 'console.vast.ai'],
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || '',
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || '',
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
```

### **PostCSS Configuration**
```javascript
// postcss.config.js
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

---

## 📖 **ACCESSIBILITY SPECIFICATIONS**

### **WCAG 2.1 AA Compliance**
```tsx
// Semantic HTML Structure
<main role="main" aria-label="GPU Marketplace Dashboard">
  <section aria-labelledby="market-overview-heading">
    <h2 id="market-overview-heading" className="sr-only">
      Market Overview
    </h2>
    <div className="grid grid-cols-4 gap-4">
      {/* KPI Cards */}
    </div>
  </section>
  
  <section aria-labelledby="gpu-offers-heading">
    <h2 id="gpu-offers-heading">
      Available GPU Offers
    </h2>
    <div role="region" aria-live="polite" aria-label="GPU offers list">
      {/* Provider cards */}
    </div>
  </section>
</main>

// Keyboard Navigation
<div 
  role="button"
  tabIndex={0}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      handleClick()
    }
  }}
  onClick={handleClick}
  aria-label="Rent GPU from RunPod - A100 40GB at $2.50 per hour"
>
  Rent Now
</div>

// Screen Reader Announcements
<div 
  role="status" 
  aria-live="polite" 
  className="sr-only"
>
  {`Loaded ${offers.length} GPU offers. Use arrow keys to navigate.`}
</div>

// Focus Management
useEffect(() => {
  if (isModalOpen) {
    const firstInput = modalRef.current?.querySelector('input')
    firstInput?.focus()
  }
}, [isModalOpen])
```

---

## 📏 **TESTING & QUALITY ASSURANCE**

### **Component Testing Patterns**
```tsx
// Example Test Structure
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ProviderCard from '@/components/providers/ProviderCard'
```

- [x] **Base Components** - Buttons, cards, inputs, forms
- [x] **Data Models** - TypeScript interfaces for all API data
- [ ] **Provider Cards** - GPU offer display components
- [ ] **Filter Panel** - Advanced filtering interface
- [ ] **KPI Dashboard** - Metrics and analytics display
- [ ] **AI Assistant** - Chat interface component
- [ ] **Authentication** - Login/register forms
- [ ] **Navigation** - Header, sidebar, mobile menu
- [ ] **Charts & Graphs** - D3.js/Recharts visualizations
- [ ] **Real-time Updates** - WebSocket integration
- [ ] **Dark Mode** - Theme switching system
- [ ] **Mobile Optimization** - Responsive design testing
- [ ] **Accessibility** - WCAG compliance testing
- [ ] **Performance** - Code splitting, virtualization
- [ ] **Testing** - Component and integration tests
- [ ] **Documentation** - Storybook component library

---

## 🎯 **NEXT STEPS FOR IMPLEMENTATION**

### **Immediate Priorities**
1. **Create Component Library** - Build reusable UI components
2. **Implement Provider Cards** - Core marketplace interface
3. **Add Real-time Updates** - WebSocket price feeds  
4. **Build Filter System** - Advanced search and filtering
5. **Integrate AI Assistant** - GPUAgenticHelper interface
6. **Test Accessibility** - WCAG compliance validation
7. **Performance Optimization** - Lazy loading, virtualization
8. **Mobile Testing** - Responsive design validation

### **Development Workflow**
1. Start with atomic components (buttons, inputs, badges)
2. Build composite components (cards, forms, panels)  
3. Create page layouts (dashboard, auth, analytics)
4. Implement state management (Zustand stores)
5. Add API integration (React Query hooks)
6. Test accessibility (screen readers, keyboard nav)
7. Optimize performance (code splitting, caching)
8. Deploy and monitor (real user metrics)

---

**📖 This document serves as the comprehensive UI/UX reference for GPUBROKER development.**  
*All specifications are extracted from actual codebase files and represent real implementation requirements.*

*Last Updated: October 12, 2025*  
*Status: Reference Material - Ready for Implementation*
