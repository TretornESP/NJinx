# NJINX

Automatically add a server blocks wrapper to your docker compose services

## How to use

You can check the dockerfile provided under ```demo/service```
You may see the ports category is sightly different as a name is 
on the left side. This is the name that will be exposed to the host.

If you want tu transform regular docker compose file, specify the ```--aggressive```
flag.

Simply run
    
    python3 ./njinx.py --start <path to docker-compose.yml>

## Disclaimer

DONT USE PROVIDED CERTIFICATES! THEY ARE PRESENT ONLY FOR TESTING PURPOSES!