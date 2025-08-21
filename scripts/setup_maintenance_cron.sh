#!/bin/bash
# Setup cron job for Docker maintenance

SCRIPT_PATH="/Users/adeel/gtd-coach/scripts/docker_maintenance.sh"
CRON_SCHEDULE="0 2 * * *"  # Run daily at 2 AM

echo "Setting up Docker maintenance cron job..."

# Check if script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "Error: Maintenance script not found at $SCRIPT_PATH"
    exit 1
fi

# Add to crontab (checking if it already exists)
(crontab -l 2>/dev/null | grep -v "$SCRIPT_PATH"; echo "$CRON_SCHEDULE $SCRIPT_PATH") | crontab -

echo "Cron job added successfully!"
echo "Docker maintenance will run daily at 2 AM"
echo ""
echo "To view current cron jobs: crontab -l"
echo "To remove the cron job: crontab -e (then delete the line)"
echo ""
echo "You can also run the maintenance manually:"
echo "  sudo $SCRIPT_PATH"