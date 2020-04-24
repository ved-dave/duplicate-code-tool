"""
Duplicate code detection tool - implemented using abstract syntax trees (AST)
"""

import ast
import collections
import argparse
import itertools

def main():
    # implement this through configs
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('files', 
        metavar='filepath(s)', nargs='+', 
        help='filepath for python file(s)')
    args.add_argument('--ignore', '-i',
        metavar='NODE', nargs='+', default=['Name'], 
        help='ignore predefined syntactic constructs')
    args.add_argument('--min', '-m',
        metavar='N', type=int, default=3, 
        help='Only report duplicates after N repetitions')
    input = args.parse_args()

    # Read file
    sources = Index(input.ignore)    
    for filepath in input.files:
        sources.add(filepath)

    # Output FIX FOR STATIC ERROR
    for expr, clones in sources.clones():
        if len(clones) >= input.min:
            print("+%d repeated instance of: %s ->" % 
                    (len(clones), expr))
            for filepath, group in itertools.groupby(clones, 
                    lambda clone: clone.file.name):
                print("  - in %s" % filepath)
                for clone in group:
                    begin, end, source = clone.source(' '*8)
                    if begin == end:
                        line = 'line %d' % begin
                    else:
                        line = 'lines %d to %d' % (begin, end)
                    print('      %s:\n%s' % (line, source))
class Position(ast.NodeVisitor):
    '''
    Find a clone position in the code (its line-span).
    Count child nodes.
    '''
    def init(self, clone):
        self.begin_line = self.end_line = clone.node.lineno
        self.node_count = 0
        self.generic_visit(clone.node)
    def visit(self, node):
        '''
        Find node's line and column span
        '''
        if hasattr(node, 'lineno'):
            self.begin_line = min(self.begin_line, node.lineno)
            self.end_line = max(self.end_line, node.lineno)
            self.node_count += 1
            self.generic_visit(node)

class Clone(collections.namedtuple('Clone', 'node file position')):
    '''
    A set of code.
    '''
    def source(self, indent=''):
        '''
        Retrieve original source code.
        '''
        if not hasattr(self.position, 'begin_line'):
            self.position.init(self)
        lines = self.file.source[
            self.position.begin_line-1:self.position.end_line]
        return (self.position.begin_line, self.position.end_line,
                '\n'.join(indent + line.rstrip() for line in lines))

class Clones(list):
    '''
    A list of identical code snippets.
    '''
    def score(self):
        '''
        Provide a score for ordering clones while reporting.
        This sorts by number of nodes in the subtree, number
        of clones of the node, and code size.
        '''
        candidate = self[0] # Pick the first clone.
        size = len(candidate.source()[-1])
        return (candidate.position.node_count, len(self), size)

class File: # SOURCE FILE
    def __init__(self, name, source):
        self.name = name
        self.source = source
            
def digest(node):
    '''
    return string representation of a sub-tree in the node.
    Emulates ast.dump(node, False).
    '''
    if isinstance(node, ast.AST):
        if not hasattr(node, '_cached'):
            node._cached = '%s(%s)' % (node.__class__.__name__, ', '.join(
                digest(b) for a, b in ast.iter_fields(node)))
        return node._cached
    elif isinstance(node, list):
        return '[%s]' % ', '.join(digest(x) for x in node)
    return repr(node)

class Index(ast.NodeVisitor):
    '''
    A source code repository.
    '''
    def __init__(self, exclude):
        '''
        Create a new file indexer.
        '''
        self.nodes = collections.defaultdict(Clones)
        self.blacklist = frozenset(exclude)
    def add(self, file):
        '''
        Add a file to the index and parse it.
        '''
        source = open(file).readlines()
        tree = ast.parse(''.join(source))
        self._file = File(file, source)
        self.generic_visit(tree)
    def visit(self, node):
        '''
        Traverse Abstract Syntax Tree of file.
        '''
        if hasattr(node, 'lineno'):
            if node.__class__.__name__ not in self.blacklist:
                expr = digest(node)
                self.nodes[expr].append(
                    Clone(node, self._file, Position()))
        self.generic_visit(node)
    def clones(self):
        '''
        Returns a list of duplicate constructs.
        '''
        return sorted(((expr, nodes) 
            for expr, nodes in self.nodes.items() if len(nodes) > 1),
                key = lambda n: n[1].score(), reverse = True)        

if __name__ == '__main__':
    main()