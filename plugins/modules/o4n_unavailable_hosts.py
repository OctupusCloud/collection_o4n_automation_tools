#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

DOCUMENTATION = """
---
module: o4n_unavailable_hosts
author: Ed Scrimaglia
short_description: Test shh connection timeout
version_added: "2.0.0"
description: Ansible module for testing shh connection timeout

options:
    type:
        description: type of inventory
        required: False
        type: str
        values:
            - static
            - dynamic
        default: static
    inventory:
        description: path to Ansible inventory
        required: true
        type: str
        values:
            - name of inventory if static
            - name of plugin if dynamic
    timeout_threshold:
        description: ssh timeout
        required: false
        type: int
        default: 5
    port:
        description: TCP port to use
        required: false
        type: int
        default: 22
    json_output:
        description: Json that contain unavailable hosts
        required: false
        type: str
        default: unavailable_hosts.json

"""

EXAMPLES = """
- name: Get list of unavailable hosts from static inventory
  o4n_unavailable_hosts:
    type: static
    inventory: inventario.ini
    timeout_threshold: {{timeout}}
    port: "{{ ansible_port }}"
    json_output: {{ slow_hosts }}
  register: output

- name: Get list of unavailable hosts from dynamic inventory
  o4n_unavailable_hosts:
    type: dynamic
    inventory: fedele_dynamic_inv.yaml
    timeout_threshold: {{timeout}}
    port: "{{ ansible_port }}"
    json_output: {{ slow_hosts }}
  register: output

"""

RETURN = """
output:
    description: the commands output as a string.
    type: str
    returned: always
    type: dict
    sample:
        output: {
            content: {
                "SW-CORE_1": {
                    "ip": "10.0.0.101",
                    "response_time": null
                },
                "SW-CORE_2": {
                    "ip": "10.0.0.102",
                    "response_time": null
                }
            }
        }
"""

# Python modules
import socket
import time
import re
from ansible.module_utils.basic import AnsibleModule
import json
import os
import yaml

# Desarrollo del módulo
def check_ssh_port(host_ip, port=22, timeout=5):
    try:
        start_time = time.time()
        with socket.create_connection((host_ip, port), timeout=timeout):
            end_time = time.time()
        return end_time - start_time
    except (socket.timeout, socket.error):
        return None

def get_hosts_and_ip(type, inventory_file):
    hosts = {}
    with open(inventory_file, 'r') as file:
        if type.lower() == "static":
                for line in file:
                    match = re.search(r'(\S+)\s+ansible_host=(\S+)', line)
                    if match:
                        host_name = match.group(1)
                        host_ip = match.group(2)
                        hosts[host_name] = host_ip
        else:
            data = yaml.safe_load(file.read())
            for key,value in data["_meta"]["hostvars"].items():
                host_name = key
                host_ip = value["ansible_host"]
                hosts[host_name] = host_ip

    return hosts

def save_to_json(data, output_file):
    with open(output_file, 'w') as file:
        json.dump(data, file, indent=3)

def find_slow_hosts(type, inventory_object, timeout_threshold=5, ssh_port=22):
    slow_hosts = {}
    status = True
    msg = "No hay hosts con problemas de conexión"
    if type.lower() == "static":
        hosts = get_hosts_and_ip(type, inventory_object)
    else:
        delimitador = inventory_object.rsplit("/",1)
        path = ""
        if len(delimitador)>1:
                path = delimitador[0]
        cod_oper = os.system(f"ansible-inventory --list -i {inventory_object} --output={path}/dynamic_inv.json")
        if cod_oper != 0:
            status = False
            msg = "Inventario dinamico no importado from Fedele"
            return status, msg, slow_hosts
        hosts = get_hosts_and_ip(type, f"{path}/dynamic_inv.json")

    for host_name, host_ip in hosts.items():
        response_time = check_ssh_port(host_ip, ssh_port, timeout=timeout_threshold)
        if response_time is None or response_time > timeout_threshold:
            slow_hosts.update({host_name: {'ip': host_ip, 'response_time': response_time}})
            msg = "Lista de hosts con problemas de conexión generada"
    
    return status, msg, slow_hosts

def main():
    module = AnsibleModule(
        argument_spec=dict(
            type=dict(required=False, type='str', choices=["static","dynamic"], default="static"),
            inventory=dict(required=True, type='str'),
            timeout_threshold=dict(required=False, type='int', default=5),
            port=dict(required=False, type='int', default=22),
            json_output=dict(required=False, type='str'),
        )
    )

    type= module.params.get('type')
    inventory = module.params.get('inventory')
    timeout = module.params.get('timeout_threshold')
    port = module.params.get('port')
    json_output = module.params.get('json_output')

    msg = (f"No se encontraron hosts con un tiempo de conexión SSH superior a {timeout} segundos.")
    
    status, msg, slow_hosts = find_slow_hosts(type, inventory, timeout, port)
    print ("status", status)
    if status:
        if not json_output is None:
            save_to_json(slow_hosts, json_output)

    # Módulo execution status
    if status:
        module.exit_json(failed=False, content=slow_hosts, msg=msg)
    else:
        module.exit_json(failed=True, msg=msg)

if __name__ == "__main__":
    main()
