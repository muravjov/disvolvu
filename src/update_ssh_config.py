#!/usr/bin/env python
# coding: utf-8
from __future__ import print_function
import os

def get_name(cont):
    names = cont["Names"]
    return names[0][1:]

def get_ipaddr(cont, client):
    info = client.inspect_container(cont)
    return info["NetworkSettings"]['IPAddress']

def update_ssh_config():
    import docker
    client = docker.Client()
    
    # запрос на функционал "Include" давно висит трекере ошибок OpenSSH,
    # https://bugzilla.mindrot.org/show_bug.cgi?id=1585 , движения нет и вряд ли
    # что изменится => делаем свою систему ~/.ssh/config.d

    # проверяем только стартовавшие контейнеры, потому что только у них 
    # есть IP-шники
    #for cont in client.containers(all=True):
    lst = []
    import disvolvu # make_struct
    for cont in client.containers():
        if cont["Labels"].get("disvolvu") == "test":
            lst.append(disvolvu.make_struct(
                name    = get_name(cont), 
                ip_addr = get_ipaddr(cont, client),
            ))
            
    import s_
    with open(os.path.expanduser("~/.ssh/config.d/local_docker"), mode='w') as f:
        for item in lst:
            f.write("""
Host %(item.name)s
    HostName %(item.ip_addr)s
    User root
""" % s_.EvalFormat())

def main():
    update_ssh_config()
    
    import ans_module
    prefix = os.path.expanduser("~/.ssh")
    
    # :KLUDGE: очень большое желание переписать самому, потому что
    # способа включать только НЕ вида *.old напрямую нет, хотя казалось бы - 
    # естественное желание; логика - либо нет точек, либо есть (одна), после нее
    # нет old, затем может быть что-то, но без точек
    regexp=r"(?P<a>^[^.]+$)|(?P<b>\.(?!old)[^.]*$)"

    ans_module.run_api("assemble", src=os.path.join(prefix, "config.d"), dest=os.path.join(prefix, "config"),
                       backup=True, delimiter='\n### START FRAGMENT ###\n\n',
                       regexp=regexp)

if __name__ == '__main__':
    main()
