#!/usr/bin/python3
import sys
from tkinter.font import names
import docker
import yaml
from pathlib import Path
from enum import Enum
import subprocess

class NginxGenerator:
    TEMPLATE = \
    """
    server {
        listen 443 ssl;

        ssl_certificate /etc/nginx/certi.crt;
        ssl_certificate_key /etc/nginx/certi.key;
        ssl_ecdh_curve secp384r1;
        ssl_protocols TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384;
        ssl_prefer_server_ciphers on;
        ssl_session_cache shared:SSL:10m;
        
        server_name %name%;

        location / {
            proxy_pass http://host.docker.internal:%port%;
        }
    }

    """

    def __init__(self):
        raise NotImplemented("This should never be instantiated")
    
    @staticmethod
    def write(name, port):
        data = NginxGenerator.TEMPLATE.replace("%name%", name).replace("%port%", port)
        with open("./nginx/generated/"+name+".conf", "w") as f:
            f.write(data)
        
    @staticmethod
    def clean(name):
        if Path("./nginx/generated/"+name+".conf").exists():
            Path("./nginx/generated/"+name+".conf").unlink()

class Remap:
    def __init__(self, target, source_port, destination_port, name, id):
        self.target = target
        self.source_port = source_port
        self.destination_port = destination_port
        self.name = name
        self.id = id
    def __str__(self):
        return f"[{self.id}] {self.target}|{self.name} -> {self.destination_port}:{self.source_port}"

class Port:
    def __init__(self, raw, name, source, destination):
        self.raw = raw
        self.name = name
        self.source = source
        self.destination = destination

class Service:
    def __init__(self, name, ports):
        self.name = name
        self.ports = []
        for port in ports:
            self.ports.append(Port(port, port.split(":")[0], port.split(":")[1], port.split(":")[0]))

class ComposeFile:
    SUPPORTED_VERSIONS = ["3.8"]

    def __init__(self, file, services):
        self.file = file
        self.services = services
    
    def save(self, ephemeral=False):
        with open(self.file, "r+") as file:
            data = yaml.safe_load(file)
            for service in self.services:
                data["services"][service.name]["ports"].clear()
                for port in service.ports:
                    data["services"][service.name]["ports"].append(f"{port.destination}:{port.source}")
            if ephemeral:
                raise NotImplemented("ephemeral not implemented")
            else:
                file.seek(0)
                file.truncate()
                yaml.safe_dump(data, file)

    @staticmethod
    def from_file(path):
        # Read the file
        with open(path, "r") as file:
            raw = yaml.safe_load(file)
            if raw.get("version") not in ComposeFile.SUPPORTED_VERSIONS:
                raise Exception(f"Unsupported version {raw.get('version')}")
            
            try:
                services = []
                for name, service in raw["services"].items():
                    services.append(Service(name, service["ports"]))

                return ComposeFile(path, services)
            except KeyError as e:
                raise Exception("Invalid docker compose file: " + str(e))
    
def load_docker_status():
    container = docker.from_env()
    return container.containers.list()

def start(file, aggresive, ephemeral, suffix=""):
    print("Starting njinx...")
    print("Loading docker services...")

    seen_ports = {}
    for container in load_docker_status():
        for container_port, host_ports in container.ports.items():
            if host_ports is None:
                continue
            for entry in host_ports:
                if entry["HostIp"] != "0.0.0.0":
                    continue
                services = seen_ports.get(entry["HostPort"], [])
                services.append({"name":container.name, "port":container_port})
                seen_ports[entry["HostPort"]] = services

    print("Loading docker compose file...")
    compose_file = ComposeFile.from_file(file)
    print("Checking for remap candidates...")
    for service in compose_file.services:
        for port in service.ports:
            original_port = Port(port.raw, port.name, port.source, port.destination)
            if port.destination.isnumeric():
                if not aggresive:
                    print("Skipping port, the service may not work!")
                    continue
                print("Performing aggresive remap...")
                while (port.destination in seen_ports.keys()):
                    port.destination = str(int(port.destination) + 1)
                    if int(port.destination) > 65535:
                        raise Exception("No more ports available!")
            else:
                port.destination = "1025"
                while (port.destination in seen_ports.keys()):
                    port.destination = str(int(port.destination) + 1)
                    if int(port.destination) > 65535:
                        raise Exception("No more ports available!")
            print(f"Remapping {service.name}:{port.source} to {port.destination}")
            seen_ports[port.destination] = original_port.source

    compose_file.save(ephemeral)

    NginxGenerator.clean(port.name)
    for service in compose_file.services:
        for port in service.ports:
            if port.name.isnumeric():
                port.name = input(f"Enter a name for {service.name}:{port.source} ({original_port.destination}): ")
            NginxGenerator.write(port.name, port.destination)

    print("Restarting patched service...")
    subprocess.run(["docker-compose", "-f", file, "down"])
    subprocess.run(["docker-compose", "-f", file, "up", "-d"])
    print("Restarting njinx service...")
    subprocess.run(["docker-compose", "-f", "./docker-compose.yml", "down"])
    subprocess.run(["docker-compose", "-f", "./docker-compose.yml", "up", "-d"])
    print("Njinx is up and running, available services: ")
    for service in compose_file.services:
        for port in service.ports:
            print(f"http://{port.name}:{port.source}/")
    return 0

def stop():
    print("Stopping njinx...")
    return 0

def usage():
    print("Usage: njinx.py <--start | --stop> [--aggresive] [--ephemeral] [--suffix=<>] <target>")
    print("--start tries to fix and start the instance")
    print("--stop stops the instance")
    print("--aggresive edits all ports, even if they are not marked as editable")
    print("--suffix adds a suffix to the virtual host")
    print("--ephemeral uses a copy of the file, instead of modifying the original")
    print("the target is docker compose file")
    print("A few examples:")
    print("njinx.py --start /service/docker-compose.yml")
    print("njinx.py --start --aggresive --suffix=dev --ephemeral /nativeservice/docker-compose.yml")
    print("njinx.py --stop /service/docker-compose.yml")
    return 1

def main():
    if len(sys.argv) >= 3:
        file = Path(sys.argv[-1]).absolute()
        if file.exists():
            if sys.argv[1] == "--start":
                aggresive = "--aggressive" in sys.argv
                ephemeral = "--ephemeral" in sys.argv
                suffix = None
                for arg in sys.argv:
                    if arg.startswith("--suffix="):
                        suffix = arg.split("=")[1]
                        break
                
                return start(file, aggresive, ephemeral, suffix)
            elif sys.argv[1] == "--stop":
                return stop(file)
        else:
            print("File not found!")
    return usage()
    

if __name__ == '__main__':
    main()