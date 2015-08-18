# Disvolvu

Disvolvu is an utility for deploying projects on *developer's machines*. For complex
projects today you have not only grab sources from various repositories, but also install
system dependencies, create test environments and so on just to begin your real coding work.

Disvolvu suggests a way to automate this routine work in way that utility `make` does.
You write a text file, called a *receipt*, where you define targetes, its dependencies
and rules how to reach targets.

## Installation

    $ pip install -r https://github.com/muravjov/disvolvu/raw/master/requirements.txt

## Syntax

```
$ disvolvu 
usage: disvolvu [-h] [--print-order] [--all-targets] [--report-timings]
                receipt.py ...

positional arguments:
  receipt.py
  targets           targets to fullfill

optional arguments:
  -h, --help        show this help message and exit
  --print-order     only print order of nodes to run
  --all-targets     run all targets
  --report-timings  report time for each target to fullfill at end
```

## Real-world example

Let's consider the following receipt, `bootstrap.py`:

```python
# coding: utf-8

import dvsdk
import disvolvu

# install PHP dependencies for target "vu-php-dep"
dvsdk.apt_action("vu-php-dep", [
    "php5-cli",
    "php5-mysqlnd",
])

# git clone the main source repository to the folder vortaro_updater
dvsdk.git_action("vortaro_updater-git", "git@bitbucket.org:******.git", "vortaro_updater")

def on_db_deploy():
    dvsdk.deploy_mysql_db("vortaro", "vortaro_updater/test-data/vortaro.sql.gz")

# create MySQL database vortaro and fill it with dump vortaro.sql.gz
disvolvu.append_edge("test-database", ["vortaro_updater-git"], action=on_db_deploy)

# install Python3 dependencies
dvsdk.apt_action("vu-py-dep", [
    "python-virtualenv",
    "python3",
    "python3-dev",
])

# create virtualenv "env" and pin install -r vortaro_updater/requirements.txt
dvsdk.pip_action_sources(
    "vortaro_updater-env", 
    ["vortaro_updater-git", "vu-py-dep"], 
    "env", "vortaro_updater/requirements.txt", python_bin="python3"
)

# git clone the second repository with code for deploying via Ansible
dvsdk.git_action("ansible-git", "git@bitbucket.org:******.git", "ansible")
# also, setup virtualenv for Ansible
dvsdk.pip_action("ansible-env", "ansible-git", "ansible/env", "ansible/requirements.txt")

# create a test machine test-eoru via Docker, using image "tutum/debian:wheezy",
# and add public key ~/.ssh/id_dsa.pub to it
import os
keyfile = os.path.expanduser("~/.ssh/id_dsa.pub")
# https://github.com/tutumcloud/tutum-debian
env = {
    "ROOT_PASS": "docker.io"
}
dvsdk.docker_action("test-eoru", keyfile, "tutum/debian:wheezy", need_install_python=True, env=env)

# do a deploy to the test machine
def on_test_eoru_deploy():
    import subprocess
    import shlex
    subprocess.check_call(shlex.split("env/bin/ansible-playbook -i ./hosts site.py"), cwd="ansible")
disvolvu.append_edge("deploy-test-eoru", ["test-eoru", "ansible-env"], action=on_test_eoru_deploy)

# target "all" depends on other targets, and is default
disvolvu.append_edge("all", [
    "vu-php-dep",
    "test-database",
    
    "vortaro_updater-env",
    "ansible-env",
])

disvolvu.append_defaults(["all"])

```

So, let's run it. By default we execute the target 'all':

	$ disvolvu bootstrap.py
    
To see what particular targets will be executed and in which order, use the option `--print-order`:

	$ disvolvu --print-order bootstrap.py

    ansible-git
    ansible-env
    vortaro_updater-git
    vu-py-dep
    vortaro_updater-env
    vu-php-dep
    test-database
    all (requested, default)

This command will deploy our service to the test Docker machine, which will be created also by this receipt:

	$ disvolvu bootstrap.py deploy-test-eoru
    
## Ansible API

`disvolvu` make use of Ansible modules for implementing the big part of its own API. Namely, the function `ans_module.run_api(module, **kwargs)` runs the corresponding Ansible module with arguments on the local machine. Examples:

	ans_module.run_api("git", repo="https://github.com/ansible/ansible.git", dest="ansible")
clones Ansible sources into the folder `ansible`, more about `git` module usage see at [git module](http://docs.ansible.com/ansible/git_module.html);

	ans_module.run_api("docker", image="tutum/debian:wheezy")
create and runs Docker machine from the image `tutum/debian:wheezy`, more about `docker` module usage see at [docker module](http://docs.ansible.com/ansible/docker_module.html);

	ans_module.run_api("apt", with_sudo=True, name=["mysql-server"])
installs MySQL server via apt, more about `apt` module usage see at [apt module](http://docs.ansible.com/ansible/apt_module.html).

## Autocomplete

`disvolvu` use the [argcomplete](http://argcomplete.readthedocs.org) for autocomplete options and targets in receipts.
For example, to turn autocomplete on you should have `disvolvu` in your PATH and run in the terminal:
	
    $ eval "$(register-python-argcomplete disvolvu)"

## FAQ

    :TODO: document
    Core API: disvolvu.append_edge(target, sources=None, action=None)
    no-global-site-packages.txt for apt to work
    API in dvsdk
