import itertools
import yaml
import os
import pybedtools
# The functools.partial trick to get descriptions to be valid is from:
#
#   http://code.google.com/p/python-nose/issues/detail?id=244#c1
from functools import partial

this_dir = os.path.dirname(__file__)
config_fn = os.path.join(this_dir, 'test_cases.yaml')


def fix(x):
    """
    Replaces spaces with tabs, removes spurious newlines, and lstrip()s each
    line. Makes it really easy to create BED files on the fly for testing and
    checking.
    """
    s = ""
    for i in  x.splitlines():
        i = i.strip()
        if len(i) == 0:
            continue
        i = i.split()
        i = '\t'.join(i)+'\n'
        s += i
    return s


def parse_yaml(infile):
    x = yaml.load(open(infile).read())
    for test_case in x:
        method = test_case['method']
        send_kwargs = test_case['kwargs']
        expected = test_case['expected']
        yield method, send_kwargs, expected


def run(method, bedtool, expected, **kwargs):
    result = getattr(bedtool, method)(**kwargs)
    print result.fn
    print 'Method call:'
    args = []
    for key, val in kwargs.items():
        args.append(('%s=%s' % (key, val)).strip())

    args = ', '.join(args)
    print 'BedTool.%(method)s(%(args)s)' % locals()
    print 'Got:'
    print result
    print 'Expected:'
    print expected
    assert str(result) == fix(expected)

def test_a_b_methods():
    """
    Generator that yields tests, inserting different versions of `a` and `b` as
    needed
    """
    for method, send_kwargs, expected in parse_yaml(config_fn):

        if 'abam' in send_kwargs:
            send_kwargs['abam'] = pybedtools.example_filename(send_kwargs['abam'])
            send_kwargs['a'] = send_kwargs['abam']

        if not (('a' in send_kwargs) and ('b' in send_kwargs)):
            continue

        # If abam, makes a BedTool out of it anyway.
        orig_a = pybedtools.example_bedtool(send_kwargs['a'])
        orig_b = pybedtools.example_bedtool(send_kwargs['b'])

        del send_kwargs['a']
        del send_kwargs['b']

        converter = {'filename': lambda x: pybedtools.BedTool(x.fn),
                     'generator': lambda x: pybedtools.BedTool(i for i in x),
                     'stream': lambda x: pybedtools.BedTool(open(x.fn))
                    }

        for kind_a, kind_b in itertools.permutations(('filename', 'generator', 'stream'), 2):

            # BAM only works as a filename; add other kinds here as they are
            # supported
            supported_bam = ('filename',)
            if 'abam' in send_kwargs:
                if (kind_a not in supported_bam):
                    continue

            # Convert to file/generator/stream
            bedtool = converter[kind_a](orig_a)
            b = converter[kind_b](orig_b)

            kind = 'a=%(kind_a)s, b=%(kind_b)s' % locals()

            send_kwargs['b'] = b

            f = partial(run, method, bedtool, expected, **send_kwargs)

            # Meaningful description
            f.description = '%(method)s, %(kind)s, %(send_kwargs)s' % locals()
            yield (f, )

def test_i_methods():
    """
    Generator that yields tests, inserting different versions of `i` as needed
    """
    for method, send_kwargs, expected in parse_yaml(config_fn):

        if ('a' in send_kwargs) and ('b' in send_kwargs):
            continue

        if 'i' not in send_kwargs:
            continue

        orig_i = pybedtools.example_bedtool(send_kwargs['i'])

        del send_kwargs['i']

        converter = {'file': lambda x: pybedtools.BedTool(x.fn),
                     'generator': lambda x: pybedtools.BedTool(i for i in x),
                     'stream': lambda x: pybedtools.BedTool(open(x.fn))
                    }
        done = []
        for kind_i in ('file', 'generator', 'stream'):
                i = converter[kind_i](orig_i)
                kind = 'i=%(kind_i)s' % locals()
                f = partial(run, method, i, expected, **send_kwargs)
                f.description = '%(method)s, %(kind)s, %(send_kwargs)s' % locals()
                yield (f, )