"""
GPUBROKER Geo-Detection Service

Detects user's country from IP address for country-specific validation.
Uses free IP geolocation APIs with fallback.

Country-specific requirements:
- Ecuador (EC): RUC (13 digits) or Cedula (10 digits) required
- Other countries: Standard email/name registration only
"""
import logging
from typing import Dict, Any, Optional
import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger('gpubrokeradmin.geo')

# Cache TTL for geo lookups (1 hour)
GEO_CACHE_TTL = 3600

# Country-specific validation requirements
COUNTRY_VALIDATIONS = {
    'EC': {  # Ecuador
        'requires_tax_id': True,
        'tax_id_name': 'RUC/Cédula',
        'tax_id_formats': ['ruc', 'cedula'],
        'language': 'es',
    },
    # Add more countries as needed
    # 'CO': {  # Colombia
    #     'requires_tax_id': True,
    #     'tax_id_name': 'NIT/Cédula',
    #     'tax_id_formats': ['nit', 'cedula_co'],
    #     'language': 'es',
    # },
}

# Default for countries without specific requirements
DEFAULT_VALIDATION = {
    'requires_tax_id': False,
    'tax_id_name': None,
    'tax_id_formats': [],
    'language': 'en',
}


class GeoService:
    """Service for IP-based geolocation and country-specific validation."""
    
    # Free geolocation API endpoints (no API key required)
    GEO_APIS = [
        'https://ipapi.co/{ip}/json/',
        'https://ip-api.com/json/{ip}',
        'https://ipwho.is/{ip}',
    ]
    
    @classmethod
    def get_country_from_ip(cls, ip_address: str) -> Dict[str, Any]:
        """
        Detect country from IP address.
        
        Returns:
            {
                'country_code': 'EC',
                'country_name': 'Ecuador',
                'city': 'Quito',
                'region': 'Pichincha',
                'detected': True,
                'source': 'ipapi.co'
            }
        """
        # Check cache first
        cache_key = f'geo:{ip_address}'
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"Geo cache hit for {ip_address}")
            return cached
        
        # Handle localhost/private IPs
        if cls._is_private_ip(ip_address):
            result = cls._get_default_geo()
            result['is_private'] = True
            return result
        
        # Try each API until one works
        for api_url in cls.GEO_APIS:
            try:
                result = cls._query_geo_api(api_url, ip_address)
                if result and result.get('detected'):
                    # Cache successful result
                    cache.set(cache_key, result, GEO_CACHE_TTL)
                    return result
            except Exception as e:
                logger.warning(f"Geo API failed ({api_url}): {e}")
                continue
        
        # All APIs failed, return default
        logger.warning(f"All geo APIs failed for {ip_address}")
        return cls._get_default_geo()
    
    @classmethod
    def _query_geo_api(cls, api_template: str, ip_address: str) -> Optional[Dict[str, Any]]:
        """Query a single geo API."""
        url = api_template.format(ip=ip_address)
        
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Normalize response based on API
        if 'ipapi.co' in api_template:
            return {
                'country_code': data.get('country_code', ''),
                'country_name': data.get('country_name', ''),
                'city': data.get('city', ''),
                'region': data.get('region', ''),
                'detected': bool(data.get('country_code')),
                'source': 'ipapi.co',
            }
        elif 'ip-api.com' in api_template:
            return {
                'country_code': data.get('countryCode', ''),
                'country_name': data.get('country', ''),
                'city': data.get('city', ''),
                'region': data.get('regionName', ''),
                'detected': data.get('status') == 'success',
                'source': 'ip-api.com',
            }
        elif 'ipwho.is' in api_template:
            return {
                'country_code': data.get('country_code', ''),
                'country_name': data.get('country', ''),
                'city': data.get('city', ''),
                'region': data.get('region', ''),
                'detected': data.get('success', False),
                'source': 'ipwho.is',
            }
        
        return None
    
    @classmethod
    def _is_private_ip(cls, ip_address: str) -> bool:
        """Check if IP is private/localhost."""
        private_prefixes = [
            '127.', '10.', '172.16.', '172.17.', '172.18.', '172.19.',
            '172.20.', '172.21.', '172.22.', '172.23.', '172.24.', '172.25.',
            '172.26.', '172.27.', '172.28.', '172.29.', '172.30.', '172.31.',
            '192.168.', '::1', 'localhost',
        ]
        return any(ip_address.startswith(p) for p in private_prefixes)
    
    @classmethod
    def _get_default_geo(cls) -> Dict[str, Any]:
        """Return default geo info when detection fails."""
        # Use deployment region setting if available
        default_region = getattr(settings, 'GPUBROKER_DEFAULT_REGION', 'US')
        
        return {
            'country_code': default_region,
            'country_name': 'Unknown',
            'city': '',
            'region': '',
            'detected': False,
            'source': 'default',
        }
    
    @classmethod
    def get_validation_requirements(cls, country_code: str) -> Dict[str, Any]:
        """
        Get validation requirements for a country.
        
        Returns:
            {
                'requires_tax_id': True/False,
                'tax_id_name': 'RUC/Cédula' or None,
                'tax_id_formats': ['ruc', 'cedula'] or [],
                'language': 'es' or 'en',
                'country_code': 'EC',
            }
        """
        requirements = COUNTRY_VALIDATIONS.get(
            country_code.upper(),
            DEFAULT_VALIDATION.copy()
        )
        requirements['country_code'] = country_code.upper()
        return requirements
    
    @classmethod
    def get_checkout_config(cls, ip_address: str) -> Dict[str, Any]:
        """
        Get complete checkout configuration based on user's location.
        
        Returns config for frontend to show/hide country-specific fields.
        """
        geo = cls.get_country_from_ip(ip_address)
        country_code = geo.get('country_code', 'US')
        requirements = cls.get_validation_requirements(country_code)
        
        return {
            'geo': geo,
            'validation': requirements,
            'show_tax_id': requirements['requires_tax_id'],
            'tax_id_label': requirements.get('tax_id_name', ''),
            'language': requirements.get('language', 'en'),
        }


# Singleton instance
geo_service = GeoService()
