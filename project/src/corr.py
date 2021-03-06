# Anything related to feature-to-feature matches.
# find_corr() and draw_matches() are the main functions;
# there are also some experimental pose compute methods
# that don't really work that well (the 2d one might work ok)

from config import *
from gtfail import matches as fail
import time
import info
import Image, ImageDraw
from collections import defaultdict
import pyflann
import render_tags
import scipy.optimize
import scipy.optimize.minpack as opt
import reader
import random
import numpy as np
import numpy.linalg as alg
from numpy import array as arr
from numpy import transpose as tp
from numpy import dot
import geom
import util_cs188
import cv2.cv as cv
import os
import client
import bundlerWrapper
import earthMine
import pnp
import homographyDecomposition

MAX_PIXEL_DEVIATION = 5
FALLBACK_PIXEL_DEVIATIONS = [2,1]
CONFIDENCE_LEVEL = .9999999
BAD_HOMOGRAPHY_DET_THRESHOLD = .005
ROT_THRESHOLD_RADIANS = 0.2 # .1 ~ 5 deg

def plusminus(i, m):
  if random.random() < .5:
    return i + m
  else:
    return i - m

def cluster_matches(matches, Ct = 15.0):
  """return strongly connected components,
     where connected means < Ct in distance"""
  edges = defaultdict(list)

  def connect(i,j):
    edges[i].append(j)
    edges[j].append(i)

  for i, m in enumerate(matches):
    for j, n in enumerate(matches):
      d = geom.distance3dt(m['pt_3d'], n['pt_3d'])
      if d <= Ct:
        connect(i,j)

  clusters = []
  iclusters = []
  closed = set()
  for i, m in enumerate(matches):
    cluster = []
    icluster = []
    fringe = set([i])
    while fringe:
      x = fringe.pop()
      if x not in closed:
        cluster.append(matches[x])
        icluster.append(x)
        closed.add(x)
        for neighbor in edges[x]:
          fringe.add(neighbor)
    if cluster:
      clusters.append(cluster)
      iclusters.append(icluster)

  return clusters, iclusters

def pick_likeliest(matches):
  """Given list of matches between 1 q feature and db cells,
     return most likely correct, or []"""

  mean = sum([f['feature_dist'] for f in matches])/len(matches)
  clusters = cluster_matches(matches)[0]
  clusters = sorted(clusters, key=len, reverse=True)
  top = clusters[0]
  out = []
  for k in clusters:
    if len(k) == len(top):
      for l in k:
        if l['feature_dist'] < mean:
          out.append(l)
  return out

def combine_spatial(outputFilePaths):
  """Returns dictionary of siftfile => matches
     Eliminates spatially inconsistent feature matches"""

  # group by query feature
  space = defaultdict(list)
  for res in outputFilePaths:
    detailed = res + ('-detailed%s.npy' % DETAIL_VERSION)
    for image, matches in np.load(detailed):
      assert type(matches) == list
      for match in matches:
        match['db_image'] = image
        space[tuple(match['query'])].append(match)

  # TODO filter out spatially inconsistent features
  # for now simply picks min dist feature across cells
  comb = defaultdict(list)
  for qf, matches in space.iteritems():
    top = pick_likeliest(matches)
    for t in top:
      comb[t['db_image']].append(t)

  return comb

ngreen = 0
ntotal = 0
def filter_admits(match):
    return True
#    plane = match['point'][3]
#    return plane != 0 and plane != 255

#  global ngreen, ntotal
#  hue3 = match['point'][0]
##  INFO(match['point'])
#  ntotal += 1
#  if 80 < hue3 < 160:
#    ngreen += 1
#    if random.random() < .01:
#      print "green/total", ngreen, "/", ntotal
#    return False
#  return True

def combine_matches(outputFilePaths):
  """Returns dictionary of siftfile => matches"""
  comb = {}
  for res in outputFilePaths:
    detailed = res + ('-detailed%s.npy' % DETAIL_VERSION)
    for image, matches in np.load(detailed):
      assert type(matches) == list
      if image not in comb:
        comb[image] = []
      for match in matches:
        if filter_admits(match):
          comb[image].append(match)
  return comb

def hashmatch(m):
  d = m['db']
  q = m['query']
  o = 0
  for i in d:
    o += i
  for i in q:
    o += i
  return o

# eqv of 70k, euclidean, matchonce
def rematch(C, Q, dbsift):
  start = time.time()
  rdr = reader.get_reader(C.params['descriptor'])
  q = rdr.load_file(Q.siftpath)
  db = rdr.load_file(dbsift)
  flann = pyflann.FLANN()
  results, dists = flann.nn(db['vec'], q['vec'], 1, algorithm='linear')
  results, dists, q = np.array(results), np.array(dists), np.array(q)
  idx = np.argsort(dists)
  results = results[idx]
  dists = dists[idx]
  q = q[idx]
  count = 1000
  matches = []
  closed = set()
  for i in range(0,len(results)):
    if results[i] not in closed and dists[i] < 40000:
      closed.add(results[i])
      atom = {'db': db[results[i]]['geom'].copy(),
                      'query': q[i]['geom'].copy()}
      matches.append(atom)
      count -= 1
    if count == 0:
      break
  INFO_TIMING("rematch took %f" % (time.time() - start))
  return matches

class CameraModel:
  def __init__(self, source):
    self.imsize = source.image.size
    self.lat = source.lat
    self.lon = source.lon
    self.alt = 0
    self.pitch = 0
    self.yaw = source.yaw
    self.roll = 0

  def as_array(self):
    return (0,0)

  def evaluator(self, map3d, matches):
    meter = 1/1e5
    best = [9999999]
    def euclidean_error_function(arr):
      error = 0.0
      ctr = 0
      buf = []
      cbuf = []
      for m in matches:
        d, q = m['db'], m['query']
        feature = map3d[int(d[0]), int(d[1])]
        if not feature:
          continue
        ctr += 1
        pz, px = geom.lltom(self.lat + meter*arr[0], self.lon + meter*arr[1], feature['lat'], feature['lon'])
        py = feature['alt'] # feature['alt'] - arr[2]
        x, y, z = geom.camera_transform(px, py, pz, self.pitch, self.yaw, self.roll)
        coord = geom.project2d(x, y, z, self.focal_length)
        pixel = geom.center(coord, self.imsize)
        error += abs(pixel[0] - q[0])
        buf.append((pixel[0], pixel[1]))
        cbuf.append((q[0], q[1]))
#      for i,j in buf:
#        print i,j
#      print
#      for i,j in cbuf:
#        print i,j
      if error < best[0]:
        best[0] = min(error, best[0])
#        print best[0]/ctr
      return error/ctr
    return euclidean_error_function

  def mutate(self, args):
    return (plusminus(args[0], .5), plusminus(args[1], .5))

  def setlat(self, args, delta):
    return (args[0] + delta, args[1])

  def trysomething(self, evaluator):
    meter = 1/1e5
    evaluator((self.lat + meter * 25, self.lon + meter * -32))
#    file = open('debug', 'w')
#    for dx in range(-50, 50, 3):
#      print dx
#      for dy in range(-50, 50, 3):
#        pt = (self.lat + meter*dx, self.lon + meter*dy)
#        print >>file, dx, dy, evaluator(pt)
#    file.close()

  def man_opt(self, evaluator):
    best, best_score = self.as_array(), evaluator(self.as_array())
    closed = set()
    closed.add(best)
    pq = util_cs188.PriorityQueue()
    pq.push(best, best_score)
    iter = 0
    while not pq.isEmpty() and iter < 50:
      iter += 1
      score, x = pq.pop()
      if score < best_score:
        best = x
        best_score = score
      for i in range(5):
        candidate = self.mutate(x)
        if candidate in closed:
          continue
        closed.add(candidate)
        score = evaluator(candidate)
        pq.push(candidate, score)
    INFO("moved %f meters" % (best[0]**2 + best[1]**2)**0.5)
#    print "dx", best[0], "dy", best[1]
    meter = 1/1e5
    return (self.lat + best[0]*meter, self.lon + best[1]*meter)

  def scipy_opt(self, evaluator):
    INFO("*** SCIPY BEGIN ***")
    arr, _ = scipy.optimize.anneal(evaluator, self.as_array(), maxeval=100)
    meter = 1/1e5
    print 'final result', arr
    return (self.lat + arr[0]*meter, self.lon + arr[1]*meter)

def compute_pose(C, Q, matches, dbimgpath, dbsiftpath):
  info = os.path.join(C.infodir, os.path.basename(dbimgpath)[:-4] + '.info')
  source = render_tags.AndroidImageInfo(Q.datasource)
  model = CameraModel(source)
  return model.man_opt(model.evaluator(C.pixelmap.open(dbsiftpath), matches))

MAX_SPATIAL_ERROR = 0
def getSpatiallyOrdered(matches, axis, inliers):
  """return length of max increasing subseq"""
  indices = map(lambda (i,m): (m['db'][axis], m['query'][axis], i), filter(lambda (j,m): inliers[j], enumerate(matches)))
  if not indices:
    return inliers
  indices.sort() # by db order
  # now find subseq by query order
  L = [None]*len(indices)
  def edgesof(j):
    for i in range(j):
      if indices[i][1] <= indices[j][1] + MAX_SPATIAL_ERROR:
        yield i
  def merge((c1, l1), (c2, l2)):
    return (c1 + c2, l1 + l2)
  for j in range(len(indices)):
    E = list(edgesof(j))
    if E:
      L[j] = merge((1, [indices[j][2]]), max([L[i] for i in E]))
    else:
      L[j] = (1, [indices[j][2]])
  best = set(max(L)[1])
  for i in range(len(inliers)):
    if i not in best:
      inliers[i] = False
  return inliers

def rot_delta(m, correction=0):
  a = m['query'][3] + correction
  b = m['db'][3]
  rot = 2*np.pi
  return min((a-b) % rot, (b-a) % rot)

#matches - list of feature match pairs (dict) where each dict {'query':[x,y,scale, rot], 'db':[x,y,scale,rot]}
# if you use ransac_pass, the inliers returned will come with
#   a reduced set of matches
# data - dictionary of information to be filled
# undefined behavior in ransac case
def find_corr(matches, hom=False, ransac_pass=True, data={}):
    timer_start('ransac')
    x = real_find_corr(matches, hom, ransac_pass, data)
    timer_end('ransac')
    return x

def real_find_corr(matches, hom=False, ransac_pass=True, data={}):
  if hom:
    if ransac_pass:
      F, inliers = _find_corr(matches, MAX_PIXEL_DEVIATION=50, rotation_filter_only=True, ROT_THRESHOLD_RADIANS=30*np.pi/180)
      matches = np.compress(inliers, matches)
    return (matches,) + _find_corr(matches, hom=True, data=data, MAX_PIXEL_DEVIATION=35, FALLBACK_PIXEL_DEVIATIONS=[15, 9, 5, 3, 1])
  else:
    return _find_corr(matches, data=data)

def _find_corr(matches, hom=False, data={}, MAX_PIXEL_DEVIATION=MAX_PIXEL_DEVIATION, FALLBACK_PIXEL_DEVIATIONS=FALLBACK_PIXEL_DEVIATIONS, rotation_filter_only=False, ROT_THRESHOLD_RADIANS=ROT_THRESHOLD_RADIANS):
  data['success'] = False # by default
  matches = list(matches)
  F = cv.CreateMat(3, 3, cv.CV_64F)
  cv.SetZero(F)
  if not matches or (hom and len(matches) < 4):
    return F, []
  inliers = cv.CreateMat(1, len(matches), cv.CV_8U)
  cv.SetZero(inliers)
  pts_q = cv.CreateMat(len(matches), 1, cv.CV_64FC2)
  pts_db = cv.CreateMat(len(matches), 1, cv.CV_64FC2)
  for i, m in enumerate(matches):
    cv.Set2D(pts_q, i, 0, cv.Scalar(*m['query'][:2]))
    cv.Set2D(pts_db, i, 0, cv.Scalar(*m['db'][:2]))

# ransac for fundamental matrix. rotation filtering
# TODO multiple RANSAC to get smaller/larger features
  if not hom:
    if rotation_filter_only:
      inliers = [1]*len(matches)
    else:
      cv.FindFundamentalMat(pts_q, pts_db, F, status=inliers, param1=MAX_PIXEL_DEVIATION, param2=CONFIDENCE_LEVEL)
      inliers = np.asarray(inliers)[0]
    # assumes roll(db) == roll(query)
    for i, m in enumerate(matches):
      if inliers[i]:
        if abs(rot_delta(m, 0)) > ROT_THRESHOLD_RADIANS:
          inliers[i] = False
    return F, inliers

  # homography only. no rotation check
  cv.FindHomography(pts_db, pts_q, F, method=cv.CV_RANSAC, ransacReprojThreshold=MAX_PIXEL_DEVIATION, status=inliers)

### try rounds of homography calculations ###
  i = 0
  while i < len(FALLBACK_PIXEL_DEVIATIONS):
    if not isHomographyGood(F):
      cv.FindHomography(pts_db, pts_q, F, method=cv.CV_RANSAC, ransacReprojThreshold=FALLBACK_PIXEL_DEVIATIONS[i], status=inliers)
      i += 1
    else:
      break
  if i >= len(FALLBACK_PIXEL_DEVIATIONS):
    cv.FindHomography(pts_db, pts_q, F, method=cv.CV_LMEDS, status=inliers)
    if isHomographyGood(F):
      data['success'] = True
  else:
    data['success'] = True

  return F, np.asarray(inliers)[0]

def isHomographyGood(H):
  pts = [(384,256), (384,361), (489,256)]
  det = np.linalg.det(H)
  if det < BAD_HOMOGRAPHY_DET_THRESHOLD:
    return False
  scale = 1
  dests = []
  for (y,x) in pts:
    dest = H*np.matrix([x,y,1]).transpose()
    try:
      dest = tuple(map(int, (dest[0].item()/dest[2].item(), dest[1].item()/dest[2].item())))
    except ZeroDivisionError:
      dest = (0,0)
    except ValueError:
      dest = (0,0)
    dest = (dest[1]*scale, dest[0]*scale)
    dests.append(dest)
  v1len = np.sqrt((dests[0][0] - dests[1][0])**2 + (dests[0][1] - dests[1][1])**2)
  v2len = np.sqrt((dests[0][0] - dests[2][0])**2 + (dests[0][1] - dests[2][1])**2)
  length_ratio = v1len / v2len
  if length_ratio > 5 or 1/length_ratio > 5:
    return False
  a = (dests[1][0] - dests[0][0], dests[1][1] - dests[0][1])
  b = (dests[2][0] - dests[0][0], dests[2][1] - dests[0][1])
  aLen = (a[0]**2 + a[1]**2)**.5
  bLen = (b[0]**2 + b[1]**2)**.5
  angle_delta = np.arccos(np.dot(a, b)/(aLen*bLen))*180.0/np.pi
  if angle_delta < 30 or angle_delta > 160:
    return False
  return True

def count_unique_matches(matches):
  return len(set(map(hashmatch, matches)))

def scaledown(image, max_height):
  scale = 1.0
  hs = float(image.size[1]) / max_height
  if hs > 1:
    w,h = image.size[0]/hs, image.size[1]/hs
    scale /= hs
    image = image.resize((int(w), int(h)), Image.ANTIALIAS)
  return image, scale

def draw_matches(C, Q, matches, rsc_matches, H, inliers, db_img, out_img, matchsiftpath, showLine=True, showtag=False, showHom=False):
  k = Q.name
  v = os.path.basename(db_img)[:-4]
  known_bad = k in fail and v in fail[k]
#  print k,v
  #fail_img = os.path.join(os.path.expanduser('~/fail'), Q.name + ';' + os.path.basename(db_img))
  fail_img = os.path.join('/home/jason/Desktop/query/project/src/fail', Q.name + '_' + os.path.basename(db_img))
  if (known_bad or os.path.exists(fail_img)) and not C.drawtopcorr:
      return
  assert os.path.exists(db_img)
  a = Image.open(Q.jpgpath)
  b = Image.open(db_img)
  if a.mode != 'RGB':
    a = a.convert('RGB')
  if b.mode != 'RGB':
    b = b.convert('RGB')
  height = b.size[1]
  pgm_height = Q.pgm_scale*a.size[1]
  a, query_scale = scaledown(a, height)
  # ratio needed to convert from query pgm size -> db size
  scale = a.size[1]/pgm_height
  assert a.mode == 'RGB'
  target = Image.new('RGBA', (a.size[0] + b.size[0], height))

  def drawline(match, color='hsl(20,100%,50%)', w=3):
    db = [match['db'][1] + a.size[0], match['db'][0]]
    draw.line([match['query'][1], match['query'][0]] + db, fill=color, width=w)

  def xdrawline((start,stop), color='hsl(20,100%,50%)', off=0):
    start = [start[0] + off, start[1]]
    stop = [stop[0] + off, stop[1]]
    draw.line(start + stop, fill=color, width=8)

  def xdrawcircle((y,x), col='hsl(20,100%,50%)', off=0):
    r = 50
    draw.ellipse((y-r+off, x-r, y+r+off, x+r), outline=col)

  def drawcircle(match, col='hsl(20,100%,50%)'):
    draw.ellipse((match['query'][1] - match['query'][2], match['query'][0] - match['query'][2], match['query'][1] + match['query'][2], match['query'][0] + match['query'][2]), outline=col)
    draw.ellipse((match['db'][1] + a.size[0] - match['db'][2], match['db'][0] - match['db'][2], match['db'][1] + a.size[0] + match['db'][2], match['db'][0] + match['db'][2]), outline=col)

  draw = ImageDraw.Draw(target)

  source = render_tags.get_image_info(db_img)
  img = render_tags.TaggedImage(db_img, source, C.tags)
  if C.compute2dpose:
    elat, elon = compute_pose(C, rsc_matches, db_img, matchsiftpath)
    points = img.map_tags_camera()
    proj_points = img.map_tags_hybrid(C.pixelmap.open(db_img[:-4] + 'sift.txt'), C, elat, elon)
  else:
    proj_points = []
    points = []
    badpoints = []
#    [points, badpoints] = img.map_tags_hybrid3(C.pixelmap.open(db_img[:-4] + 'sift.txt'), C)
  H = np.matrix(np.asarray(H))
  tagmatches = []

  green = np.compress(inliers, rsc_matches).tolist()
  notred = set([hashmatch(m) for m in green])
  red = []
  for m in matches:
    if hashmatch(m) not in notred:
      red.append(m)

  for g in green:
      g['query'][0]*=scale
      g['query'][1]*=scale

  for g in red:
      g['query'][0]*=scale
      g['query'][1]*=scale

  if not proj_points:
#     transfer using H matrix
#     confusing geometry. x and y switch between the reprs.
    for (tag, (dist, pixel)) in points:
      y, x = pixel # backwards
      x2 = x+5
      dest = H*np.matrix([x,y,1]).transpose()
      dest2 = H*np.matrix([x2,y,1]).transpose()
      try:
        dest = tuple(map(int, (dest[0].item()/dest[2].item(), dest[1].item()/dest[2].item())))
        dest2 = tuple(map(int, (dest2[0].item()/dest2[2].item(), dest2[1].item()/dest2[2].item())))
      except ZeroDivisionError:
        dest = dest2 = (0,0)
      except ValueError:
        dest = dest2 = (0,0)
      tagmatches.append({'db': [x, y, 10], 'query': [dest[0], dest[1], 10]})
      correction = min(15, max(.1, abs(dest[0]-dest2[0])/5.0))
      dest = (dest[1]*scale, dest[0]*scale)
      dest2 = (dest2[1]*scale, dest2[0]*scale)
      proj_points.append((tag, (dist, dest), correction))
#  print Q.jpgpath
  target.paste(a, (0,0))
  target.paste(b, (a.size[0],0))

  def colorize(theta):
    if theta < .1:
      return 'green'
    elif theta < .2:
      return 'blue'
    elif theta < .5:
      return 'purple'
    elif theta < 1.5:
      return 'orange'
    else:
      return 'red'

  if showLine:
#      for match in red:
#        drawline(match, 'red', w=1)
#        drawcircle(match, colorize(rot_delta(match, 0)))
      for match in green:
        drawline(match, 'green', w=2)
        drawcircle(match, colorize(rot_delta(match, 0)))

  # ImageDraw :(
  corrected = not C.compute2dpose
  a2 = img.taggedcopy(proj_points, a, correction=corrected)
  b2 = img.taggedcopy(points, b)
  a = Image.new('RGBA', (a.size[0], height))
  b = Image.new('RGBA', (b.size[0], height))
  a = img.taggedcopy(proj_points, a, correction=corrected)
  b = img.taggedcopy(points, b)
  tags = Image.new('RGBA', (a.size[0] + b.size[0], height))
  tagfilled = Image.new('RGBA', (a.size[0] + b.size[0], height))
  tags.paste(a, (0,0))
  tags.paste(b, (a.size[0],0))
  tagfilled.paste(a2, (0,0))
  tagfilled.paste(b2, (a.size[0],0))
  if showtag:
    target.paste(tagfilled, mask=tags)

  if showHom:
    pts = [(384,256), (384,361), (489, 256)]
    dests = []
    for (y,x) in pts:
      dest = H*np.matrix([x,y,1]).transpose()
      try:
        dest = tuple(map(int, (dest[0].item()/dest[2].item(), dest[1].item()/dest[2].item())))
      except ZeroDivisionError:
        dest = (0,0)
      except ValueError:
        dest = (0,0)
      dest = (dest[1]*scale, dest[0]*scale)
      dests.append(dest)

    xdrawline((pts[0], pts[1]), 'violet', off=a.size[0])
    xdrawline((pts[0], pts[2]), 'yellow', off=a.size[0])
    xdrawline((dests[0], dests[1]), 'violet')
    xdrawline((dests[0], dests[2]), 'yellow')
    xdrawcircle(dests[0], 'yellow')
    xdrawcircle(pts[0], 'yellow', off=a.size[0])
    det = np.linalg.det(H)
    detstr = " det H = %s" % det
    truematch = isHomographyGood(H)
    guess = " guess = %s match" % truematch
    draw.rectangle([(0,0), (150,20)], fill='black')
    draw.text((0,0), detstr)
    draw.text((0,10), guess)

  if C.drawtopcorr:
      target.save(out_img, 'jpeg', quality=90)
  if C.log_failures and 'gtFalse' in out_img:
      target.save(fail_img, 'jpeg', quality=90)
  return H, inliers

def draw_reproj(C, Q, map2d, db_img, out_img):
    
  assert os.path.exists(db_img)
  a = Image.open(Q.jpgpath)
  if a.mode != 'RGB':
    a = a.convert('RGB')
  pgm_height = Q.pgm_scale*a.size[1]
  scale = a.size[1]/pgm_height
  assert a.mode == 'RGB'
  target = Image.new('RGBA', (a.size[0], a.size[1]))

  def xdrawline((start,stop), color='hsl(20,100%,50%)', off=0):
    start = [start[0] + off, start[1]]
    stop = [stop[0] + off, stop[1]]
    draw.line(start + stop, fill=color, width=3)

  def xdrawcircle((y,x), col='hsl(20,100%,50%)', off=0):
    r = 25
    draw.ellipse((y-r+off, x-r, y+r+off, x+r), outline=col)

  draw = ImageDraw.Draw(target)
  target.paste(a, (0,0))

  count = 0
  for m2d in map2d:
    start = np.array([0,0])
    start[1],start[0] = scale*m2d[0:2]
    stop = np.array([0,0])
    stop[1],stop[0] = scale*m2d[2:]
    xdrawcircle(start,'yellow')
    xdrawline((start,stop),'orange')
    xdrawcircle(stop,'red')
    
  
  target.save(out_img, 'jpeg', quality=90)

def draw_pairs(C, Q, matches, db_img, out_img):
  # compute pose [experimental]
#  print Q.jpgpath
#  print db_img
  assert os.path.exists(db_img)
  a = Image.open(Q.jpgpath)
  b = Image.open(db_img)
  if a.mode != 'RGB':
    a = a.convert('RGB')
  if b.mode != 'RGB':
    b = b.convert('RGB')
  height = b.size[1]
  pgm_height = Q.pgm_scale*a.size[1]
  a, query_scale = scaledown(a, height)
  # ratio needed to convert from query pgm size -> db size
  scale = a.size[1]/pgm_height
  assert a.mode == 'RGB'
  off = a.size[0]
  target = Image.new('RGBA', (a.size[0] + b.size[0], height))

  def xdrawline((start,stop), color='hsl(20,100%,50%)', off=0):
    start = [start[0] + off, start[1]]
    stop = [stop[0] + off, stop[1]]
    draw.line(start + stop, fill=color, width=1)

  def xdrawcircle((y,x), col='hsl(20,100%,50%)', off=0):
    r = 3
    draw.ellipse((y-r+off, x-r, y+r+off, x+r), outline=col)

  draw = ImageDraw.Draw(target)
  target.paste(a, (0,0))
  target.paste(b, (off,0))

  for i in range(len(matches)):
    start = np.array([0,0])
    stop = np.array([0,0])
    start[1],start[0] = scale*matches[i]['query'][0:2]
    stop[1],stop[0] = matches[i]['db'][0:2]
    stop[0] += off
    xdrawcircle(start,'yellow')
    xdrawline((start,stop),'orange')
    xdrawcircle(stop,'red')

  target.save(out_img, 'jpeg', quality=90)
