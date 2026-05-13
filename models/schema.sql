-- KisanSathi AI — Supabase Database Schema
-- Run this in your Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ========================================
-- USERS TABLE (extends Supabase auth.users)
-- ========================================
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    role TEXT DEFAULT 'farmer' CHECK (role IN ('farmer', 'admin')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- FARMER PROFILES
-- ========================================
CREATE TABLE IF NOT EXISTS public.farmer_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    name TEXT,
    phone TEXT,
    state TEXT,
    district TEXT,
    village TEXT,
    farm_size DECIMAL(10,2), -- in acres
    primary_crops TEXT[],
    soil_type TEXT,
    language TEXT DEFAULT 'hindi' CHECK (language IN ('hindi', 'punjabi', 'english')),
    fcm_token TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- CROP HISTORY
-- ========================================
CREATE TABLE IF NOT EXISTS public.crop_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    crop TEXT NOT NULL,
    season TEXT,
    area DECIMAL(10,2),
    yield_kg DECIMAL(10,2),
    revenue DECIMAL(12,2),
    notes TEXT,
    planted_at DATE,
    harvested_at DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- DISEASE REPORTS
-- ========================================
CREATE TABLE IF NOT EXISTS public.disease_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    disease TEXT,
    severity TEXT CHECK (severity IN ('Low', 'Medium', 'High', 'Critical')),
    confidence SMALLINT CHECK (confidence BETWEEN 0 AND 100),
    treatment TEXT,
    analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- FERTILIZER REPORTS
-- ========================================
CREATE TABLE IF NOT EXISTS public.fertilizer_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    crop TEXT NOT NULL,
    recommendation TEXT,
    quantity TEXT,
    timing TEXT,
    details_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- YIELD PREDICTIONS
-- ========================================
CREATE TABLE IF NOT EXISTS public.yield_predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    crop TEXT NOT NULL,
    predicted_yield DECIMAL(10,2),
    profit_estimate DECIMAL(12,2),
    risk TEXT CHECK (risk IN ('Low', 'Medium', 'High')),
    details_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- WEATHER LOGS
-- ========================================
CREATE TABLE IF NOT EXISTS public.weather_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    location TEXT,
    data_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- NOTIFICATIONS
-- ========================================
CREATE TABLE IF NOT EXISTS public.notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    type TEXT DEFAULT 'general' CHECK (type IN ('weather', 'disease', 'fertilizer', 'irrigation', 'general')),
    read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- CHAT HISTORY
-- ========================================
CREATE TABLE IF NOT EXISTS public.chat_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    language TEXT DEFAULT 'english',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- UPLOADED IMAGES
-- ========================================
CREATE TABLE IF NOT EXISTS public.uploaded_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    cloudinary_url TEXT NOT NULL,
    public_id TEXT,
    type TEXT DEFAULT 'disease' CHECK (type IN ('disease', 'profile', 'farm', 'other')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================
-- INDEXES
-- ========================================
CREATE INDEX IF NOT EXISTS idx_disease_reports_user ON public.disease_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_fertilizer_reports_user ON public.fertilizer_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_yield_predictions_user ON public.yield_predictions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_user ON public.chat_history(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON public.notifications(user_id, read);
CREATE INDEX IF NOT EXISTS idx_weather_logs_user ON public.weather_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_crop_history_user ON public.crop_history(user_id);

-- ========================================
-- ROW LEVEL SECURITY (RLS)
-- ========================================
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.farmer_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.crop_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.disease_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fertilizer_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.yield_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.weather_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.uploaded_images ENABLE ROW LEVEL SECURITY;

-- Users can only see their own data
CREATE POLICY "Users can see own data" ON public.farmer_profiles FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can see own crops" ON public.crop_history FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can see own diseases" ON public.disease_reports FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can see own fertilizer" ON public.fertilizer_reports FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can see own yields" ON public.yield_predictions FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can see own weather" ON public.weather_logs FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can see own notifications" ON public.notifications FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can see own chats" ON public.chat_history FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can see own images" ON public.uploaded_images FOR ALL USING (auth.uid() = user_id);

-- ========================================
-- AUTO-UPDATE TRIGGER
-- ========================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON public.farmer_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at();
