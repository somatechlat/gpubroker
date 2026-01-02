const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:28080';

export interface Provider {
  id: string;
  name: string;
  gpu_type: string;
  price_per_hour: number;
  availability: string;
  region: string;
  memory_gb: number;
  compliance_tags?: string[];
}

export interface FetchProvidersParams {
  page?: number;
  per_page?: number;
  filters?: {
    gpu?: string;
    gpu_type?: string;
    memory_min?: string;
    price_min?: number;
    price_max?: number;
    region?: string;
    availability?: string;
  };
  // Legacy flat params for backwards compatibility
  gpu_type?: string;
  price_min?: number;
  price_max?: number;
  region?: string;
  availability?: string;
}

export interface FetchProvidersResult {
  items: Provider[];
  total?: number;
  page?: number;
  per_page?: number;
}

export async function fetchProviders(params?: FetchProvidersParams): Promise<FetchProvidersResult> {
  try {
    const url = new URL(API_BASE + '/api/v2/providers');
    if (params) {
      // Handle pagination
      if (params.page) url.searchParams.append('page', String(params.page));
      if (params.per_page) url.searchParams.append('per_page', String(params.per_page));

      // Handle nested filters
      if (params.filters) {
        Object.entries(params.filters).forEach(([key, value]) => {
          if (value !== undefined) url.searchParams.append(key, String(value));
        });
      }

      // Handle legacy flat params
      ['gpu_type', 'price_min', 'price_max', 'region', 'availability'].forEach(key => {
        const value = (params as any)[key];
        if (value !== undefined) url.searchParams.append(key, String(value));
      });
    }
    const response = await fetch(url.toString());
    if (!response.ok) throw new Error('Failed to fetch providers');
    const data = await response.json();
    return {
      items: data.offers || data.providers || data.items || [],
      total: data.total,
      page: data.page,
      per_page: data.per_page,
    };
  } catch (error) {
    console.error('Error fetching providers:', error);
    return { items: [] };
  }
}

export async function fetchProviderById(id: string): Promise<Provider | null> {
  try {
    const response = await fetch(API_BASE + '/api/v2/providers/' + id);
    if (!response.ok) throw new Error('Failed to fetch provider');
    return await response.json();
  } catch (error) {
    console.error('Error fetching provider:', error);
    return null;
  }
}
