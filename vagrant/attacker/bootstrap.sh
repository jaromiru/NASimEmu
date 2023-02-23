#!/bin/bash

echo "Bootstrapping attacker"
sudo systemctl stop NetworkManager.service

su vagrant -c 'msfrpcd -P msfpassword'

sudo apt update
sudo apt install -y lynx # lynx is a useful tool for debugging http servers
echo "accept_all_cookies=on" >> /home/vagrant/.lynxrc

#sudo apt remove -y libwacom2
#sudo apt install -y libwacom9
#sudo apt upgrade -y metasploit-framework

# partial search in console...
echo 'autoload -U up-line-or-beginning-search' >> ~/.zshrc
echo 'autoload -U down-line-or-beginning-search' >> ~/.zshrc
echo 'zle -N up-line-or-beginning-search' >> ~/.zshrc
echo 'zle -N down-line-or-beginning-search' >> ~/.zshrc
echo 'bindkey "$key[Up]" up-line-or-beginning-search' >> ~/.zshrc
echo 'bindkey "$key[Down]" down-line-or-beginning-search' >> ~/.zshrc