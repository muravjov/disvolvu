#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function

import disvolvu
import ans_module
import os

ansible_action_impl = ans_module.run_api

def ansible_action(tgt_name, sources, module_name, **kwargs):
    def on_action():
        return ansible_action_impl(module_name, **kwargs)
    
    disvolvu.append_edge(tgt_name, sources=sources, action=on_action)

def ansible_apt_impl(lst):
    return ansible_action_impl("apt", with_sudo=True, name=lst)

#
# apt_action()
# 
def apt_action(tgt_name, pkg_list):
    ansible_action(tgt_name, [], "apt", with_sudo=True, name=pkg_list)

#
# deploy_mysql_db()
#

import subprocess
import shlex

def run_sudo_cmd(cmd):
    # :REFACTOR: ans_module.run_module()
    print("\nsudo " + cmd)
    process = subprocess.Popen(["sudo"] + shlex.split(cmd), stdout=subprocess.PIPE)
    
    output, unused_err = process.communicate()
    retcode = process.poll()
    
    return retcode, output

def db_not_exists(dbname):
    cmd = """mysql -sNe "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME='%(dbname)s'" """ % locals()
    # :TRICKY: можно через  -u root, то по-моему это хак
    retcode, output = run_sudo_cmd(cmd)
    assert retcode == 0, "failed cmd: %(cmd)s" % locals()
    
    return output.find(dbname) == -1

def ans_action_check(module_name, **kwargs):
    res = ansible_action_impl(module_name, **kwargs)
    assert res, "failed ansible module: %(module_name)s, kwargs = %(kwargs)s" % locals()

# если что-то пошло не так = установилось наполовину:
# - drop database <dbname>
# - drop user '<username>'@'localhost';
# - поправить код, дамп и т.д.
# - запустить снова
def deploy_mysql_db(dbname, dump_fpath, username=None, password=None):
    # установка базы
    
    res = ansible_apt_impl([
        # :COPY_N_PASTE_ETALON: pybooksdk.install_mysql_server()
        "mysql-server",
        "python-mysqldb", # для модулей Ansible
    ])
    assert res
    
    # аналогично ansible/site.py: развертывание db
    if db_not_exists(dbname):
        ans_action_check("mysql_db", with_sudo=True, name=dbname, state="present")

        if username:
            ans_action_check("mysql_user", with_sudo=True, name=username, password=password, priv="%(dbname)s.*:ALL" % locals(), state="present")
        
        def import_db(dump_fpath):
            ans_action_check("mysql_db", with_sudo=True, name=dbname, state="import", target=dump_fpath)
        
        if dump_fpath.endswith(".gz"):
            import o_p
            import gzip
            import contextlib
            import shutil
            
            with contextlib.nested(gzip.open(dump_fpath), o_p.create_named_tmp_file(suffix="sql")) as (src_f, dst_f):
                shutil.copyfileobj(src_f, dst_f)
                dst_f.close()
                
                import_db(dst_f.name)
        else:
            import_db(dump_fpath)

#
# git_action()
#

def git_action(tgt_name, repo, dest, add_git_host_key=True, **kwargs):
    """ add_git_host_key=False: попытка указать (коду модуля git.py) не
        связываться с изменением known_hosts"""
    
    if add_git_host_key:
        kwargs["accept_hostkey"] = True
    else:
        kwargs["ssh_opts"] = "-o StrictHostKeyChecking=no"
        
    if not("merge" in kwargs):
        kwargs["merge"] = True

    ansible_action(tgt_name, None, "git", repo=repo, dest=dest, **kwargs)

#
# pip_action()
#

def pip_action_sources(tgt_name, sources, env_path, req_path=None, **kwargs):
    # :TRICKY: модуль pip запускает все команды из директории /tmp, suprpise!
    if req_path:
        kwargs["requirements"] = os.path.realpath(req_path)
        
    ansible_action(tgt_name, sources, "pip", virtualenv=os.path.realpath(env_path), **kwargs)

def pip_action(tgt_name, source, env_path, req_path=None, **kwargs):
    sources = []
    if source:
        sources.append(source)
    
    pip_action_sources(tgt_name, sources, env_path, req_path=req_path, **kwargs)

#
# docker_action()
#

sshpass_installed = False

def docker_action(tgt_name, keyfile, image, **kwargs):
    def on_action():
        import setup_container
        res = bool(setup_container.find_container(tgt_name, search_all=True))
        
        if not res:
            setup_container.setup(tgt_name, keyfile, image, **kwargs)
    
    source = "dvsdk_sshpass"

    global sshpass_installed
    if not sshpass_installed:
        apt_action(source, "sshpass")
        sshpass_installed = True
    disvolvu.append_edge(tgt_name, [source], action=on_action)
    
