#!/usr/bin/env python
# coding: utf-8

# :TRICKY: не переводим в Python 3 из-за
# ansible-кода (а так - сразу)

from __future__ import print_function

node_graph = {}

import argparse
def make_struct(**kwargs):
    return argparse.Namespace(**kwargs)

def create_node(sources):
    return make_struct(
        sources = set(sources),
        visited = False,
        action  = None
    )

def append_edge(target, sources=None, action=None):
    """ sources - список, от которых зависит target """
    if sources is None:
        sources = []

    for src in sources:
        append_edge(src)
    
    node = node_graph.get(target)
    if node:
        if sources:
            node.sources = node.sources.union(sources)
    else:
        node_graph[target] = node = create_node(sources)
        
    if action:
        assert not node.action, "Node %(target)s already has action" % locals()
        node.action = action

def pass_topologically(targets, on_passing_node):
    #    
    # топологическая сортировка
    #
    def pass_around(name, node):
        if not node.visited:
            node.visited = True
            for src in node.sources:
                pass_around(src, node_graph[src])
                
            on_passing_node(name, node)
    
    for name in targets:
        pass_around(name, node_graph[name])

default_targets = []

def append_defaults(lst):
    default_targets.extend(lst)

class StopExecution(Exception):
    pass

def message(text):
    print("\n%(text)s" % locals())

def play_receipt(args):
    glbs = {
        # exec/execfile() не устанавливает __file__, поэтому делаем сами
        # :TRICKY: еще можно вытащить имя файла через inspect.getframeinfo(inspect.currentframe())[0] уже
        # при выполнении, но, кажется, это хак
        "__file__" : args.receipt
    }
    
    execfile(args.receipt, glbs)

import timeit
def timer():
    tmr = timeit.default_timer # time.clock
    return tmr()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-order", action='store_true', help="only print order of nodes to run")
    parser.add_argument("--all-targets", action='store_true', help="run all targets")
    parser.add_argument("--report-timings", action='store_true', help="report time for each target to fullfill at end")

    # :TODO: дела по автодополнению:
    # - пути автодополняются не так, как обычно (зачем полные пути?)
    # - зачем автодополняются опции после указания рецепта
    # - глобальное автодополнение не работает:
    #   - в Ubuntu пакет есть, но он выполняет activate-global-python-argcomplete
    #   - даже если вручную включить для текущего терминала (появится hook _python_argcomplete_global()),
    #     то все равно не работает, хотя eval "$(register-python-argcomplete disvolvu)" работает - надо разбираться
    
    import argcomplete
    import argcomplete.completers
    # :TRICKY: по умолчанию автодополняются файлы, но почему-то пробел ставится; если использовать
    # argcomplete.completers.FilesCompleter, то похоже на поведение по умолчанию, хотя все равно не
    # так (автодополняемые пути выдаются полностью, а не последние компоненты)
    parser.add_argument("receipt", metavar="receipt.py").completer = argcomplete.completers.FilesCompleter()
    
    def all_targets_completer(prefix, parsed_args, **kwargs):
        play_receipt(parsed_args)
        #argcomplete.warn("arguments:", parsed_args, kwargs)
        
        #lst = ["qqq", "www", "eee", "rrr"]
        lst = node_graph.keys()
        return (v for v in lst if v.startswith(prefix))
    parser.add_argument('targets', nargs=argparse.REMAINDER, help="targets to fullfill").completer = all_targets_completer
    
    argcomplete.autocomplete(parser)
    
    args = parser.parse_args()
    
    play_receipt(args)
    
    user_targets = args.targets
    if not user_targets:
        user_targets = default_targets
        
    time_list = []
    def run_node(name, node):
        if node.action:
            if args.report_timings:
                dur = timer()
                res = node.action()
                time = timer() - dur
                time_list.append((name, time))
            else:
                res = node.action()
            if res is False:
                message("""Fullfilling target %(name)s failed.""" % locals())
                raise StopExecution()
        
    on_passing_node = run_node

    if args.print_order:
        def print_node(name, node):
            properties = []
            if name in user_targets:
                properties.append("requested")
                
            if name in default_targets:
                properties.append("default")
            
            text = name
            if properties:
                properties = ", ".join(properties)
                text = "%(text)s (%(properties)s)" % locals()
            print(text)
        on_passing_node = print_node
    
    targets = node_graph.keys() if args.all_targets else user_targets
    
    try:
        pass_topologically(targets, on_passing_node)
    except StopExecution:
        pass
    
    if args.report_timings:
        import operator
        time_list.sort(key=operator.itemgetter(1), reverse=True)
        
        print()
        print("Timing Report:")
        
        import s_
        total = 0
        for item in time_list:
            time = item[1]
            print("%(item[0])-20s .................. %(time).2f sec" % s_.EvalFormat())
            total += time
            
        print()
        print("Total: %.2f sec" % total)

if __name__ == '__main__':
    main()
    