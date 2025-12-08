/*
⚠️ WARNING: REAL IMPLEMENTATION ONLY ⚠️
We do NOT mock, bypass, or invent data.
We use ONLY real servers, real APIs, and real data.
This codebase follows principles of truth, simplicity, and elegance.
*/

'use client'

import { Header as DashboardHeader } from '@/components/layout/Header'
import { ProviderGrid } from '@/components/providers/ProviderGrid'
import { FilterPanel } from '@/components/filters/FilterPanel'
import { KPIOverview } from '@/components/kpi/KPIOverview'
import { Suspense } from 'react'

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <DashboardHeader />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* KPI Overview Section */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
            Market Overview
          </h2>
          <Suspense fallback={<div className="animate-pulse bg-gray-200 h-32 rounded-lg" />}>
            <KPIOverview />
          </Suspense>
        </div>

        {/* Main Content Area */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Filter Sidebar */}
          <div className="lg:col-span-1">
            <div className="sticky top-4">
              <FilterPanel />
            </div>
          </div>

          {/* Provider Grid */}
          <div className="lg:col-span-3">
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                  GPU Offers
                </h2>
                <div className="flex items-center space-x-4">
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    Real-time pricing from multiple providers
                  </span>
                </div>
              </div>
              
              <Suspense fallback={<div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="animate-pulse bg-gray-200 h-64 rounded-lg" />
                ))}
              </div>}>
                <ProviderGrid />
              </Suspense>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
