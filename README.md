# Ansible Collection - o4n_automation_tools

## Octupus Collection

Collection o4n_automation_tools helps developers to develop automation Ansible software.  
By Ed Scrimaglia, Randy Rozo

## Required

Ansible >= 2.10

## Modules

### o4n_unavailable_hosts

The module finds either using a static or dynamic inventory from Fedele SoT, all the hosts having connecion issues. As a resutl, the
module creates a json file to be used by ansible playbooks to avoid unnecessary connection delays.

### o4n_render_config

The module generates device configurations by combining templates with existing elements in each device. It uses TTP to parse device configurations, extracting and matching specific elements, and then applies Jinja2 templates to generate the final configuration. The module supports filtering unwanted elements through ignore keys and can output the resulting configuration to a file, making it ideal for automating consistent configuration deployments across diverse network devices.
