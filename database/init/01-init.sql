-- ⚠️ WARNING: REAL IMPLEMENTATION ONLY ⚠️
-- We do NOT mock, bypass, or invent data.
-- We use ONLY real servers, real APIs, and real data.
-- This codebase follows principles of truth, simplicity, and elegance.

-- GPUBROKER Database Schema
-- PostgreSQL initialization script

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ========================================
-- USERS & AUTHENTICATION
-- ========================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    organization VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT users_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

CREATE TABLE user_sessions (
    jti UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    revoked_at TIMESTAMP WITH TIME ZONE,
    user_agent TEXT,
    ip_address INET
);

CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    scopes TEXT[] DEFAULT ARRAY[]::TEXT[],
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    revoked_at TIMESTAMP WITH TIME ZONE
);

-- ========================================
-- PROVIDERS & MARKETPLACE
-- ========================================

CREATE TABLE providers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    website_url VARCHAR(500),
    api_base_url VARCHAR(500) NOT NULL,
    documentation_url VARCHAR(500),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'maintenance', 'deprecated')),
    supported_regions TEXT[] DEFAULT ARRAY[]::TEXT[],
    compliance_tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    reliability_score DECIMAL(3,2) DEFAULT 0.5,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE gpu_offers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_id UUID NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
    external_id VARCHAR(255) NOT NULL, -- Provider's internal ID
    gpu_type VARCHAR(100) NOT NULL,
    gpu_memory_gb INTEGER NOT NULL,
    cpu_cores INTEGER NOT NULL,
    ram_gb INTEGER NOT NULL,
    storage_gb INTEGER NOT NULL,
    storage_type VARCHAR(20) DEFAULT 'SSD', -- SSD, NVMe, HDD
    price_per_hour DECIMAL(8,4) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    region VARCHAR(50) NOT NULL,
    availability_zone VARCHAR(100),
    availability_status VARCHAR(20) DEFAULT 'available' CHECK (availability_status IN ('available', 'limited', 'unavailable')),
    min_rental_time INTEGER DEFAULT 1, -- minutes
    max_rental_time INTEGER, -- minutes, null = unlimited
    spot_pricing BOOLEAN DEFAULT FALSE,
    preemptible BOOLEAN DEFAULT FALSE,
    sla_uptime DECIMAL(5,2), -- percentage
    network_speed_gbps DECIMAL(6,2),
    compliance_tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(provider_id, external_id)
);

-- ========================================
-- KPI & ANALYTICS TABLES
-- ========================================

CREATE TABLE kpi_calculations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    offer_id UUID NOT NULL REFERENCES gpu_offers(id) ON DELETE CASCADE,
    calculation_type VARCHAR(50) NOT NULL, -- 'cost_per_token', 'cost_per_gflop', 'efficiency_score'
    value DECIMAL(12,6) NOT NULL,
    metadata JSONB DEFAULT '{}',
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(offer_id, calculation_type, calculated_at::DATE)
);

CREATE TABLE provider_health_checks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_id UUID NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL CHECK (status IN ('healthy', 'degraded', 'down', 'error')),
    response_time_ms INTEGER NOT NULL,
    error_message TEXT,
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE price_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    offer_id UUID NOT NULL REFERENCES gpu_offers(id) ON DELETE CASCADE,
    price_per_hour DECIMAL(8,4) NOT NULL,
    availability_status VARCHAR(20) NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ========================================
-- USER PREFERENCES & SETTINGS
-- ========================================

CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    preference_key VARCHAR(100) NOT NULL,
    preference_value JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, preference_key)
);

CREATE TABLE saved_searches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    search_filters JSONB NOT NULL,
    is_alert BOOLEAN DEFAULT FALSE,
    alert_threshold DECIMAL(8,4), -- price threshold for alerts
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ========================================
-- AUDIT & COMPLIANCE
-- ========================================

CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(50) NOT NULL,
    user_id UUID REFERENCES users(id),
    resource_type VARCHAR(50),
    resource_id UUID,
    event_data JSONB NOT NULL DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Hash chain for immutability
    previous_hash VARCHAR(64),
    current_hash VARCHAR(64) GENERATED ALWAYS AS (
        encode(digest(
            COALESCE(previous_hash, '') || 
            id::TEXT || 
            event_type || 
            COALESCE(user_id::TEXT, '') ||
            event_data::TEXT ||
            created_at::TEXT, 
            'sha256'
        ), 'hex')
    ) STORED
);

-- ========================================
-- INDEXES FOR PERFORMANCE
-- ========================================

-- Users
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_expires ON user_sessions(expires_at);
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);

-- Providers & Offers
CREATE INDEX idx_providers_status ON providers(status);
CREATE INDEX idx_gpu_offers_provider ON gpu_offers(provider_id);
CREATE INDEX idx_gpu_offers_gpu_type ON gpu_offers(gpu_type);
CREATE INDEX idx_gpu_offers_region ON gpu_offers(region);
CREATE INDEX idx_gpu_offers_price ON gpu_offers(price_per_hour);
CREATE INDEX idx_gpu_offers_availability ON gpu_offers(availability_status);
CREATE INDEX idx_gpu_offers_updated ON gpu_offers(updated_at);
CREATE INDEX idx_gpu_offers_composite ON gpu_offers(gpu_type, region, availability_status, price_per_hour);

-- KPIs & Analytics
CREATE INDEX idx_kpi_calculations_offer ON kpi_calculations(offer_id);
CREATE INDEX idx_kpi_calculations_type ON kpi_calculations(calculation_type);
CREATE INDEX idx_kpi_calculations_date ON kpi_calculations(calculated_at);
CREATE INDEX idx_provider_health_provider ON provider_health_checks(provider_id);
CREATE INDEX idx_provider_health_time ON provider_health_checks(checked_at);
CREATE INDEX idx_price_history_offer ON price_history(offer_id);
CREATE INDEX idx_price_history_time ON price_history(recorded_at);

-- User Data
CREATE INDEX idx_user_preferences_user ON user_preferences(user_id);
CREATE INDEX idx_saved_searches_user ON saved_searches(user_id);

-- Audit
CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_event_type ON audit_log(event_type);
CREATE INDEX idx_audit_log_created ON audit_log(created_at);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_type, resource_id);

-- ========================================
-- SEED DATA
-- ========================================

-- Insert initial providers
INSERT INTO providers (name, display_name, api_base_url, supported_regions, compliance_tags) VALUES
('runpod', 'RunPod', 'https://api.runpod.io', ARRAY['us-east', 'us-west', 'eu-west'], ARRAY['us-east', 'eu-west']),
('vastai', 'Vast.ai', 'https://console.vast.ai/api/v0', ARRAY['us-central', 'us-east', 'us-west', 'eu-west', 'ap-southeast'], ARRAY['us-central', 'us-east', 'us-west', 'eu-west']),
('coreweave', 'CoreWeave', 'https://api.coreweave.com', ARRAY['us-east', 'us-west'], ARRAY['us-east', 'us-west', 'soc2']),
('lambdalabs', 'Lambda Labs', 'https://cloud.lambdalabs.com/api/v1', ARRAY['us-east', 'us-west'], ARRAY['us-east', 'us-west']),
('paperspace', 'Paperspace', 'https://api.paperspace.io', ARRAY['us-east', 'us-west', 'eu-west'], ARRAY['us-east', 'us-west', 'eu-west', 'soc2']),
('huggingface', 'HuggingFace', 'https://api-inference.huggingface.co', ARRAY['us-east', 'eu-west'], ARRAY['us-east', 'eu-west', 'gdpr']);

-- ========================================
-- FUNCTIONS & TRIGGERS
-- ========================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for auto-updating timestamps
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_providers_updated_at BEFORE UPDATE ON providers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_gpu_offers_updated_at BEFORE UPDATE ON gpu_offers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_saved_searches_updated_at BEFORE UPDATE ON saved_searches FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to maintain audit log hash chain
CREATE OR REPLACE FUNCTION maintain_audit_hash_chain()
RETURNS TRIGGER AS $$
DECLARE
    last_hash TEXT;
BEGIN
    -- Get the last hash from the most recent audit entry
    SELECT current_hash INTO last_hash 
    FROM audit_log 
    ORDER BY created_at DESC, id DESC 
    LIMIT 1;
    
    -- Set the previous hash
    NEW.previous_hash = COALESCE(last_hash, '');
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for audit log hash chain
CREATE TRIGGER maintain_audit_hash_chain_trigger 
    BEFORE INSERT ON audit_log 
    FOR EACH ROW EXECUTE FUNCTION maintain_audit_hash_chain();

-- Grant permissions to application user
-- Note: In production, create a specific application user with limited permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO gpubroker;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO gpubroker;