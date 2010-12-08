import os
import re
import shutil

import earthMine as em
import info

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

def copyclosest(querydir="E:/Research/collected_images/query/query2/",
                inputDir="E:/Research/collected_images/earthmine-new,culled/37.871955,-122.270829/",
                outputDir="E:/Research/query2closest-r120", radius=120):

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
   
def writeCellCoords(path, fname):
    """writes cell coordinates for all celldirs in path into a file fname for use in google earth"""
    if not os.path.exists(path):
        return
    dirs = getdirs(path)
    f = open(fname, "w")
    for dir in dirs:
        lat, lon = dir.split(',')
        f.write(',' + lon + '-' + lat + ',' + lon + ',' + lat + '' + '\n')
    f.close()
    

def writeQueryCoords(querydir, fname):
    """writes coordinates for all querysift in path into a file fname for use in google earth"""
    if not os.path.exists(querydir):
        return
    f = open(fname, "w")
    for querysift in getSiftFileNames(querydir):
        lat, lon = info.getQuerySIFTCoord(querysift)
        lat = str(lat)
        lon = str(lon)
        f.write(',' + querysift.split(',')[0] + ',' + lon + ',' + lat + '' + '\n')

def writedbImgCoords(dbdir="/home/zhangz/.gvfs/data on 128.32.43.40/Research/collected_images/earthmine-new,culled/37.871955,-122.270829/",
                     fname = "/media/data/lst"):
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
    for lon, lat in coords:
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
    
def makecellsgivenspots(spots, inputDir, radius, outputDir='X:\\Research\\newcells\\'):
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

def getclosestcells(lat, lon, celldir):
    if not os.path.exists(celldir):
        print "ERR: celldir does not exist: {0}".format(celldir)
        return []
    dirs = getdirs(celldir)
    closest_cells = []
    for dir in dirs:
        lat2, lon2 = dir.split(',')
        lat2 = float(lat2)
        lon2 = float(lon2)
        dist = info.distance(lat, lon, lat2, lon2)
        closest_cells.append((dir, dist))
    closest_cells.sort(key=lambda x: x[1])
    return closest_cells

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
    
def getAvgNumImgsInCell(cellsdirpath="E:\Research\cellsg=50,r=100,d=86.6"):
    if os.path.exists(cellsdirpath):
        count = 0
        cells = getdirs(cellsdirpath)
        for cell in cells:
            count += len(getSiftFileNames(os.path.join(cellsdirpath, cell)))
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

#import groundtruthG
#import groundtruthY
#import groundtruthR
#import groundtruthB
#import groundtruthO
#def pythonToMatlabGroundTruth(d, fname):
#    f = open(fname,"w")
#    for key in d:
#        f.write( "{0}\t{1}\n".format(key, d[key]))
#pythonToMatlabGroundTruth(groundtruthG.matches, "gtG")
#pythonToMatlabGroundTruth(groundtruthY.matches, "gtY")
#pythonToMatlabGroundTruth(groundtruthR.matches, "gtR")
#pythonToMatlabGroundTruth(groundtruthB.matches, "gtB")
#pythonToMatlabGroundTruth(groundtruthO.matches, "gtO")

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

##BEGIN VOCABTREE STUFF
#import queryDatabase as qD
#import vTreeBuild
#import vocabularyTree

#def examine(file):
#    file = os.path.join("H:\\results2", file)
#    copy_results("C:\\37.87070,-122.27160,500\\37.8707,-122.2716\\jpg", "C:\\matches", file)
#    copyResultPGMs("C:\\37.87070,-122.27160,500\\37.8707,-122.2716\\pgm", "C:\\matchPGMs", file)
#    for line in dupCount(file).items():
#        print line

# def writeBuiltDBCoords(path, fname):
    # """writes cell coordinates for all celldirs in path with built vocabtree databases into a file fname for use in google earth"""
    # if not os.path.exists(path):
        # return
    # dirs = os.listdir(path)
    # dirs = [ dir for dir in dirs if os.path.isdir(os.path.join(path,dir))]
    # f = open(fname,"w")
    # for dir in dirs:
        # lat, lon = dir.split(',')
        # dirpath = os.path.join(path, dir)
        # d=os.path.join(dirpath, "doneDatabase10_5.2.bin")
        # if os.path.exists(d):
            # f.write(','+lon+'-'+lat+','+lon+','+lat+''+'\n')
    # f.close()

#def writeResultCoords(path, fname):
#    if not os.path.exists(path):
#        return
#    results = os.listdir(path)
#    f = open(fname, "w")
#    for res in results:
#        lat, lon = res.split(',')[1:3]
#        lon = lon[0:-4]
#        f.write(',,' + lon + ',' + lat + '' + '\n')
#    f.close()

#def copy_results(imgdir, outdir, file):
#    shutil.rmtree(outdir)
#    os.makedirs(outdir)
#    file = open(file)
#    lines = []
#    for line in file:
#        lines.append(line)
#    lines.sort(key=lambda x: float(x.split(' ')[0].split(',')[-1]))
#    c1 = 1
#    for line in lines[0:4]:
#        c2 = 1
#        for img in line.split(' ')[1:6]:
#            shutil.copy(os.path.join(imgdir, ('%s.jpg' % img)), os.path.join(outdir, '%s-%s-%s.jpg' % (c1, c2, img)))
#            c2 += 1
#        c1 += 1
#def copyResultPGMs(imgdir, outdir, file):
#    shutil.rmtree(outdir)
#    os.makedirs(outdir)
#    file = open(file)
#    lines = []
#    for line in file:
#        lines.append(line)
#    lines.sort(key=lambda x: float(x.split(' ')[0].split(',')[-1]))
#    for line in lines[0:4]:
#        for img in line.split(' ')[1:6]:
#            shutil.copy(os.path.join(imgdir, ('%s.pgm' % img)), outdir)
#def copyResultSIFTs(imgdir, outdir, file):
#    file = open(file)
#    lines = []
#    for line in file:
#        lines.append(line)
#    lines.sort(key=lambda x: float(x.split(' ')[0].split(',')[-1]))
#    for line in lines[0:4]:
#        for img in line.split(' ')[1:6]:
#            shutil.copy(os.path.join(imgdir, ('%ssift.txt' % img)), outdir)

#def query(lat, lon, celldir, imgPath, radius=150):
#    if not os.path.exists(celldir):
#        return
#    dirs = [ dir for dir in os.listdir(celldir) if os.path.isdir(os.path.join(celldir,dir))]
#    for dir in dirs:
#        lat2, lon2 = dir.split(',')
#        lat2 = float(lat2)
#        lon2 = float(lon2)
#        dirpath = os.path.join(celldir, dir)
#        d=os.path.join(dirpath, "doneDatabase10_5.2.bin")
#        if  info.distance(lat,lon,lat2,lon2) < radius and os.path.exists(d):
#            print "querying{0}".format(dir)
#            qD.queryTree(d, imgPath, os.path.join("C:\\results\\", dir), numresults=10)

#def queryTrees(celldir, qPath, outdir, radius=150, numresults=10):
#    regex = re.compile(r'.*sift.txt$', re.IGNORECASE)
#    files = [f for f in os.listdir(qPath) if regex.match(f)]
#    files.sort()
#    dirs = [ dir for dir in os.listdir(celldir) if os.path.isdir(os.path.join(celldir,dir))]
#    for file in files:
#        outfile = os.path.join(outdir, "%s.txt" % file[0:-8])
#        print outfile
#        if not os.path.exists(outfile):
#            print "checking query: {0}".format(file)
#            lat, lon = info.getQuerySIFTCoord(file)
#            feats = vocabularyTree.readonefileSIFT(os.path.join(qPath,file))
#            r=[]
#            toQuery=[]
#            for dir in dirs:
#                lat2, lon2 = info.getCellCoord(dir)
#                dirpath = os.path.join(celldir, dir)
#                dbpath = os.path.join(dirpath, "doneDatabase10_5.2.bin")
#                dist = info.distance(lat,lon,lat2,lon2)
#                if  dist < radius and os.path.exists(dbpath):
#                    toQuery.append([dir, dist])
#            toQuery.sort(key = lambda x : x[1])
#            for pair in toQuery[0:4]:
#                dir = pair[0]
#                dist = pair[1]
#                dirpath = os.path.join(celldir, dir)
#                dbpath = os.path.join(dirpath, "doneDatabase10_5.2.bin")
#                print "Loading database: {0}".format(dbpath)
#                d = vocabularyTree.Database(None)
#                d.fromFile(dbpath)
#                print "querying"
#                results = d.queryn(feats, numresults)
#                results.reverse()
#                r.append(" ".join(["%(dir)s,%(dist)s" % locals()] + map(lambda x: str(x[0]),results)))
#                del d
#            print "writing output: {0}".format(file)
#            of = open(outfile,'w')
#            for result in r:
#                of.write(result)
#                of.write("\n")
#            of.close()

##END VOCABTREE STUFF
