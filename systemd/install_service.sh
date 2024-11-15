# Copy the service file to the systemd directory for custom services
sudo cp media_manager.service /etc/systemd/system/media_manager.service

# Reload the systemd manager configuration to recognize the new service file
sudo systemctl daemon-reload

# Start the media_manager service immediately
sudo systemctl start media_manager.service

# Enable the service to start automatically at boot
sudo systemctl enable media_manager.service

# Check the current status of the media_manager service to ensure it’s running correctly
sudo systemctl status media_manager.service

# View real-time logs for the media_manager service
journalctl -u media_manager.service -f
