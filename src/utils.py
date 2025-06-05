import socket
import subprocess
import json
import time

def find_available_port(start_port=8000, end_port=9000):
    for port in range(start_port, end_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(('127.0.0.1', port))
            if result != 0:
                return port
    return None

def get_ip_address(name: str):
    """
    获取LXD容器的IPv4地址，如果IP地址未立即分配则在2秒内重试
    """
    max_retry_time = 5 
    retry_interval = 0.5 
    start_time = time.time()
    
    while time.time() - start_time < max_retry_time:
        try:
            result = subprocess.run(['lxc', 'list', name, '--format=json'], capture_output=True, text=True, check=True)
            
            if not result.stdout.strip():
                time.sleep(retry_interval)
                continue
                
            containers = json.loads(result.stdout)
            
            if not containers:
                time.sleep(retry_interval)
                continue
                
            container = containers[0]  
            
            if 'state' in container and 'network' in container['state']:
                for interface_name, interface_data in container['state']['network'].items():
                    if interface_name == 'lo':
                        continue
                        
                    for address in interface_data.get('addresses', []):
                        if address.get('family') == 'inet' and address.get('address'):
                            return {"success": True, "ipv4": address.get('address')}
            
            time.sleep(retry_interval)
            
        except subprocess.CalledProcessError as e:
            time.sleep(retry_interval)
        except json.JSONDecodeError as e:
            time.sleep(retry_interval)
        except Exception as e:
            time.sleep(retry_interval)
    
    return {"success": False, "message": "Failed to obtain IP address for container '{name}' within {max_retry_time} seconds"}
