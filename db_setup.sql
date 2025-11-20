
-- Creates the database, user, and grants privileges.
-- This script must be run by a user with root or administrative privileges.

-- 1. Create the application database
CREATE DATABASE IF NOT EXISTS chatroomdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 2. Create the dedicated database user
-- REPLACE 'your_secure_db_password' with the password you choose.
CREATE USER 'chatroom_user'@'localhost' IDENTIFIED BY 'choco';

-- 3. Grant the user full privileges on the new database
GRANT ALL PRIVILEGES ON chatroomdb.* TO 'chatroom_user'@'localhost';

-- 4. Apply changes
FLUSH PRIVILEGES;
