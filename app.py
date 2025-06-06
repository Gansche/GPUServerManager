import json

from werkzeug.wrappers import response
from flask import Flask, request, jsonify
from flask_cors import CORS

from src.executer import RemoteExecuter, get_ip_address

app = Flask(__name__)
app.config.from_object(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

## gpu

@app.route('/gpu/pci_list', methods=['GET'])
def gpu_pci_list():
    pci_list = RemoteExecuter.pci_list()
    return jsonify(pci_list)    

@app.route('/gpu/data', methods=['GET'])
def gpu_memory_utilization():
    gpu_info = RemoteExecuter.gpu_memory_utilization()
    return jsonify(gpu_info)

## container

@app.route('/container/create', methods=['POST'])
def container_create():
    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({"success": False, "message": "Missing 'name'"}), 400
    result = RemoteExecuter.create_container(name)
    if result['success']:
        return jsonify({"success": True, "port": result['port'], "ipv4": result['ipv4']})
    else:
        return jsonify({"success": False, "message": "Failed to create container"}), 500

@app.route('/container/start', methods=['POST'])
def container_start():
    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({"success": False, "message": "Missing 'name'"}), 400
    RemoteExecuter.start_container(name)
    return jsonify({"success": True})   

@app.route('/container/stop', methods=['POST'])
def container_stop():
    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({"success": False, "message": "Missing 'name'"}), 400
    RemoteExecuter.stop_container(name)
    return jsonify({"success": True})

@app.route('/container/restart', methods=['POST'])
def container_restart():
    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({"success": False, "message": "Missing 'name'"}), 400
    RemoteExecuter.restart_container(name)
    return jsonify({"success": True})

@app.route('/container/delete', methods=['POST'])
def container_delete():
    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({"success": False, "message": "Missing 'name'"}), 400
    RemoteExecuter.delete_container(name)
    return jsonify({"success": True})

@app.route('/container/num', methods=['GET'])
def container_num():
    num = RemoteExecuter.container_num()
    return jsonify({"num": num})    

@app.route('/container/info', methods=['GET'])
def container_info():
    name = request.args.get('name')
    info = RemoteExecuter.container_info(name)
    return jsonify(info)

@app.route('/container/allocate', methods=['POST'])
def container_allocate():
    data = request.get_json()
    name = data.get('name')
    gpu_list = data.get('gpu_list')
    pci_list = data.get('pci_list')
    if not name or not gpu_list or not pci_list:
        return jsonify({"success": False, "message": "Missing 'name' or 'gpu_list' or 'pci_list'"}), 400
    RemoteExecuter.allocate_gpu(name, gpu_list, pci_list) 
    return jsonify({"success": True})

@app.route('/container/release', methods=['POST'])
def container_release():
    data = request.get_json()
    name = data.get('name')
    gpu_list = data.get('gpu_list')
    if not name or not gpu_list:
        return jsonify({"success": False, "message": "Missing 'name' or 'gpu_list'"}), 400
    RemoteExecuter.release_gpu(name, gpu_list)
    return jsonify({"success": True})
    
@app.route('/container/allocated', methods=['GET'])
def container_allocated():
    name = request.args.get('name')
    allocated = RemoteExecuter.allocated_gpu(name)
    return jsonify({"allocated": allocated})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8026)
    
