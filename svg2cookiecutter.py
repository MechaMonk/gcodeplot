import sys
import svgpath.parser as parser

PRELIM = """// OpenSCAD file automatically generated by svg2cookiercutter.py
wallHeight = 12;
minWallThickness = 2;
maxWallThickness = 3;
minInsideWallThickness = 1;
maxInsideWallThickness = 3;

wallFlareWidth = 5;
wallFlareThickness = 3;
insideWallFlareWidth = 5;
insideWallFlareThickness = 3;

featureHeight = 8;
minFeatureThickness = 0.8;
maxFeatureThickness = 3;

connectorThickness = 1;
cuttingEdgeThickness = 1;

size = $OVERALL_SIZE$;

scale = size/$OVERALL_SIZE$;

module ribbon(points, thickness=1) {
    union() {
        for (i=[1:len(points)-1]) {
            hull() {
                translate(points[i-1]) circle(d=thickness, $fn=8);
                translate(points[i]) circle(d=thickness, $fn=8);
            }
        }
    }
}

module wall(path,height,thickness) {
  render(convexity=10) minkowski() {
    linear_extrude(height=.1) ribbon(path,thickness=.01);
    cylinder(h=height,d1=thickness,d2=cuttingEdgeThickness,$fn=4);
  }
  // faster but less sharp edges:
  // render(convexity=10) linear_extrude(height=height) ribbon(path,thickness=thickness);
}



module outerFlare(path) {
  difference() {
    render(convexity=10) linear_extrude(height=wallFlareThickness) ribbon(path,thickness=wallFlareWidth);
    translate([0,0,-0.01]) linear_extrude(height=wallFlareThickness+0.02) polygon(points=path);
  }
}

module innerFlare(path) {
  intersection() {
    render(convexity=10) linear_extrude(height=insideWallFlareThickness) ribbon(path,thickness=insideWallFlareWidth);
    translate([0,0,-0.01]) linear_extrude(height=insideWallFlareThickness+0.02) polygon(points=path);
  }
}

module connector(path) {
  render(convexity=10) linear_extrude(height=connectorThickness) polygon(points=path);
}

module cookieCutter() {
"""

class Line(object):
    def __init__(self, height="featureHeight", width="0.5", base=False, wall=False, insideWall=False, stroke=False):
        self.height = height
        self.width = width
        self.base = base
        self.wall = wall
        self.insideWall = insideWall
        self.stroke = stroke
        self.points = []
        
    def toCode(self, pathCount):
        code = []
        path = 'path'+str(pathCount)
        code.append( path + '=scale*[' + ','.join(('[%.3f,%.3f]'%tuple(p) for p in self.points)) + '];' );
        if self.stroke:
            code.append('wall('+path+','+self.height+','+self.width+');')
            if self.wall:
                code.append('outerFlare('+path+');')
            elif self.insideWall:
                code.append('innerFlare('+path+');')
        if self.base:
            code.append('connector('+path+');')
        code.append('') # will add a newline
        return code
        
def isRed(rgb):
    return rgb is not None and rgb[0] >= 0.4 and rgb[1]+rgb[2] < rgb[0] * 0.25

def isGreen(rgb):
    return rgb is not None and rgb[1] >= 0.4 and rgb[0]+rgb[2] < rgb[1] * 0.25

def svgToCookieCutter(filename, tolerance=0.1, strokeAll = False):
    code = [PRELIM]
    pathCount = 0;
    minXY = [float("inf"), float("inf")]
    maxXY = [float("-inf"), float("-inf")]
    
    for superpath in parser.getPathsFromSVGFile(filename)[0]:
        for path in superpath.breakup():
            line = Line()
            
            line.base = False
            line.stroke = False
            
            if path.svgState.fill is not None:
                line.base = True

            if strokeAll or path.svgState.stroke is not None:
                line.stroke = True
                if isRed(path.svgState.stroke):
                    line.width = "min(maxWallThickness,max(%.3f,minWallThickness))" % path.svgState.strokeWidth
                    line.height = "wallHeight"
                    line.wall = True
                elif isGreen(path.svgState.stroke):
                    line.width = "min(maxInsideWallThickness,max(%.3f,minInsideWallThickness))" % path.svgState.strokeWidth
                    line.height = "wallHeight"
                    line.insideWall = True
                else:
                    line.width = "min(maxFeatureThickness,max(%.3f,minFeatureThickness))" % path.svgState.strokeWidth
                    line.height = "featureHeight"
                    line.wall = False
            elif not line.base:
                continue
                
            lines = path.linearApproximation(error=tolerance)
            
            line.points = [(-l.start.real,l.start.imag) for l in lines]
            line.points.append((-lines[-1].end.real, lines[-1].end.imag))
            
            for i in range(2):
                minXY[i] = min(minXY[i], min(p[i] for p in line.points))
                maxXY[i] = max(maxXY[i], max(p[i] for p in line.points))
                
            code += line.toCode(pathCount)
            pathCount += 1

    size = max(maxXY[0]-minXY[0], maxXY[1]-minXY[1])
    
    code.append('}\n')
    code.append('translate([%.3f*scale + wallFlareWidth/2,  %.3f*scale + wallFlareWidth/2,0]) cookieCutter();' % (-minXY[0],-minXY[1]))
            
    return '\n'.join(code).replace('$OVERALL_SIZE$', '%.3f' % size)
    
if __name__ == '__main__':
    print(svgToCookieCutter(sys.argv[1]))
    
