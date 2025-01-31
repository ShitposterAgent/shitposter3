# Troubleshooting

## XGetImage() failed
This indicates no active X server. To fix:
1. Install Xvfb:  
   sudo apt-get install xvfb  
2. Run the script with virtual framebuffer:  
   xvfb-run -a python -m shitposter3

