"""
A series of utility functions for transforming BRIL programs into and out of SSA form.
"""
import json
import sys
from collections import defaultdict, deque
from typing import Dict, List, Set

from bril_type import *
from cfg import get_entry_nodes, to_cfg_fine_grain
from dominator import _get_dominators, dominance_frontier, dominance_tree
from node import Node, PhiNode, visualize
from utils import load


def _collect_vars(entry_node: Node) -> Dict[str, Set[Node]]:
    """
    Return a mapping of variables to the nodes in which they are defined/assigned .
    """
    var_to_assignments: Dict[str, Set[Node]] = defaultdict(set)
    q = deque([entry_node])
    seen: Set[str] = set()
    while q:
        node = q.popleft()
        seen.add(node.id)

        # assignment statement
        if "dest" in node.instr:
            var_name = node.instr["dest"]
            var_to_assignments[var_name].add(node)

        q.extend([succ for succ in node.successors if succ.id not in seen])

    return var_to_assignments


def _rename_vars(entry_node: Node, dom_tree_dict: Dict[str, List[Node]]) -> None:
    """
    Rename variables in a CFG to be in SSA form.
    - entry_node: the entry node of the CFG
    - dom_tree_dict: a mapping of node_id to nodes that it immediately dominates
    """
    # key: old_var_name, value: deque of renamed var_names (var -> var_0, var_1, etc.)
    var_stack: Dict[str, deque] = defaultdict(deque)

    # could use len(var_stack[var]) instead?
    var_counter: Dict[str, int] = defaultdict(int)

    # tracks the current path the recursive _rename function has taken from the entry_node
    node_ids_seen: Set[str] = set()

    def _get_new_name(var: str) -> str:
        new_name = f"{var}_{var_counter[var]}"
        var_counter[var] += 1
        var_stack[var].append(new_name)
        return new_name

    def _rename(node: Node) -> None:
        node_ids_seen_cache = node_ids_seen.copy()
        node_ids_seen.add(node.id)

        # deep copy of var_stack
        var_stack_cache = {var_name: q.copy() for var_name, q in var_stack.items()}

        # rename dest for all phi_nodes in current node
        if node.phi_nodes is not None:
            for _, phi in node.phi_nodes.items():
                phi.dest = _get_new_name(phi.dest)

        if "args" in node.instr:
            # replace args
            new_args = [var_stack[arg][-1] for arg in node.instr["args"]]
            node.instr["args"] = new_args

        if "dest" in node.instr:
            # replace dest
            pre_rename_dest = node.instr["dest"]
            post_rename_dest = _get_new_name(pre_rename_dest)
            node.instr["dest"] = post_rename_dest

        # update phi_nodes in successors
        for succ in node.successors:
            if succ.phi_nodes is not None:
                for pre_rename_dest, phi in succ.phi_nodes.items():
                    for phi_src_node_id in phi.args.keys():
                        # if phi_src_node_id exists on the current path
                        # (recursively traversed from the entry_node)
                        if phi_src_node_id in node_ids_seen:
                            phi.args[phi_src_node_id] = var_stack[pre_rename_dest][-1]

        # rename all immediately dominated nodes
        for im_dom_node in sorted(dom_tree_dict[node.id]):
            _rename(im_dom_node)

        # restore var_stack
        var_stack.clear()
        var_stack.update(var_stack_cache)

        # restore node_ids_seen
        node_ids_seen.clear()
        node_ids_seen.update(node_ids_seen_cache)

    _rename(entry_node)


def to_ssa(entry_node: Node) -> None:
    """
    Convert a CFG into SSA form.
    """
    var_to_assignments = _collect_vars(entry_node)

    for var in var_to_assignments.keys():
        assignments_q = deque(var_to_assignments[var])
        while assignments_q:
            node = assignments_q.popleft()
            for df_node in dominance_frontier(node, entry_node):
                # no phi_nodes, create one for var
                if df_node.phi_nodes is None:
                    df_node.phi_nodes = {var: PhiNode(dest=var, args={node.id: var})}

                # no phi_node for var, create one
                elif var not in df_node.phi_nodes:
                    df_node.phi_nodes[var] = PhiNode(dest=var, args={node.id: var})

                else:
                    df_node.phi_nodes[var].args[node.id] = var

                # update assignments to include the phi node use case
                if df_node not in var_to_assignments[var]:
                    var_to_assignments[var].add(df_node)
                    assignments_q.append(df_node)

    doms = _get_dominators(entry_node)
    all_nodes = {node.id: node for node in doms.keys()}

    dom_tree = dominance_tree(doms)
    dom_tree_dict = {
        node.id: [all_nodes[succ.id] for succ in node.successors] for node in dom_tree
    }

    _rename_vars(entry_node, dom_tree_dict)


def from_ssa(cfg_nodes: List[Node]) -> List[Node]:
    """
    Convert a CFG from SSA form back into regular form.
    """
    return []


def validate_ssa(cfg_nodes: List[Node]) -> bool:
    """
    Validate that a CFG is in SSA form.
    """
    return True


if __name__ == "__main__":
    program, cli_flags = load(["-to", "-from", "-check"])

    if program is None:
        sys.exit(1)

    if not cli_flags["to"] and not cli_flags["from"]:
        print("Please specify either: \n  ... ssa.py -to \n  ... ssa.py -from")
        sys.exit(1)

    cfg_root_nodes = to_cfg_fine_grain(program)

    if cli_flags["to"]:
        for root_node in cfg_root_nodes:
            to_ssa(root_node.entry_node)
            print(visualize(root_node.entry_node))

    elif cli_flags["from"]:
        if cli_flags["-check"]:
            # Validate that the program is in SSA form
            pass
        pass
