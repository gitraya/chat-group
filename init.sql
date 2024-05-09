-- Create the users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    hash TEXT NOT NULL,
    profile_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create the channels table
CREATE TABLE channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    admin_id INTEGER NOT NULL,
    FOREIGN KEY (admin_id) REFERENCES users(id)
);

-- Create the members table
CREATE TABLE members (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (channel_id) REFERENCES channels(id)
);

-- Create the messages table
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    is_start_date BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (channel_id) REFERENCES channels(id)
);

-- Insert the default user
INSERT INTO users (username, email, name, hash) VALUES ('admin', 'admin@localhost', 'Admin', '$2b$10$1J');

-- Insert the default channel
INSERT INTO channels (name, admin_id, description) VALUES ('General', 1, "The default channel for all users.");
