# Setup required before running those tests :
# on the edge node :
# Stop the chef client (if running) to prevent sudoer file being overwritten :
# 	 bluepill chef-client stop 
# Enable tty for the root account:
#    sudo vi /etc/sudoers
#    add the following line to the end of the file:
#    Defaults:root   !requiretty

run_id = 'SprintDemo'
serverNode = "10.148.44.215"
#clientNode = "10.148.44.220"
params = '-R'

clusterNodes = ['10.148.44.215', '10.148.44.215 ', '10.148.44.215  ']