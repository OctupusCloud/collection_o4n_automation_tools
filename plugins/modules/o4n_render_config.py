#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r'''
---
module: o4n_render_config
short_description: Generates configurations by combining templates with existing device elements, allowing specific exclusions
version_added: "1.0.0"
description:
  - Parses device configurations using TTP templates
  - Matches and extracts existing elements from device configurations
  - Applies template patterns to matched elements
  - Supports filtering specific elements via ignore keys
  - Generates device-specific configurations based on discovered elements
  - Can write resulting configuration to a file

options:
  config:
    description:
      - Raw device configuration as inline text
      - Mutually exclusive with I(config_src)
    type: str
    required: false
  config_src:
    description:
      - Path to file containing device configuration
      - Mutually exclusive with I(config)
    type: str
    required: false
  template:
    description:
      - TTP parsing template as inline text
      - Mutually exclusive with I(template_src)
    type: str
    required: false
  template_src:
    description:
      - Path to file containing TTP parsing template
      - Mutually exclusive with I(template)
    type: str
    required: false
  dest_path:
    description:
      - Destination path for generated configuration
      - Returns result without writing if not specified
    type: str
    required: false
  keys_ignore:
    description:
      - Key(s) to ignore in parsed data
      - Can be single string or list of strings
      - Uses startswith comparison for values
    type: raw
    required: false
    default: ""

author:
  - Randy Rozo (@randyrozo)

requirements:
  - ttp
  - jinja2

notes:
  - In check mode (--check), no files will be written
  - When ignoring keys, comparison uses startswith logic
'''

EXAMPLES = r'''
# Basic example with inline content
- name: Generate interface configuration
  o4n_render_config:
    config: |
      Building configuration...

      Current configuration with default configurations exposed : 50303 bytes
      !
      ! Last configuration change at 09:49:53 UTC Mon Feb 3 2025
      !
      version 15.2
      !
      hostname G3_ACCESO
      !
      vlan 15
       name V_Datos_EDF
      !
      vlan 20
       name V_Voz
      !
      vlan 30
       name V_Servicios
      !
      vlan 51
       name V_Remediacion_ED
      !
      vlan 62
       name DATOS_SES_TCS
      !
      interface GigabitEthernet0/0
       switchport
       switchport access vlan 1
      !
      interface GigabitEthernet0/1
       description IMPRESORA
       switchport
       switchport access vlan 15
       switchport mode access
      !
      interface GigabitEthernet0/2
       description USR-TCS-USUARIO-VLAN15
       switchport
       switchport access vlan 15
       switchport mode access
      !
      interface GigabitEthernet0/3
       switchport
       switchport access vlan 15
       switchport mode access
      !
      interface GigabitEthernet1/0
       switchport
       switchport access vlan 1
      !
      interface GigabitEthernet1/1
       switchport
       switchport access vlan 1
      !
      interface GigabitEthernet1/2
       switchport
       switchport access vlan 1
      !
      interface GigabitEthernet1/3
       switchport
       switchport access vlan 1
      !
      interface GigabitEthernet2/0
       switchport
       switchport access vlan 1
      !
      interface Vlan1
       ip address 10.2.7.11 255.255.255.0
       ip redirects
       ip unreachables
       ip proxy-arp
      interface Vlan10
       ip address 10.1.9.136 255.255.255.0
       ip redirects
       ip unreachables
       ip proxy-arp
      !
      interface Vlan15
       ip address 10.1.7.252 255.255.254.0
       ip redirects
       ip unreachables
       ip proxy-arp
      !
      interface Vlan30
       description V_Servicios
       ip address 10.1.16.11 255.255.255.0
       ip redirects
       ip unreachables
       ip proxy-arp
      interface Vlan51
       ip address 10.1.63.246 255.255.254.0
       ip redirects
       ip unreachables
       ip proxy-arp
      !
      end
    template: |
      interface {{ ifname }}
       no ip proxy-arp
       ip verify unicast source reachable-via rx
    dest_path: "./configuraciones/{{ inventory_hostname }}.cfg"
  register: config_output

# Example using external files
- name: Generate interface configuration
  o4n_render_config:
    config_src: "./files/device_config/{{ inventory_hostname }}.device"
    template_src: "/templates/interface_template"
    keys_ignore: 
      - "GigabitEthernet"
      - "Loopback"
    dest_path: "./configuraciones/{{ inventory_hostname }}.cfg"
'''

RETURN = r'''
rendered_config:
  description: Final rendered configuration
  type: str
  returned: always
  sample: |
    interface Vlan1
     no ip proxy-arp
     ip verify unicast source reachable-via rx
    interface Vlan10
     no ip proxy-arp
     ip verify unicast source reachable-via rx
    interface Vlan15
     no ip proxy-arp
     ip verify unicast source reachable-via rx
    interface Vlan30
     no ip proxy-arp
     ip verify unicast source reachable-via rx
    interface Vlan51
     no ip proxy-arp
     ip verify unicast source reachable-via rx
ignored_instances:
  description: Structured data from TTP parsing
  type: list
  returned: always
  sample: [{"ifname": "GigabitEthernet0/0", "ifname": "GigabitEthernet0/1", "ifname": "GigabitEthernet0/2", "ifname": "GigabitEthernet0/3", "ifname": "GigabitEthernet1/0", "ifname": "GigabitEthernet1/1", "ifname": "GigabitEthernet1/2", "ifname": "GigabitEthernet1/3", "ifname": "GigabitEthernet2/0", "ifname": "GigabitEthernet2/1"}]
render_data:
  description: Structured data from TTP parsing
  type: list
  returned: always
  sample: [{"ifname": "Vlan1", "ifname": "Vlan10", "ifname": "Vlan15", "ifname": "Vlan30", "ifname": "Vlan51"}]
source_used:
  description: Sources used for configuration and template
  type: dict
  returned: always
  contains:
    config_source:
      description: Configuration source (inline or file path)
      type: str
    template_source:
      description: Template source (inline or file path)
      type: str
dest_path:
  description: Path where configuration was written
  type: str
  returned: when dest_path is specified
  sample: "/configurations/final.cfg"
changed:
  description: Indicates if changes were made to the system
  type: bool
  returned: always
'''

from ansible.module_utils.basic import AnsibleModule
from jinja2 import Template
from ttp import ttp
import json
import os


def load_content(param_value, is_path=False):
    """Carga contenido desde diferentes fuentes"""
    try:
        if is_path:
            if not os.path.exists(param_value):
                raise ValueError(f"File not found: {param_value}")
            with open(param_value, 'r') as f:
                return f.read(), f"file:{param_value}"
        return param_value, "inline"
    except Exception as e:
        raise ValueError(f"Error loading content: {str(e)}")


def parse_configuration(data, template):
    """Ejecuta el parser TTP y valida resultados"""
    try:
        parser = ttp(data=data, template=template)
        parser.parse()
        return parser.result(format="raw")
    except Exception as e:
        raise ValueError(f"Error en parseo TTP: {str(e)}")


def render_configuration(parsed_data, context_template, keys_ignore):
    """Genera configuración a partir de datos parseados"""
    template = Template(context_template)
    rendered_parts = []
    ignored_instances = []
    render_data = []

    if not parsed_data:
        return context_template

    for entry in parsed_data:
        if keys_ignore:
            #  Verificar si algún valor contiene el key_ignore
            if any(str(value).startswith(key_ignore) for value in entry.values() for key_ignore in keys_ignore):
                ignored_instances.append(entry)
                # parsed_data.remove(entry)
                continue  # Saltar esta entrada completamente

        # Renderizar la entrada válida
        rendered_parts.append(template.render(**entry))
        render_data.append(entry)


    return "\n".join(rendered_parts), ignored_instances, render_data


def main():
    # Definición de argumentos del módulo
    module_args = dict(
        config=dict(type='str', required=False),
        config_src=dict(type='str', required=False),
        template=dict(type='str', required=False),
        template_src=dict(type='str', required=False),
        dest_path=dict(type='str', required=False),
        keys_ignore=dict(type="raw", choice=[str, list], required=False, default="")
    )
    module = AnsibleModule(
        argument_spec=module_args,
        mutually_exclusive=[('config', 'config_src'), ('template', 'template_src')],
        required_one_of=[('config', 'config_src'), ('template', 'template_src')],
        supports_check_mode=True
    )
 
    result = {
        'changed': False,
        'rendered_config': '',
        'source_used': {
            'config_source': None,
            'template_source': None
        },
        'dest_path': None
    }

    try:
        # Cargar configuración
        if module.params['config']:
            config_content, config_source = module.params['config'], 'inline'
        else:
            config_content, config_source = load_content(module.params['config_src'], is_path=True)
        
        result['source_used']['config_source'] = config_source

        # Cargar template
        if module.params['template']:
            context_template, template_source = module.params['template'], 'inline'
        else:
            context_template, template_source = load_content(module.params['template_src'], is_path=True)

        result['source_used']['template_source'] = template_source

        if module.params['dest_path']:
            result['dest_path'] = module.params['dest_path']


        # Parsear configuración
        parsed_raw = parse_configuration(config_content, context_template)
        
        if not parsed_raw:
            module.fail_json(msg="No se encontraron datos válidos en el parseo", **result)
        
        # Normalizar estructura de datos
        parsed_data = parsed_raw[0][0] if isinstance(parsed_raw[0], list) else parsed_raw
        # result["parsed_data"] = parsed_data  # Para debugging

        # Renderizar configuración
        rendered, ignored_instances, render_data = render_configuration(
            parsed_data,
            context_template,
            module.params['keys_ignore']
        )
        result["rendered_config"] = rendered
        result["ignored_instances"] = ignored_instances
        result["render_data"] = render_data

        if not module.check_mode and module.params['dest_path']:
            dest = module.params['dest_path']

            # Verificar si el archivo existe y comparar contenido
            if os.path.exists(dest):
                with open(dest, 'r') as f:
                    current_content = f.read()
                
                if current_content == rendered:
                    result["changed"] = False
                else:
                    with open(dest, 'w') as f:
                        f.write(rendered)
                    result["changed"] = True
            else:
                # Archivo no existe, crear nuevo
                with open(dest, 'w') as f:
                    f.write(rendered)
                result["changed"] = True


    except Exception as e:
        module.fail_json(msg=str(e), **result)
    
    module.exit_json(**result)

if __name__ == '__main__':
    main()
