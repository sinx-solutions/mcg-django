#!/bin/bash

# Script to manage the Django application with PM2

# Navigate to the directory containing manage.py
# IMPORTANT: Adjust this path relative to where you run the script from,
# or use an absolute path on your server. Assuming this script is in the 'api' dir:
APP_DIR=$(pwd) # Or specify the absolute path: /path/to/your/cloned/repo/api
VENV_PATH="$APP_DIR/../venv" # Assuming venv is one level up, adjust if needed
PROJECT_NAME="backend" # The Django project name (contains wsgi.py)
APP_NAME="mcg-django-app" # Name for the app in PM2
GUNICORN_WORKERS=3 # Adjust based on your server's cores (2 * cores + 1 is a good start)
GUNICORN_BIND="0.0.0.0:8000" # Internal port Gunicorn listens on

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Check if Gunicorn is installed
if ! command -v gunicorn &> /dev/null
then
    echo "Gunicorn could not be found. Please install it: pip install gunicorn"
    exit 1
fi

# Check if PM2 is installed
if ! command -v pm2 &> /dev/null
then
    echo "PM2 could not be found. Please install it (e.g., npm install pm2 -g)"
    exit 1
fi

cd "$APP_DIR" || exit # Move into the Django project directory

start() {
    echo "Starting $APP_NAME with PM2..."
    pm2 start gunicorn --name "$APP_NAME" -- \
        "$PROJECT_NAME.wsgi:application" \
        --workers "$GUNICORN_WORKERS" \
        --bind "$GUNICORN_BIND"
    pm2 save # Save the current process list
    pm2 startup # Generate command to make PM2 start on boot
}

stop() {
    echo "Stopping $APP_NAME..."
    pm2 stop "$APP_NAME"
    pm2 save
}

restart() {
    echo "Restarting $APP_NAME..."
    pm2 restart "$APP_NAME"
    # pm2 reload $APP_NAME # Use reload for zero-downtime restarts if configured
    pm2 save
}

status() {
    echo "Status for $APP_NAME:"
    pm2 list | grep "$APP_NAME"
    pm2 logs "$APP_NAME" --lines 20 # Show last 20 log lines
}

logs() {
    echo "Tailing logs for $APP_NAME..."
    pm2 logs "$APP_NAME" --lines 100 # Show more lines initially
}

delete() {
    echo "Deleting $APP_NAME from PM2..."
    pm2 delete "$APP_NAME"
    pm2 save
}


# Script execution logic
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    delete)
        delete
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|delete}"
        exit 1
esac

exit 0
