#!/usr/bin/env python

print 'import modules...',
import sys
sys.stdout.flush()
print

import system
import reader
import os
from context import DEFAULT_CONTEXT

C = DEFAULT_CONTEXT.copy()
C.QUERY = 'oakland1'
C.params.update({
  'algorithm': 'kdtree',
  'checks': 1024,
  'trees': 1,
  'vote_method': 'filter',
  'num_neighbors': 1,
  'dist_threshold': 70000,
  'confstring': '',
})

C.max_matches_to_analyze = 1
C.stop_on_homTrue = 0
C.put_into_dirs = 0
C.show_feature_pairs = True
C.do_posit = 0
C.solve_pnp = 0
C.dump_hom = 0

C.ranking_min_consistent = 1
C.ranking_max_considered = 30

C.ncells = 9
C.ambiguity = 75

if 'DEBUG' in os.environ:
  system.characterize(C)
else:
  with system.MultiprocessExecution():
    system.characterize(C)

# vim: et sw=2
