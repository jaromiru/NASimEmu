echo 'Creating loot at /home/kylo_ren/loot'
su kylo_ren -c 'echo LOOT=`date +%M-%S-%N | md5sum | cut -f 1 -d " "` > ~/loot; chmod 600 ~/loot'