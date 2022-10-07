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

![capture](https://github.com/TretornESP/njinx/raw/main/doc/capture1.png)
![exec](https://github.com/TretornESP/njinx/raw/main/doc/capture2.png)
![result1](https://github.com/TretornESP/njinx/raw/main/doc/capture3.png)
![result2](https://github.com/TretornESP/njinx/raw/main/doc/capture4.png)

## Disclaimer

DONT USE PROVIDED CERTIFICATES! THEY ARE PRESENT ONLY FOR TESTING PURPOSES!