#!/usr/bin/env python
# coding: utf-8
from __future__ import print_function

def run_module(hosts, module_name, args, **complex_args):
    import ansible.inventory
    pattern = "all"
    inventory = ansible.inventory.Inventory(',')
    
    all_group = inventory.get_group("all")
    from ansible.inventory.host import Host
    for h in hosts:
        host = Host(h["host"], h.get("port"))
        for key, value in h["settings"].iteritems():
            host.set_variable(key, value)
    
        all_group.add_host(host)
    
    # в конструкторе кэш посчитался заранее
    inventory.clear_pattern_cache()
    
    # сам Ansible использует отдельный Runner для каждого действия в playbook,
    # так что вот готов отдельный кирпичик для системы развертывания
    import ansible.runner 
    runner = ansible.runner.Runner(
        module_name=module_name,
        module_args=args,
        complex_args=complex_args,
        pattern=pattern,
        inventory=inventory,
        
    )
    results = runner.run()
    
    # :COPY_N_PASTE_REALIZATION: bin/ansible
    if results['dark']:
        assert False, "Couldn't connect to %s" % results['dark']
    total = 0
    for result in results['contacted'].values():
        if 'failed' in result or result.get('rc', 0) != 0:
            assert False, result
        total += 1
    assert total == len(hosts), "The host was not connected to"
    
import docker
import update_ssh_config

def find_container(cont_name, client=None, search_all=False):
    if not client:
        client = docker.Client()
        
    # all=True покажет и не работающие
    containers = client.containers(all=search_all)
    
    cont = None
    for c in containers:
        if update_ssh_config.get_name(c) == cont_name:
            cont = c
            break
    return cont

def run_command(cmd):
    import subprocess
    import shlex
    subprocess.check_call(shlex.split(cmd))

def setup(cont_name, keyfile, image, need_install_python=False, **kwargs):
    with open(keyfile) as f:
        pub_key = f.read()

    # добавляем директорию ansible_plugins в список, где искать доп. расширения
    # (до run_api())
    from ansible import utils
    import o_p
    import os
    get_par = os.path.dirname
    utils.plugins.push_basedir(o_p.join(get_par(get_par(__file__)), "ansible_plugins"))

    import ans_module
    labels = {
        "disvolvu": "test"
    }    
    # настраиваем docker без with_sudo=True
    res = ans_module.run_api("docker", name=cont_name, image=image,
                             labels=labels, **kwargs)
    assert res
    
    client = docker.Client()
    cont = find_container(cont_name, client)
    assert cont
    ip_addr = update_ssh_config.get_ipaddr(cont, client)
    #print(ip_addr)
    
    # удаляем предыдущий возможный fingerprint
    known_hosts = os.path.expanduser("~/.ssh/known_hosts")
    run_command("""ssh-keygen -f "%(known_hosts)s" -R %(ip_addr)s""" % locals())
    
    # добавляем SSH-публичный ключ хоста в known_hosts, чтобы
    # ssh не ругался при неинтерактивном соединении
    from ansible.module_utils.known_hosts import add_git_host_key
    
    # :TRICKY: настраиваем фейковый модуль
    from ansible.module_utils.basic import AnsibleModule
    ans_module.setup_module_arguments(None)
    fake_module = AnsibleModule({})
    
    # :KLUDGE: сделать нормальную функцию без имитации git-адреса
    add_git_host_key(fake_module, "git@%(ip_addr)s/" % locals())
    
    # 
    standard_password = "docker.io"
    
    if need_install_python:
        run_command("sshpass -p %(standard_password)s ssh root@%(ip_addr)s apt-get -y install python" % locals())
    
    # в Ubuntu пакет python уже есть, поэтому
    # сразу к делу - authorized_key
    run_module([
        {
            "host": ip_addr,
            "settings": {
                "ansible_ssh_user": "root",
                "ansible_ssh_pass": "docker.io"
            },
            
        },
    ], "authorized_key", '', user="root", key=pub_key)
    
    update_ssh_config.main()

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("name",    help="name of Docker container to create")
    parser.add_argument("keyfile", help="path to public SSH keyfile to setup for root in container")
    args = parser.parse_args()
    
    cont_name = args.name
    keyfile   = args.keyfile
    
    setup(cont_name, keyfile, "ubuntu-upstart:trusty")

if __name__ == '__main__':
    main()
