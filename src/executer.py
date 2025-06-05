import json
import pynvml
import subprocess
import socket
import time
import re

from .utils import *

class RemoteExecuter:

    @classmethod
    def pci_list(cls):
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        pci_list = {}
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            pci_info = pynvml.nvmlDeviceGetPciInfo(handle).busIdLegacy
            device_name = pynvml.nvmlDeviceGetName(handle)
            
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            total_memory = memory_info.total / (1024 * 1024)  
            
            pci_list[i] = {
                "pci_id": pci_info,
                "model": device_name,
                "memory": round(total_memory, 2)  
            }
        pynvml.nvmlShutdown()
        
        return pci_list

    @classmethod
    def gpu_memory_utilization(cls):
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        gpu_info = {}
        
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpu_util = utilization.gpu
            
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            total_memory = memory_info.total / (1024 * 1024) 
            used_memory = memory_info.used / (1024 * 1024)  
            memory_percentage = (used_memory / total_memory) * 100 if total_memory > 0 else 0
            
            gpu_info[i] = {
                "gpu_util": gpu_util,  
                "memory_util": round(memory_percentage, 2)
            }
            
        pynvml.nvmlShutdown()
        return gpu_info

    @classmethod
    def create_container(cls, name):
        try:
            # 验证容器名称
            if not re.match(r'^[a-zA-Z0-9][-a-zA-Z0-9_.]*$', name):
                # 将下划线替换为连字符以避免LXC命令行工具的问题
                modified_name = name.replace('_', '-')
                print(f"Container name with underscores detected, using {modified_name} instead")
                name = modified_name
            
            # 第一步：复制容器
            result = subprocess.run(['lxc', 'copy', 'root', name], capture_output=True, text=True, check=True)
            if result.returncode != 0:
                raise Exception(f"Failed to copy container: {result.stderr}")
            
            # 第二步：启动容器
            result = subprocess.run(['lxc', 'start', name], capture_output=True, text=True, check=True)
            if result.returncode != 0:
                raise Exception(f"Failed to start container: {result.stderr}")
            
            # 第三步：找到可用端口
            port = find_available_port()
            
            # 第四步：获取IP地址（确保容器已经完全启动）
            # 添加等待时间确保容器网络就绪
            time.sleep(2)
            get_ipv4 = get_ip_address(name)
            
            # 第五步：设置root密码
            result = subprocess.run(['lxc', 'exec', name, '--', 'sh', '-c', 'echo "root:123456" | chpasswd'], capture_output=True, text=True, check=True)
            if result.returncode != 0:
                raise Exception(f"Failed to set root password: {result.stderr}")
            
            # 第六步：设置ubuntu密码
            result = subprocess.run(['lxc', 'exec', name, '--', 'sh', '-c', 'echo "ubuntu:123456" | chpasswd'], capture_output=True, text=True, check=True)
            if result.returncode != 0:
                raise Exception(f"Failed to set ubuntu password: {result.stderr}")
            
            if get_ipv4['success']:
                subprocess.run([
                    'lxc', 'config', 'device', 'add', name, 'proxy', 'proxy',
                    f'listen=tcp:0.0.0.0:{port}',
                    f'connect=tcp:{get_ipv4["ipv4"]}:22',
                    'bind=host'
                ], check=True)
                return {'success': True, 'port': port, 'ipv4': get_ipv4['ipv4']}
            else:
                return {'success': False, 'port': None, 'ipv4': None}
        except Exception as e:
            # 清理失败的容器创建
            try:
                subprocess.run(['lxc', 'stop', name, '--force'], capture_output=True, text=True)
                subprocess.run(['lxc', 'delete', name], capture_output=True, text=True)
            except:
                pass
            raise Exception(f"Container creation failed: {str(e)}")
        
    @classmethod
    def start_container(cls, name):
        try:
            result = subprocess.run(['lxc', 'start', name], capture_output=True, text=True, check=True)
            if result.returncode != 0:
                raise Exception(f"Failed to start container: {result.stderr}")
            return {'success': True, 'message': 'Container started successfully'}
        except Exception as e:
            return {'success': False, 'message': f"Error starting container: {str(e)}"}
        
    @classmethod
    def stop_container(cls, name):
        try:
            result = subprocess.run(['lxc', 'stop', name], capture_output=True, text=True, check=True)
            if result.returncode != 0:
                raise Exception(f"Failed to stop container: {result.stderr}")
            return {'success': True, 'message': 'Container stopped successfully'}
        except Exception as e:
            return {'success': False, 'message': f"Error stopping container: {str(e)}"}
        
    @classmethod
    def restart_container(cls, name):
        try:
            result = subprocess.run(['lxc', 'restart', name], capture_output=True, text=True, check=True)
            if result.returncode != 0:
                raise Exception(f"Failed to restart container: {result.stderr}")
            return {'success': True, 'message': 'Container restarted successfully'}
        except Exception as e:
            return {'success': False, 'message': f"Error restarting container: {str(e)}"}
            
    @classmethod
    def delete_container(cls, name):
        try:
            result = subprocess.run(['lxc', 'delete', name, '--force'], capture_output=True, text=True, check=True)
            if result.returncode != 0:
                raise Exception(f"Failed to delete container: {result.stderr}")
            return {'success': True, 'message': 'Container deleted successfully'}
        except Exception as e:
            return {'success': False, 'message': f"Error deleting container: {str(e)}"}
            
    @classmethod
    def container_num(cls):
        try:
            result = subprocess.run(['lxc', 'list', '--format', 'csv'], capture_output=True, text=True, check=True)
            container_list = result.stdout.strip().splitlines()
            return len(container_list)
        except subprocess.CalledProcessError as e:
            print(f"Error executing lxd command: {e}")
            return None
    
    @classmethod
    def container_info(cls, name):
        try:
            result = subprocess.run(['lxc', 'list', name, '--format', 'json'], capture_output=True, text=True, check=True)
            return json.loads(result.stdout)[0]
        except subprocess.CalledProcessError as e:
            print(f"Error getting container info: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return None
        
    @classmethod
    def allocate_gpu(cls, name, gpu_list):
        try:
            allocated_gpus = []
            for gpu in gpu_list:
                try:
                    result = subprocess.run(['lxc', 'config', 'device', 'add', name, f'gpu{gpu}', 'gpu', f'id={gpu}'], capture_output=True, text=True, check=True)
                    if result.returncode != 0:
                        raise Exception(f"Failed to allocate GPU {gpu}: {result.stderr}")
                    allocated_gpus.append(gpu)
                except Exception as e:
                    for allocated_gpu in allocated_gpus:
                        try:
                            subprocess.run(['lxc', 'config', 'device', 'remove', name, f'gpu{allocated_gpu}'], capture_output=True, text=True)
                        except:
                            pass
                    raise e  
            
            return {'success': True, 'message': 'GPUs allocated successfully'}
        except Exception as e:
            return {'success': False, 'message': f"Error allocating GPU: {str(e)}"}
        
    @classmethod
    def release_gpu(cls, name, gpu_list):
        try:
            failed_gpus = []
            for gpu in gpu_list:
                try:
                    result = subprocess.run(['lxc', 'config', 'device', 'remove', name, f'gpu{gpu}'], capture_output=True, text=True, check=True)
                    if result.returncode != 0:
                        failed_gpus.append(gpu)
                except Exception:
                    failed_gpus.append(gpu)
            
            if failed_gpus:
                return {'success': False, 'message': f"Failed to release GPUs: {failed_gpus}"}
            return {'success': True, 'message': 'GPUs released successfully'}
        except Exception as e:
            return {'success': False, 'message': f"Error releasing GPU: {str(e)}"}
        
    @classmethod
    def allocated_gpu(cls, name):
        try:
            result = subprocess.run(['lxc', 'config', 'device', 'list', name], capture_output=True, text=True, check=True)
            if result.returncode != 0:
                raise Exception(f"Error: {result.stderr}")

            output = result.stdout
            gpu_devices = []
            for line in output.splitlines():
                if 'gpu' in line:
                    gpu_number = line.strip().replace('gpu', '')
                    gpu_devices.append(int(gpu_number))

            return sorted(gpu_devices)

        except Exception as e:
            print(f"Error: {e}")
            return []
