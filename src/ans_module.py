#!/usr/bin/env python
# coding: utf-8
from __future__ import print_function

import sys
import json
import disvolvu # message()
import os

import ansible.module_utils.basic as basic

def clean_execfile(fpath, gvars=None):
    # нам нужна компиляция fpath без наследования флагов =>
    # dont_inherit = 1
    
    #execfile(fpath, gvars) 
    with open(fpath) as f:
        code = compile(f.read(), fpath, 'exec', 0, 1)
        exec(code, gvars)    

class StopModuleExecution(Exception):
    pass

def setup_module_arguments(args, **complex_args):
    # настраиваем параметры как в modify_module()
    #module_data = module_data.replace(REPLACER_VERSION, repr(__version__))
    #module_data = module_data.replace(REPLACER_ARGS, encoded_args)
    #module_data = module_data.replace(REPLACER_COMPLEX, encoded_complex)

    import ansible

    basic.ANSIBLE_VERSION = ansible.__version__
    basic.MODULE_ARGS     = args if args else ""
    # сам Ansible использует обертку в виде ansible.utils.jsonify()
    basic.MODULE_COMPLEX_ARGS = json.dumps(complex_args)
    
    basic.VERBOSE_OUTPUT = True
    
    # :KLUDGE: отправить фикс в upstream ansible, чтоб такой ерундой не заниматься 
    import ansible.module_utils.known_hosts as known_hosts
    known_hosts.os = os

def run_module_do(module_name, args, on_finish=None, **complex_args):
    """ Сложные аргументы удобней передавать complex_args,
        оставив args = None"""
    
    from ansible import utils
    module_path = utils.plugins.module_finder.find_plugin(module_name, None)
    assert module_path, '''No such module "%(module_name)s"''' % locals()
    
    setup_module_arguments(args, **complex_args)
    
    if on_finish:
        def do_finish(res, kwargs):
            on_finish(res, kwargs)
            raise StopModuleExecution()
            
        def exit_json(self, **kwargs):
            ''' return from the module, without error '''
            self.add_path_info(kwargs)
            if not 'changed' in kwargs:
                kwargs['changed'] = False
            self.do_cleanup_files()

            #print self.jsonify(kwargs)
            #sys.exit(0)
            do_finish(True, kwargs)
    
        def fail_json(self, **kwargs):
            ''' return from the module, with an error message '''
            self.add_path_info(kwargs)
            assert 'msg' in kwargs, "implementation error -- msg to explain the error is required"
            kwargs['failed'] = True
            self.do_cleanup_files()
            
            #print self.jsonify(kwargs)
            #sys.exit(1)
            do_finish(False, kwargs)
        
        AnsibleModule = basic.AnsibleModule
        # :TODO: не менять каждый раз
        AnsibleModule.exit_json = exit_json
        AnsibleModule.fail_json = fail_json
    
    glbs = {
        # :KLUDGE: для модулей типа apt.py требуется удостовериться, что они __main__
        "__name__": "__main__"
    }
    try:
        clean_execfile(module_path, glbs)
    except StopModuleExecution:
        pass
    
    # :KLUDGE: git.py мусорит, черт; надо общаться с upstream
    def clear_env_var(name):
        if name in os.environ:
            del os.environ[name]
    clear_env_var("GIT_SSH")
    clear_env_var("GIT_SSH_OPTS")

def run_module(module_name, args, on_finish=None, with_sudo=False, **complex_args):
    if on_finish:
        def on_verbose_finish(res, res_kwargs):
            if not res:
                module_name, args, complex_args
                import pprint
                disvolvu.message("ans_module error: %(module_name)s, %(args)s, %(complex_args)s: %(res_kwargs)s" % locals())
            on_finish(res)
    else:
        on_verbose_finish = None
    
    if with_sudo:
        # Опыт по выполнению команд с привилегиями:
        # - по умолчанию sudo не трогает stdin, а напрямую связывается с терминалом (tty) для получения пароля;
        #   так что через sudo можно спокойно передавать данные от родительского процесса к дочернему через stdin
        #   опция -S отключает это поведение
        # - ssh поступает аналогично, только ключа -S у нее нет; зато есть спец. программа sshpass, которая обманывает
        #   ssh, создавая виртуальный терминал
        # - функционал become_user сделан на основе функции utils.make_become_cmd(), вот вариант:
        #   >>> utils.make_become_cmd('whoami', 'root', '/bin/bash', 'sudo')[0]
        #       /bin/bash -c 'sudo -k && sudo -H -S -p "[sudo via ansible, key=ptxobqqddlurcnjwbxulojkgmqzizdtj] password: " -u root /bin/bash -c '"'"'echo BECOME-SUCCESS-ptxobqqddlurcnjwbxulojkgmqzizdtj; whoami'"'"''
        #   ; случайная последовательность (в данном случае ptxobqqddlurcnjwbxulojkgmqzizdtj) используется для
        #   нахождения успеха при вводе пароля - строки echo BECOME-SUCCESS-ptxobqqddlurcnjwbxulojkgmqzizdtj, чтобы
        #   после нее считывать stdout уже целевой программы (whoami)
        import subprocess
        import shlex
        import s_
        
        cmd = "\nsudo %(sys.executable)s %(__file__)s --stdin %(module_name)s" % s_.EvalFormat()
        print(cmd)
        process = subprocess.Popen(shlex.split(cmd), 
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        
        args_struct = {
            "args":         args,
            "complex_args": complex_args
        }
        json.dump(args_struct, process.stdin)
        # communicate() сам в любом случае закрывает stdin
        #process.stdin.close()
        
        output, unused_err = process.communicate()
        retcode = process.poll()
        
        if on_finish:
            json_ok = True
            try:
                res_kwargs = json.loads(output)
            except:
                json_ok = False
                res_kwargs = None
                
            res = retcode == 0
            if json_ok:
                on_verbose_finish(res, res_kwargs)
            else:
                disvolvu.message('''ans_module format error: %(module_name)s, %(args)s, %(complex_args)s: "%(output)s"''' % locals())
                on_finish(res)
        else:
            print(output, end='')
            sys.exit(retcode)
    else:
        run_module_do(module_name, args, on_finish=on_verbose_finish, **complex_args)

def run_api(module_name, **kwargs):
    result = disvolvu.make_struct()
    def on_finish(res):
        result.res = res
        
    run_module(module_name, None, on_finish=on_finish, **kwargs)
    return result.res

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdin", action='store_true', help="read arguments from stdin")
    parser.add_argument("--sudo", action='store_true', help="run command with sudo")
    parser.add_argument("command")
    parser.add_argument('args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    
    # в Python 3.3 есть тот же quote, но в логичном shlex.quote()
    import pipes
    ans_args = ' '.join([pipes.quote(arg) for arg in args.args])
    
    if args.stdin:
        args_struct = json.load(sys.stdin)
        ans_args     = args_struct["args"]
        complex_args = args_struct["complex_args"]
    else:
        complex_args = {}
    run_module(args.command, ans_args, with_sudo=args.sudo, **complex_args)

if __name__ == '__main__':
    main()
