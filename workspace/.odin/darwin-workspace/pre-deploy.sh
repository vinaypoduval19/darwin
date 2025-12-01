#!/usr/bin/env bash
set -e

echo "APP_DIR: ${APP_DIR}"
echo "ENV: ${ENV}"
echo "SERVICE_NAME: ${SERVICE_NAME}"

# Database connection
MYSQL_HOST="${DARWIN_MYSQL_HOST}"
MYSQL_USER="${DARWIN_MYSQL_USERNAME}"
MYSQL_PASS="${DARWIN_MYSQL_PASSWORD}"
MYSQL_DB="${DARWIN_MYSQL_DATABASE}"

# Install MySQL client
echo "Installing MySQL client..."
apt-get update -qq && apt-get install -y -qq default-mysql-client > /dev/null
echo "MySQL client installed"

# Create database
echo "Creating database: ${MYSQL_DB}"
mysql -h "$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASS" -e "CREATE DATABASE IF NOT EXISTS ${MYSQL_DB};"

# Run migrations
echo "Running migrations..."
mysql -h "$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASS" "$MYSQL_DB" <<'SQL'

CREATE TABLE IF NOT EXISTS `projects` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `cloned_from` varchar(255),
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
);

CREATE TABLE IF NOT EXISTS `codespaces` (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` int NOT NULL,
  `name` varchar(255) NOT NULL,
  `sync_location` text,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `cluster_id` varchar(255),
  `jupyter_link` varchar(255),
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `last_synced_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `user_id` varchar(255),
  `sync_job_id` varchar(255),
  PRIMARY KEY (`id`)
);

CREATE TABLE IF NOT EXISTS `last_selected_codespace` (
  `user_id` varchar(255) NOT NULL,
  `codespace_id` int NOT NULL,
  PRIMARY KEY (`user_id`)
);

SQL

echo "Migrations completed successfully"

# Verify tables
echo "Verifying tables in database: ${MYSQL_DB}"
mysql -h "$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASS" "$MYSQL_DB" -e "SHOW TABLES;"

echo "Pre-deploy completed"
