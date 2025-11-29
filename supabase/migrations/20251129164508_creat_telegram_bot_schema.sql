/*
  # Create Telegram Bot Schema for Chemical Engineering Association

  1. New Tables
    - `users`
      - `id` (uuid, primary key)
      - `telegram_id` (bigint, unique) - Telegram user ID
      - `username` (text) - Telegram username
      - `first_name` (text)
      - `last_name` (text)
      - `role` (text) - user role: member, admin, superadmin
      - `student_id` (text) - Student ID for verification
      - `major` (text) - Academic major
      - `year` (integer) - Academic year
      - `is_verified` (boolean) - Verification status
      - `is_active` (boolean) - Active status
      - `joined_at` (timestamptz)
      - `last_activity` (timestamptz)

    - `announcements`
      - `id` (uuid, primary key)
      - `title` (text)
      - `content` (text)
      - `category` (text) - event, news, exam, project, general
      - `priority` (text) - low, medium, high, urgent
      - `created_by` (uuid, foreign key to users)
      - `created_at` (timestamptz)
      - `scheduled_for` (timestamptz) - For scheduled announcements
      - `is_published` (boolean)
      - `views_count` (integer)

    - `events`
      - `id` (uuid, primary key)
      - `title` (text)
      - `description` (text)
      - `event_date` (timestamptz)
      - `location` (text)
      - `capacity` (integer)
      - `registered_count` (integer)
      - `created_by` (uuid, foreign key to users)
      - `created_at` (timestamptz)
      - `is_active` (boolean)

    - `event_registrations`
      - `id` (uuid, primary key)
      - `event_id` (uuid, foreign key to events)
      - `user_id` (uuid, foreign key to users)
      - `registered_at` (timestamptz)
      - `status` (text) - registered, attended, cancelled

    - `resources`
      - `id` (uuid, primary key)
      - `title` (text)
      - `description` (text)
      - `category` (text) - book, paper, video, course, tool
      - `file_url` (text)
      - `file_type` (text)
      - `uploaded_by` (uuid, foreign key to users)
      - `created_at` (timestamptz)
      - `downloads_count` (integer)
      - `tags` (text[])

    - `questions`
      - `id` (uuid, primary key)
      - `user_id` (uuid, foreign key to users)
      - `title` (text)
      - `content` (text)
      - `category` (text) - homework, concept, exam, project
      - `created_at` (timestamptz)
      - `is_answered` (boolean)
      - `views_count` (integer)

    - `answers`
      - `id` (uuid, primary key)
      - `question_id` (uuid, foreign key to questions)
      - `user_id` (uuid, foreign key to users)
      - `content` (text)
      - `created_at` (timestamptz)
      - `is_accepted` (boolean)

    - `bot_settings`
      - `id` (uuid, primary key)
      - `setting_key` (text, unique)
      - `setting_value` (jsonb)
      - `updated_at` (timestamptz)

  2. Security
    - Enable RLS on all tables
    - Add policies for authenticated users
    - Add admin-only policies for sensitive operations
*/

-- Create users table
CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_id bigint UNIQUE NOT NULL,
  username text,
  first_name text,
  last_name text,
  role text DEFAULT 'member' CHECK (role IN ('member', 'admin', 'superadmin')),
  student_id text,
  major text,
  year integer,
  is_verified boolean DEFAULT false,
  is_active boolean DEFAULT true,
  joined_at timestamptz DEFAULT now(),
  last_activity timestamptz DEFAULT now()
);

-- Create announcements table
CREATE TABLE IF NOT EXISTS announcements (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL,
  content text NOT NULL,
  category text DEFAULT 'general' CHECK (category IN ('event', 'news', 'exam', 'project', 'general')),
  priority text DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
  created_by uuid REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz DEFAULT now(),
  scheduled_for timestamptz,
  is_published boolean DEFAULT false,
  views_count integer DEFAULT 0
);

-- Create events table
CREATE TABLE IF NOT EXISTS events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL,
  description text,
  event_date timestamptz NOT NULL,
  location text,
  capacity integer,
  registered_count integer DEFAULT 0,
  created_by uuid REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz DEFAULT now(),
  is_active boolean DEFAULT true
);

-- Create event_registrations table
CREATE TABLE IF NOT EXISTS event_registrations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id uuid REFERENCES events(id) ON DELETE CASCADE,
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  registered_at timestamptz DEFAULT now(),
  status text DEFAULT 'registered' CHECK (status IN ('registered', 'attended', 'cancelled')),
  UNIQUE(event_id, user_id)
);

-- Create resources table
CREATE TABLE IF NOT EXISTS resources (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL,
  description text,
  category text DEFAULT 'book' CHECK (category IN ('book', 'paper', 'video', 'course', 'tool')),
  file_url text,
  file_type text,
  uploaded_by uuid REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz DEFAULT now(),
  downloads_count integer DEFAULT 0,
  tags text[]
);

-- Create questions table
CREATE TABLE IF NOT EXISTS questions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  title text NOT NULL,
  content text NOT NULL,
  category text DEFAULT 'concept' CHECK (category IN ('homework', 'concept', 'exam', 'project')),
  created_at timestamptz DEFAULT now(),
  is_answered boolean DEFAULT false,
  views_count integer DEFAULT 0
);

-- Create answers table
CREATE TABLE IF NOT EXISTS answers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  question_id uuid REFERENCES questions(id) ON DELETE CASCADE,
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  content text NOT NULL,
  created_at timestamptz DEFAULT now(),
  is_accepted boolean DEFAULT false
);

-- Create bot_settings table
CREATE TABLE IF NOT EXISTS bot_settings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  setting_key text UNIQUE NOT NULL,
  setting_value jsonb,
  updated_at timestamptz DEFAULT now()
);

-- Enable Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE announcements ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE event_registrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE resources ENABLE ROW LEVEL SECURITY;
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_settings ENABLE ROW LEVEL SECURITY;

-- RLS Policies for users table
CREATE POLICY "Users can view all active users"
  ON users FOR SELECT
  USING (is_active = true);

CREATE POLICY "Users can update own profile"
  ON users FOR UPDATE
  USING (telegram_id = (current_setting('app.telegram_id', true))::bigint);

-- RLS Policies for announcements
CREATE POLICY "Everyone can view published announcements"
  ON announcements FOR SELECT
  USING (is_published = true);

CREATE POLICY "Admins can manage announcements"
  ON announcements FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM users
      WHERE users.telegram_id = (current_setting('app.telegram_id', true))::bigint
      AND users.role IN ('admin', 'superadmin')
    )
  );

-- RLS Policies for events
CREATE POLICY "Everyone can view active events"
  ON events FOR SELECT
  USING (is_active = true);

CREATE POLICY "Admins can manage events"
  ON events FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM users
      WHERE users.telegram_id = (current_setting('app.telegram_id', true))::bigint
      AND users.role IN ('admin', 'superadmin')
    )
  );

-- RLS Policies for event_registrations
CREATE POLICY "Users can view own registrations"
  ON event_registrations FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM users
      WHERE users.id = event_registrations.user_id
      AND users.telegram_id = (current_setting('app.telegram_id', true))::bigint
    )
  );

CREATE POLICY "Users can register for events"
  ON event_registrations FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM users
      WHERE users.id = user_id
      AND users.telegram_id = (current_setting('app.telegram_id', true))::bigint
    )
  );

-- RLS Policies for resources
CREATE POLICY "Everyone can view resources"
  ON resources FOR SELECT
  USING (true);

CREATE POLICY "Verified users can upload resources"
  ON resources FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM users
      WHERE users.id = uploaded_by
      AND users.telegram_id = (current_setting('app.telegram_id', true))::bigint
      AND users.is_verified = true
    )
  );

-- RLS Policies for questions
CREATE POLICY "Everyone can view questions"
  ON questions FOR SELECT
  USING (true);

CREATE POLICY "Users can create questions"
  ON questions FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM users
      WHERE users.id = user_id
      AND users.telegram_id = (current_setting('app.telegram_id', true))::bigint
    )
  );

CREATE POLICY "Users can update own questions"
  ON questions FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM users
      WHERE users.id = questions.user_id
      AND users.telegram_id = (current_setting('app.telegram_id', true))::bigint
    )
  );

-- RLS Policies for answers
CREATE POLICY "Everyone can view answers"
  ON answers FOR SELECT
  USING (true);

CREATE POLICY "Users can create answers"
  ON answers FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM users
      WHERE users.id = user_id
      AND users.telegram_id = (current_setting('app.telegram_id', true))::bigint
    )
  );

-- RLS Policies for bot_settings
CREATE POLICY "Admins can manage settings"
  ON bot_settings FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM users
      WHERE users.telegram_id = (current_setting('app.telegram_id', true))::bigint
      AND users.role = 'superadmin'
    )
  );

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_announcements_published ON announcements(is_published, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_date ON events(event_date);
CREATE INDEX IF NOT EXISTS idx_questions_category ON questions(category, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_resources_category ON resources(category, created_at DESC);
