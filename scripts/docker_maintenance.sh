#!/bin/bash
# Docker Maintenance Script for GTD Coach
# This script performs regular maintenance tasks to prevent disk space exhaustion

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
LOG_FILE="/var/log/docker_maintenance.log"
DISK_THRESHOLD=80  # Alert when disk usage exceeds this percentage
DOCKER_PRUNE_AGE="24h"  # Remove images older than this

# Function to log messages
log_message() {
    echo -e "${1}" | tee -a "$LOG_FILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${1}" >> "$LOG_FILE"
}

# Function to check disk space
check_disk_space() {
    DISK_USAGE=$(df / | grep / | awk '{ print $5 }' | sed 's/%//g')
    log_message "${GREEN}Current disk usage: ${DISK_USAGE}%${NC}"
    
    if [ "$DISK_USAGE" -ge "$DISK_THRESHOLD" ]; then
        log_message "${RED}WARNING: Disk usage is above ${DISK_THRESHOLD}%!${NC}"
        return 1
    fi
    return 0
}

# Function to get Docker disk usage
get_docker_usage() {
    log_message "${YELLOW}Docker disk usage:${NC}"
    docker system df
}

# Function to clean Docker logs
clean_docker_logs() {
    log_message "${YELLOW}Cleaning Docker container logs...${NC}"
    
    # Find and truncate large log files (>100MB)
    find /var/lib/docker/containers -name "*-json.log" -size +100M -exec sh -c 'echo "Truncating large log: {}"; truncate -s 0 {}' \;
    
    log_message "${GREEN}Docker logs cleaned${NC}"
}

# Function to prune Docker resources
prune_docker_resources() {
    log_message "${YELLOW}Pruning Docker resources...${NC}"
    
    # Remove stopped containers
    docker container prune -f --filter "until=${DOCKER_PRUNE_AGE}" || true
    
    # Remove unused images
    docker image prune -a -f --filter "until=${DOCKER_PRUNE_AGE}" || true
    
    # Remove unused volumes (be careful with this)
    docker volume prune -f || true
    
    # Remove unused networks
    docker network prune -f || true
    
    # Remove build cache
    docker builder prune -f --filter "until=${DOCKER_PRUNE_AGE}" || true
    
    log_message "${GREEN}Docker resources pruned${NC}"
}

# Function to restart unhealthy containers
restart_unhealthy_containers() {
    log_message "${YELLOW}Checking for unhealthy containers...${NC}"
    
    UNHEALTHY=$(docker ps --filter health=unhealthy -q)
    if [ -n "$UNHEALTHY" ]; then
        log_message "${RED}Found unhealthy containers, restarting...${NC}"
        docker restart $UNHEALTHY
    else
        log_message "${GREEN}All containers are healthy${NC}"
    fi
}

# Function to setup Netdata monitoring (optional)
setup_netdata_monitoring() {
    # Check if Netdata is installed
    if ! command -v netdata &> /dev/null; then
        log_message "${YELLOW}Netdata not installed. Consider installing for better monitoring:${NC}"
        log_message "  docker run -d --name=netdata \\"
        log_message "    -p 19999:19999 \\"
        log_message "    -v /etc/passwd:/host/etc/passwd:ro \\"
        log_message "    -v /etc/group:/host/etc/group:ro \\"
        log_message "    -v /proc:/host/proc:ro \\"
        log_message "    -v /sys:/host/sys:ro \\"
        log_message "    -v /var/run/docker.sock:/var/run/docker.sock:ro \\"
        log_message "    --cap-add SYS_PTRACE \\"
        log_message "    --security-opt apparmor=unconfined \\"
        log_message "    netdata/netdata"
    else
        log_message "${GREEN}Netdata is installed and monitoring${NC}"
    fi
}

# Main execution
main() {
    log_message "${GREEN}========================================${NC}"
    log_message "${GREEN}Starting Docker Maintenance - $(date)${NC}"
    log_message "${GREEN}========================================${NC}"
    
    # Check disk space before cleanup
    log_message "\n${YELLOW}Pre-cleanup disk check:${NC}"
    check_disk_space
    INITIAL_DISK_CRITICAL=$?
    
    # Show Docker usage before cleanup
    get_docker_usage
    
    # Perform cleanup operations
    if [ "$INITIAL_DISK_CRITICAL" -eq 1 ]; then
        log_message "\n${RED}Disk space critical - performing aggressive cleanup${NC}"
        clean_docker_logs
        prune_docker_resources
    else
        log_message "\n${YELLOW}Performing routine maintenance${NC}"
        # Only prune old resources in routine maintenance
        prune_docker_resources
    fi
    
    # Check disk space after cleanup
    log_message "\n${YELLOW}Post-cleanup disk check:${NC}"
    check_disk_space
    
    # Show Docker usage after cleanup
    log_message "\n${YELLOW}Post-cleanup Docker usage:${NC}"
    get_docker_usage
    
    # Check container health
    restart_unhealthy_containers
    
    # Check Netdata setup
    setup_netdata_monitoring
    
    log_message "\n${GREEN}Docker maintenance completed successfully${NC}"
    log_message "${GREEN}========================================${NC}\n"
}

# Run with proper permissions check
if [ "$EUID" -ne 0 ]; then
    log_message "${RED}This script must be run as root or with sudo${NC}"
    exit 1
fi

# Create log file if it doesn't exist
mkdir -p $(dirname "$LOG_FILE")
touch "$LOG_FILE"

# Execute main function
main

# Exit with success
exit 0