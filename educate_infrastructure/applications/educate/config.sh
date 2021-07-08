#!/bin/bash
cd ~
# Fresh installations of Ubuntu do not have a locale yet, and this will cause
# the Open edX installer scripts to fail, so we'll  set it now.
# For any input prompts that follow, you can select the default value.
# locale-gen sets the character set for terminal output.
sudo locale-gen en_GB en_GB.UTF-8
# With the locale set, we'll reconfigure the Ubuntu packages
# to use whatever character set you selected.
# dpkg-reconfigure locales
sudo dpkg --configure -a
# Update Ubuntu 16.04
sudo apt-get update
sudo apt-get upgrade -y

sudo apt-get install awscli -y
aws s3 cp s3://3ducate-config/config.yml config.yml
aws s3 cp s3://3ducate-config/my-passwords.yml my-passwords.yml

# Install open edX
wget https://raw.githubusercontent.com/BbrSofiane/edx.scripts/master/edx.platform-install.sh 
chmod +x edx.platform-install.sh
# sudo nohup ./edx.platform-install.sh &

# versions.py - Script to list versions of core elements of open edx
cd /home/ubuntu
wget https://gist.githubusercontent.com/fdns/8032710eceea0a2c63c1b4f0a5da8ec1/raw/29d0bfcc9d0152c9f57629598c02a73061a9c0cc/version.py
chmod +x version.py

git clone https://github.com/BbrSofiane/edx.scripts.git

chown -R ubuntu:ubuntu *
# sudo ./version.py > versions.log