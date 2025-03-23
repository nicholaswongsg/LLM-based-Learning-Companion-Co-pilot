-- Users Table
CREATE TABLE IF NOT EXISTS users (
   email VARCHAR(100) PRIMARY KEY,
   password_hash VARCHAR(255) NOT NULL,
   role VARCHAR(50) CHECK (role IN ('Student', 'Instructor')) NOT NULL,
   school_id INT,
   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversations Table
CREATE TABLE conversation_history (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    question TEXT NOT NULL,
    response TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Curriculums Table
CREATE TABLE IF NOT EXISTS curriculums (
   curriculum_id SERIAL PRIMARY KEY,
   email VARCHAR(100) REFERENCES users(email),
   subject VARCHAR(100) NOT NULL,
   start_date DATE,
   commitment_level VARCHAR(50) CHECK (commitment_level IN ('Daily', 'Weekly', 'Twice a Week', 'Monthly')),
   duration_per_session INT CHECK (duration_per_session > 0), 
   goal_description TEXT,
   learning_goal TEXT,
   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Curriculum Chapters Table
CREATE TABLE IF NOT EXISTS curriculum_chapters (
    chapter_id SERIAL PRIMARY KEY,
    curriculum_id INT REFERENCES curriculums(curriculum_id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    scheduled_date DATE,
    is_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Quiz Questions Table
CREATE TABLE IF NOT EXISTS quiz_questions (
    question_id SERIAL PRIMARY KEY,
    chapter_id INT REFERENCES curriculum_chapters(chapter_id),
    question_text TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    option_c TEXT NOT NULL,
    option_d TEXT NOT NULL,
    correct_option CHAR(1) CHECK (correct_option IN ('A', 'B', 'C', 'D')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Quiz Results Table
CREATE TABLE IF NOT EXISTS quiz_results (
    result_id SERIAL PRIMARY KEY,
    chapter_id INT REFERENCES curriculum_chapters(chapter_id),
    email VARCHAR(100) REFERENCES users(email),
    score INT CHECK (score >= 0 AND score <= 10),
    reflection_after_quiz TEXT,
    taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Escalated Tickets Table
CREATE TABLE IF NOT EXISTS escalated_tickets (
    ticket_id SERIAL PRIMARY KEY,
    student_email VARCHAR(100) REFERENCES users(email),
    instructor_email VARCHAR(100) REFERENCES users(email),
    escalated_message TEXT NOT NULL,
    ticket_status VARCHAR(20) CHECK (ticket_status IN ('open', 'resolved', 'pending')) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ticket Messages Table
CREATE TABLE IF NOT EXISTS ticket_messages (
    id SERIAL PRIMARY KEY,
    ticket_id INT REFERENCES escalated_tickets(ticket_id),
    role VARCHAR(50) CHECK (role IN ('Student', 'Instructor')) NOT NULL,
    message_content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Feedback Table
CREATE TABLE IF NOT EXISTS feedback (
    feedback_id SERIAL PRIMARY KEY,
    email VARCHAR(100) REFERENCES users(email),
    conversation_id INT REFERENCES conversation_history(id),
    feedback_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table is properly indexed

CREATE INDEX idx_curriculums_email_subject 
ON curriculums (email, LOWER(subject));

CREATE INDEX idx_curriculums_created_at 
ON curriculums (created_at);

CREATE INDEX idx_chapters_curriculum_id_is_completed
ON curriculum_chapters (curriculum_id, is_completed);

CREATE TABLE public.user_streaks (
    email VARCHAR(100) REFERENCES users(email) ON DELETE CASCADE,
    current_streak INT DEFAULT 0 NOT NULL CHECK (current_streak >= 0),
    longest_streak INT DEFAULT 0 NOT NULL CHECK (longest_streak >= 0),
    last_active_date DATE NOT NULL,
    PRIMARY KEY (email)
);

CREATE OR REPLACE FUNCTION update_streak() 
RETURNS TRIGGER AS $$
DECLARE 
    today DATE := CURRENT_DATE;
BEGIN
    -- If it's an INSERT, initialize streaks
    IF TG_OP = 'INSERT' THEN
         NEW.current_streak := 1;
         NEW.longest_streak := 1;
         NEW.last_active_date := today;
         RETURN NEW;
    END IF;

    -- For UPDATE, decide whether to continue the streak
    IF OLD.last_active_date = today - INTERVAL '1 day' THEN
         NEW.current_streak := OLD.current_streak + 1;
    ELSE
         NEW.current_streak := 1;
    END IF;

    -- Update longest streak if needed
    NEW.longest_streak := GREATEST(NEW.current_streak, OLD.longest_streak);
    
    -- Update last active date
    NEW.last_active_date := today;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER streak_trigger
BEFORE INSERT OR UPDATE ON public.user_streaks
FOR EACH ROW
EXECUTE FUNCTION update_streak();
