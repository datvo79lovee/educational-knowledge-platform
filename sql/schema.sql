CREATE TABLE sources (
    source_id SERIAL PRIMARY KEY,
    source_name VARCHAR(255) NOT NULL,
    channel_id VARCHAR(100) UNIQUE,
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE videos (
    video_id VARCHAR(50) PRIMARY KEY,
    source_id INT NOT NULL REFERENCES sources(source_id),

    title TEXT NOT NULL,
    description TEXT,

    publish_date DATE,

    duration_seconds INT,

    view_count BIGINT,

    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transcripts (
    transcript_id SERIAL PRIMARY KEY,

    video_id VARCHAR(50) NOT NULL
        REFERENCES videos(video_id),

    language VARCHAR(20),

    raw_text TEXT NOT NULL,

    retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chunks (
    chunk_id SERIAL PRIMARY KEY,

    transcript_id INT NOT NULL
        REFERENCES transcripts(transcript_id),

    chunk_index INT NOT NULL,

    chunk_text TEXT NOT NULL,

    start_second INT,

    end_second INT,

    token_count INT
);