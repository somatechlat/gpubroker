import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import '../components/saas-layout';
import '../components/saas-glass-modal';
import '../components/saas-infra-card';

@customElement('view-broker-setup')
export class ViewBrokerSetup extends LitElement {
    @state() modalOpen = false;
    @state() modalTitle = '';

    createRenderRoot() { return this; }

    openModal(title: string) {
        this.modalTitle = title;
        this.modalOpen = true;
    }

    closeModal() {
        this.modalOpen = false;
    }

    render() {
        return html`
      <saas-layout>
        <!-- Header -->
        <header class="sticky top-0 z-40 bg-white/80 backdrop-blur-md border-b border-gray-100 h-16 flex items-center justify-between px-8">
          <span class="font-semibold text-lg">GPUBroker Control Tower</span>
          <div class="flex items-center gap-2">
            <div class="h-2 w-2 rounded-full bg-saas-success animate-pulse"></div>
            <span class="text-sm font-medium">Cluster Admin</span>
          </div>
        </header>

        <!-- Dashboard Grid (Broker Specific Layout) -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 p-8 h-[calc(100vh-64px-80px)] overflow-y-auto">
          
          <!-- Col 1: Broker Infrastructure -->
          <div class="space-y-6">
            <h2 class="text-2xl font-bold tracking-tight">Cluster Infra</h2>
            <div class="grid gap-4">
              <saas-infra-card name="Listen Stream (Redis)" status="connected" @edit="${() => this.openModal('Configure Redis Stream')}"></saas-infra-card>
              <saas-infra-card name="Offer Ledger (Postgres)" status="connected" @edit="${() => this.openModal('Configure Postgres')}"></saas-infra-card>
              <saas-infra-card name="Payment Bus (Stripe/Crypto)" status="pending" @edit="${() => this.openModal('Configure Payments')}"></saas-infra-card>
            </div>
          </div>

          <!-- Col 2: GPU Nodes (Tenants) -->
          <div class="space-y-6">
            <div class="flex items-center justify-between">
              <h2 class="text-2xl font-bold tracking-tight">Compute Nodes</h2>
              <button @click="${() => this.openModal('New Node')}" class="rounded-lg bg-black px-4 py-2 text-sm font-medium text-white hover:bg-gray-800">
                + Provision Node
              </button>
            </div>
            
            <div class="grid gap-4">
              <div class="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
                 <div class="flex items-center justify-between">
                   <div class="flex items-center gap-4">
                     <div class="h-10 w-10 rounded-lg bg-black text-white flex items-center justify-center font-bold font-mono">H100</div>
                     <div>
                       <h3 class="font-semibold">Cluster Alpha-1</h3>
                       <p class="text-xs text-gray-500">8x H100 • 640GB VRAM</p>
                     </div>
                   </div>
                   <span class="rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-700">Online</span>
                 </div>
              </div>
            </div>
          </div>

        </div>

        <!-- Footer / Launch Bar -->
        <div class="fixed bottom-0 left-0 right-0 h-20 bg-white border-t border-gray-100 flex items-center justify-center px-8 z-40">
           <button class="w-full max-w-4xl rounded-xl bg-black h-12 text-white font-bold uppercase tracking-widest hover:bg-gray-900 transition-colors shadow-lg">
             Initialize Cluster
           </button>
        </div>

        <!-- Glass Modal -->
        <saas-glass-modal ?open="${this.modalOpen}" title="${this.modalTitle}" @close="${this.closeModal}">
          <div class="space-y-4">
            <div>
               <p class="text-sm text-gray-600 mb-4">Configure the connection parameters for this infrastructure component.</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Service URL</label>
              <input type="text" class="w-full rounded-lg border border-gray-200 px-4 py-2 focus:border-black focus:ring-black" placeholder="service-url" />
            </div>
            <div class="pt-4 flex justify-end gap-3">
              <button @click="${this.closeModal}" class="px-4 py-2 text-sm font-medium text-gray-600 hover:text-black">Cancel</button>
              <button @click="${this.closeModal}" class="px-6 py-2 rounded-lg bg-black text-sm font-medium text-white hover:bg-gray-900">Save</button>
            </div>
          </div>
        </saas-glass-modal>

      </saas-layout>
    `;
    }
}
