CREATE DATABASE sentiment_analysis;
USE sentiment_analysis;




CREATE TABLE user (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL
);

CREATE TABLE Post (
    id VARCHAR(255) PRIMARY KEY,          -- Post ID (string type, primary key)
    page_id VARCHAR(255) NOT NULL,        -- Page ID related to the post
    message TEXT,                         -- Post message content
    created_time DATETIME,                -- Timestamp of when the post was created
    image_url VARCHAR(512),               -- URL of the post image (if any)
    likes INT DEFAULT 0,                  -- Number of likes on the post
    shares INT DEFAULT 0,                 -- Number of shares of the post
    sentiment VARCHAR(50)                 -- Sentiment of the post (Positive, Negative, Neutral)
);



CREATE TABLE Comment (
    id VARCHAR(255) PRIMARY KEY,          -- Synthetic comment ID
    post_id VARCHAR(255),                 -- Foreign key referencing the post
    message TEXT,                         -- Comment message content
    created_time DATETIME,                -- Timestamp of when the comment was created
    sentiment VARCHAR(50),                -- Sentiment analysis result
    FOREIGN KEY (post_id) REFERENCES Post(id)  -- Foreign key relationship with Post table
);





drop table post;
drop table comment;

SELECT * FROM user;
SELECT * FROM post;
SELECT * FROM comment;


