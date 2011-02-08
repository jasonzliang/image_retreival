import os.path
import pprint
import datetime

import os
import re
import shutil

import earthMine as em
import info
import geom

def select_dist_exceeds(map3d, mapping, dataset, results, origin3d, thresh, enum):
    out = []
    for i, dist in enum:
        image = mapping[dataset[results[i]]['index']]
        coord = dataset[results[i]]['geom']
        coord3d = map3d[results[i]]
        if coord3d['lat'] == 0 or geom.distance3d(coord3d, origin3d) > thresh:
            return dist
    return None

def countuniqimages(celldir="E:\Research\cellsg=100,r=d=236.6"):
    names = set()
    cells = getdirs(celldir)
    for cell in cells:
        cellpath=os.path.join(celldir, cell)
        jpgs = getJPGFileNames(cellpath)
        for jpg in jpgs:
            names.add(jpg)
        print len(jpgs)
    print len(cells)
    return len(names)


def countimgsinrange(querydir="E:\query3", celldir="E:\Research\cellsg=100,r=d=236.6"):
    names = set()
    jpgs = getJPGFileNames(querydir)
    counts=[]
    for img in jpgs:
        lat, lon = info.getQueryCoord(img)
        cell, dist=getclosestcell(lat, lon, celldir)
        count = getNumJPGInRange(lat, lon, os.path.join(celldir, cell), 100)
        print "{0}: {1}".format(img, count)
        counts.append(count)
    print sum(counts)/len(counts)


def getdirs(path):
    return [dir for dir in os.listdir(path) if os.path.isdir(os.path.join(path, dir))]

def getfiles(path):
    return [dir for dir in os.listdir(path) if not os.path.isdir(os.path.join(path, dir))]

def getPSLFileNames(dir):
    regex = re.compile(r'.*.psl$', re.IGNORECASE)
    return [f for f in getfiles(dir) if regex.match(f)]

def getSiftFileNames(dir):
    regex = re.compile(info.SIFTREGEXSTR, re.IGNORECASE)
    return [f for f in getfiles(dir) if regex.match(f)]

def getCHOGFileNames(dir):
    regex = re.compile(info.CHOGREGEXSTR, re.IGNORECASE)
    return [f for f in getfiles(dir) if regex.match(f)]

def getSURFFileNames(dir):
    regex = re.compile(info.SURFREGEXSTR, re.IGNORECASE)
    return [f for f in getfiles(dir) if regex.match(f)]

def getJPGFileNames(dir):
    regex = re.compile(info.IMGREGEXSTR, re.IGNORECASE)
    return [f for f in getfiles(dir) if regex.match(f)]

def removeEmptyDir(path):
    if not os.path.exists(path):
        return
    dirs = getdirs(path)
    count = 0
    for dir in dirs:
        count += 1
        p = os.path.join(path, dir)
        if not os.listdir(p):
            os.rmdir(p)
    print "removed: {0}".format(count)
    
def removeSreetFacingSIFT(path):
    if not os.path.exists(path):
        return
    dirs = getdirs(path)
    count = 0
    for dir in dirs:
        files = getSiftFileNames(os.path.join(path, dir))
        for file in files:
            angle = info.getSIFTAngle(file)
            if angle == 0 or angle == 6:
                os.remove(os.path.join(path, dir, file))
                count += 1
    print "count: {0}".format(count)

def compileGroundTruthFile(inputDir, outputFile):
    """takes in collection of query_image/acceptable_match.jpg as inputDir
    and writes groundTruth data format to outputFile"""
    all_matches = {}
    for query in os.listdir(inputDir):
        query_path = os.path.join(inputDir, query)
        matches = getJPGFileNames(query_path)
        all_matches[query[:-4]] = [match[:-4] for match in matches]
        print query
    with open(outputFile, 'w') as output:
        output.write('# generated by util.compileGroundTruthFile(%s, %s) on %s\n\n' % (inputDir, outputFile, str(datetime.datetime.today())))
        output.write('matches = ')
        pprint.pprint(all_matches, stream=output)

def getNumJPGInRange(lat, lon, inputDir, radius):
    """counts all images in inputDir within radius of given coordinate makes assumption about format of filename"""
    if os.path.exists(inputDir):
        count = 0
        files = getJPGFileNames(inputDir)
        for file in files:
            lat2, lon2 = info.getImgCoord(str(file))
            dist = info.distance(lat, lon, lat2, lon2)
            if(dist < radius):
                count+=1
        return count
    else:
        raise OSError("{p} does not exist.".format(p=inputDir))
        
def copyJPGInRange(lat, lon, inputDir, outputDir, radius):
    """puts all images in inputDir within radius of given coordinate into outputDir.
    makes assumption about format of filename"""
    if not os.path.exists(outputDir):
        try:
            os.makedirs(outputDir)
        except Exception:
            print "Error making directory...quitting..."
            return
    if os.path.exists(inputDir):
        files = getJPGFileNames(inputDir)
        for file in files:
            lat2, lon2 = info.getImgCoord(str(file))
            dist = info.distance(lat, lon, lat2, lon2)
            if(dist < radius):
                shutil.copy(os.path.join(inputDir, file), outputDir)  
    else:
        raise OSError("{p} does not exist.".format(p=inputDir))

def copyclosest(querydir="E:/Research/collected_images/query/query1/",
                inputDir="E:/Research/collected_images/earthmine-new,culled/37.871955,-122.270829/",
                outputDir="E:/Research/query1closest-r80", radius=80):

    queryfiles = getJPGFileNames(querydir)
    if  os.path.exists(outputDir):
        shutil.rmtree(outputDir)
    os.makedirs(outputDir)
    for queryfile in queryfiles:
        outdir = os.path.join(outputDir, queryfile)
        os.makedirs(outdir)
        lat, lon = info.getQueryCoord(queryfile)
        print lat, lon
        copyJPGInRange(lat, lon, inputDir, outdir, radius)

def copySIFTInRange(lat, lon, inputDir, outputDir, radius):
    """puts all sift files in inputDir within radius of given coordinate into outputDir.
    makes assumption about format of filename"""
    if not os.path.exists(outputDir):
        try:
            os.makedirs(outputDir)
        except Exception:
            print "Error making directory...quitting..."
            return
    if os.path.exists(inputDir):
        files = getSiftFileNames(inputDir)
        for file in files:
            lat2, lon2 = info.getSIFTCoord(str(file))
            dist = info.distance(lat, lon, lat2, lon2)
            if(dist < radius):
                shutil.copy(os.path.join(inputDir, file), outputDir)  
    else:
        raise OSError("{p} does not exist.".format(p=inputDir))
    
def writeCellCoordsIfInRange(path, fname, lat, lon, radius):
    if not os.path.exists(path):
        return
    dirs = getdirs(path)
    f = open(fname, "w")
    for dir in dirs:
        l = len(os.listdir(os.path.join(path, dir)))
        if l > 100:
            lat2, lon2 = dir.split(',')
            lat2 = float(lat2)
            lon2 = float(lon2)
            if distance(lat, lon, lat2, lon2) < radius:
                f.write(',' + str(l) + ',' + str(lon2) + ',' + str(lat2) + '' + '\n')
    f.close()
   
def writeCellCoords(path='/home/zhangz/shiraz/Research/cells/g=100,r=d=236.6', fname='/home/zhangz/shiraz/cells.txt'):
    """writes cell coordinates for all celldirs in path into a file fname for use in google earth"""
    if not os.path.exists(path):
        print "invalid path"
        return
    dirs = getdirs(path)
    f = open(fname, "w")
    for dir in dirs:
        lat, lon = dir.split(',')
        f.write(',' + lon + '-' + lat + ',' + lon + ',' + lat + '' + '\n')
    f.close()

def writeGridCoords(center = (37.872436,-122.272609), fname='/home/zhangz/shiraz/Research/google earth visuals/tmp.txt'):
    import querySystem
    f = open(fname, "w")
    for lat, lon in querySystem._skew_location(center, 75):
        lat = str(lat)
        lon = str(lon)
        f.write(',' + ',' + lon + ',' + lat + '' + '\n')
    f.close()

def writeQueryCoords(querydir, fname):
    """writes coordinates for all querysift in path into a file fname for use in google earth"""
    if not os.path.exists(path):
        print "invalid path"
        return
    f = open(fname, "w")
    for querysift in getSiftFileNames(querydir):
        lat, lon = info.getQuerySIFTCoord(querysift)
        lat = str(lat)
        lon = str(lon)
        f.write(',' + querysift.split(',')[0] + ',' + lon + ',' + lat + '' + '\n')
    f.close()

def writedbImgCoords(dbdir="E:/Research/collected_images/earthmine-new,culled/37.871955,-122.270829/",
                     fname = "E:/dl.txt"):
    """writes coordinates for all querysift in path into a file fname for use in google earth"""
    if not os.path.exists(dbdir):
        return
    f = open(fname, "w")
    coords = []
    files = getJPGFileNames(dbdir)
    print len(files)
    for file in files:
        coord = info.getImgCoord(file)
        if  coord not in coords:
            coords.append(coord)
    for lat, lon in coords:
        f.write(', ,' + str(lon) + ',' + str(lat) + '' + '\n')
    f.close()

		
def generateCellCoords(lat, lon, len, distance):
#takes lat long as upper left corner and length as distance to go right and down 150degrees
#distance is distance between cells
    coords = []
    candlat1 = lat
    candlon1 = lon
    while(info.distance(lat, lon, candlat1, candlon1) < len):
        candlat2, candlon2 = candlat1, candlon1
        while(info.distance(candlat1, candlon1, candlat2, candlon2) < len):
            coords.append((candlat2, candlon2))
            candlat2, candlon2 = em.moveLocation4(candlat2, candlon2, distance, 90)
        candlat1, candlon1 = em.moveLocation4(candlat1, candlon1, distance, 150)
    return coords
    
def makecellsgivenspots(spots, inputDir="E:\\Research\\collected_images\\earthmine-new,culled\\37.871955,-122.270829", radius=236.6, outputDir='E:\\Research\\newcells\\'):
    print "creating {0} cells from {1}".format(len(spots), inputDir)
    for spot in spots:
        spotstr = str(spot[0]) + ',' + str(spot[1]);
        if not os.path.exists(outputDir + spotstr):
            print "Moving spot:" + spotstr
            copyJPGInRange(spot[0], spot[1], inputDir, outputDir + spotstr, radius)
            copySIFTInRange(spot[0], spot[1], inputDir, outputDir + spotstr, radius)
            if not os.listdir(outputDir + spotstr):
                print "spot empty"
                os.rmdir(outputDir + spotstr)
            
def makecells(lat=37.875134477254974, lon=-122.27778058982598, length=1000, inputDir="E:\\Research\\collected_images\\earthmine-new,culled\\37.871955,-122.270829", distance=236.60254, radius=236.60254, outputDir='E:\\Research\\newcells\\'):
    spots = generateCellCoords(lat, lon, length, distance)
    print "spots:{0} ".format(len(spots))
    makecellsgivenspots(spots, inputDir, radius, outputDir)

# def writeCellCoords(lat, lon, length, fname):
    # spots = generateCellCoords(lat, lon, length)
    # f = open(fname, "w")
    # for lat, lon in spots:
        ##f.write(str(lat)+'|'+str(lon)+'\n')
        # f.write(',,' + str(lon) + ',' + str(lat) + '' + '\n')
    # f.close()

dircache = {} # assume invariant across run
def getclosestcells(lat, lon, celldir):
    if celldir in dircache:
        dirs = dircache[celldir]
    else:
        if not os.path.exists(celldir):
            print "ERR: celldir does not exist: {0}".format(celldir)
            return []
        dirs = dircache[celldir] = getdirs(celldir)
    closest_cells = []
    for dir in dirs:
        lat2, lon2 = dir.split(',')
        lat2 = float(lat2)
        lon2 = float(lon2)
        dist = info.distance(lat, lon, lat2, lon2)
        closest_cells.append((dir, dist))
    closest_cells.sort(key=lambda x: x[1])
    return closest_cells

def getfurthestcell(lat, lon, celldir):
    return os.path.join(celldir, getclosestcells(lat, lon, celldir)[-1][0])

def printclosestcells(lat, lon, celldir="/media/data/Research/cellsg=50,r=100,d=86.6"):
    for cell in getclosestcells(lat, lon, celldir):
        print cell

def getclosestcell(lat, lon, celldir):
    if not os.path.exists(celldir):
        return
    dirs = getdirs(celldir)
    closest_dist = float('inf')
    closest_cell = ''
    for dir in dirs:
        lat2, lon2 = dir.split(',')
        lat2 = float(lat2)
        lon2 = float(lon2)
        dist = info.distance(lat, lon, lat2, lon2)
        if  dist < closest_dist:
            closest_dist = dist
            closest_cell = dir
    return closest_cell, closest_dist
    
def getAvgNumImgsInCell(cellsdirpath="E:\Research\cellsg=100,r=d=236.6"):
    if os.path.exists(cellsdirpath):
        count = 0
        cells = getdirs(cellsdirpath)
        for cell in cells:
            num = len(getSiftFileNames(os.path.join(cellsdirpath, cell)))
            count += num
            print cell, num
        return count / len(cells)
    else:
        raise OSError("{p} does not exist.".format(p=celldirpath))
        
        
def getAvgNumFeaturesInCell(cellsdirpath="E:\Research\cellsg=50,r=100,d=86.6"):
    if os.path.exists(cellsdirpath):
        feats = 0
        cells = getdirs(cellsdirpath)
        for cell in cells:
            feats += getNumFeaturesInCell(os.path.join(cellsdirpath, cell))
        return feats / len(cells)
    else:
        raise OSError("{p} does not exist.".format(p=celldirpath))
        
def getNumFeaturesInCell(celldirpath="E:\Research\cellsg=50,r=100,d=86.6\\37.869064249,-122.267457673"):
    if os.path.exists(celldirpath):
        feats = 0
        for file in getSiftFileNames(celldirpath):
            f = open(os.path.join(celldirpath, file), 'r')
            (numfeats, dim) = f.readline().split()
            feats += int(numfeats)
            f.close()
        return feats
    else:
        raise OSError("{p} does not exist.".format(p=celldirpath))
    

#def printclosestcells(lat, lon, celldir, radius=150):
#    if not os.path.exists(celldir):
#        return
#    dirs = getdirs(celldir)
#    for dir in dirs:
#        lat2, lon2 = dir.split(',')
#        lat2 = float(lat2)
#        lon2 = float(lon2)
#        #dirpath = os.path.join(celldir, dir)
#        #d=os.path.join(dirpath, "doneDatabase10_5.2.bin")
#        if  info.distance(lat, lon, lat2, lon2) < radius: #and os.path.exists(d):
#            print "{0},\t distance: {1}".format(dir, info.distance(lat, lon, lat2, lon2))

import groundtruthG
import groundtruthY
import groundtruthR
import groundtruthB
import groundtruthO
import query1Groundtruth
import query2Groundtruth
def python_to_matlab_groundTruth(d, fname):
    f = open(fname,"w")
    for key in d:
        if d[key]:
            f.write( "{0}\n{1}\n".format(key, '\n'.join(d[key])))
        else:
            f.write( "{0}\n".format(key))
#python_to_matlab_groundTruth(groundtruthG.matches, "gt3G")
#python_to_matlab_groundTruth(groundtruthY.matches, "gt3Y")
#python_to_matlab_groundTruth(groundtruthR.matches, "gt3R")
#python_to_matlab_groundTruth(groundtruthB.matches, "gt3B")
#python_to_matlab_groundTruth(groundtruthO.matches, "gt3O")
#python_to_matlab_groundTruth(query1Groundtruth.matches, "gt1")
#python_to_matlab_groundTruth(query2Groundtruth.matches, "gt2")

#def dupCount(file):
#    counter = {}
#    file = open(file)
#    lines = []
#    for line in file:
#        lines.append(line)
#    lines.sort(key=lambda x: float(x.split(' ')[0].split(',')[-1]))
#    for line in lines[0:4]:
#        for img in line.split(' ')[1:6]:
#            if img in counter:
#                counter[img] += 1
#            else:
#                counter[img] = 1
#    return counter
