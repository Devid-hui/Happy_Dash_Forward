"""Continuous sleeve sections from measured CC0 hm08 arm cross sections.

This module changes neither limb centreline nor skeleton. Distances are metres;
sample(s) travels from the existing wrist/cuff to the shoulder. The reference
fractions travel in the opposite direction (shoulder -> elbow -> wrist).
"""
import bisect
import math


def _slopes(x, y):
    """C1 cubic slopes limited per interval to prevent overshoot."""
    secants = [(b-a)/(v-u) for u,v,a,b in zip(x,x[1:],y,y[1:])]
    slopes = [0.0] * len(x)
    for i in range(1, len(x)-1):
        a, b = secants[i-1], secants[i]
        if a*b > 0:
            slopes[i] = 2*a*b/(a+b)
    # Equal endpoint slopes flatten the cuff and shoulder boundaries. The
    # Fritsch-Carlson interval limit is a sufficient monotonicity constraint.
    for i, secant in enumerate(secants):
        if abs(secant) < 1e-14:
            slopes[i] = slopes[i+1] = 0.0
            continue
        a, b = slopes[i]/secant, slopes[i+1]/secant
        if a < 0:
            slopes[i] = 0.0
            a = 0.0
        if b < 0:
            slopes[i+1] = 0.0
            b = 0.0
        magnitude = math.hypot(a,b)
        if magnitude > 3.0:
            scale = 3.0/magnitude
            slopes[i] *= scale
            slopes[i+1] *= scale
    return slopes


class SleeveProfile:
    def __init__(self, stations, radii, reference_sha, elbow_arc, length, cuff_length):
        self.stations = tuple(stations)
        self.radii = tuple(tuple(pair) for pair in radii)
        self.slopes = tuple(tuple(_slopes(self.stations, [r[axis] for r in self.radii])) for axis in (0,1))
        self.reference_sha = reference_sha
        self.elbow_arc = elbow_arc
        self.length = length
        self.cuff_length = cuff_length

    def _interval(self, s):
        s = min(self.length,max(0.0,float(s)))
        i = max(0,min(len(self.stations)-2,bisect.bisect_right(self.stations,s)-1))
        span = self.stations[i+1]-self.stations[i]
        return i,span,(s-self.stations[i])/span

    def sample(self, s):
        """Return (width_radius, depth_radius) with no per-call file IO."""
        i,h,t = self._interval(s)
        a = 2*t*t*t-3*t*t+1
        b = t*t*t-2*t*t+t
        c = -2*t*t*t+3*t*t
        d = t*t*t-t*t
        return tuple(a*self.radii[i][k]+b*h*self.slopes[k][i]+c*self.radii[i+1][k]+d*h*self.slopes[k][i+1] for k in (0,1))

    def derivative(self, s):
        """Radius derivative with respect to metres along the sleeve."""
        i,h,t = self._interval(s)
        return tuple(((6*t*t-6*t)*self.radii[i][k]+(-6*t*t+6*t)*self.radii[i+1][k])/h+(3*t*t-4*t+1)*self.slopes[k][i]+(3*t*t-2*t)*self.slopes[k][i+1] for k in (0,1))

    def receipt(self):
        return {
            'version':1,
            'reference_sha256':self.reference_sha,
            'method':'One C1 shape-preserving cubic across both measured limb regions; fixed existing cuff; 3 mm cloth allowance per side',
            'elbow_arc_m':self.elbow_arc,
            'length_m':self.length,
            'cuff_preserved_length_m':self.cuff_length,
            'stations_m':list(self.stations),
            'width_depth_radii_m':[list(p) for p in self.radii],
            'centreline_changed':False,
            'left_right_anatomical_scaling':1.0,
        }


def make_sleeve_profile(reference, elbow_arc, length, cuff_radii=None):
    """Build once before the ring loop; then call profile.sample(arc[i]).

    reference is the parsed HM08_ARM_SECTION_REFERENCE.json. cuff_radii should
    be the caller's *existing* width/depth radii, preserving the wrist opening.
    Omitting it uses the reference's distal forearm plus 3 mm clothing allowance.
    Both sides deliberately share the same anatomy instead of arbitrary waves.
    """
    elbow_arc, length = float(elbow_arc), float(length)
    if not (0.08 < elbow_arc < length-0.08):
        raise ValueError('both sleeve limb regions must be longer than 80 mm')
    measured = []
    for region in ('fore','upper'):
        for row in reference['profiles'][region]['samples']:
            fraction = float(row['fraction'])
            s = (1-fraction)*elbow_arc if region=='fore' else elbow_arc+(1-fraction)*(length-elbow_arc)
            radii = (float(row['width_mm'])*.0005+.003,float(row['depth_mm'])*.0005+.003)
            measured.append((s,radii))
    measured.sort()
    if cuff_radii is None:
        cuff_radii = measured[0][1]
    cuff_radii = tuple(float(value) for value in cuff_radii)
    if len(cuff_radii)!=2 or any(not (.015 <= value <= .04) for value in cuff_radii):
        raise ValueError('cuff radii must be two realistic existing metre radii')
    # The initial 25 mm stays attached to the original cuff. Use at least a
    # further 20 mm before the first measured full-body section, so the left
    # cuff can meet the shared anatomy without a 5–10 mm bulge at its edge.
    cuff_length = .025
    first_body = .045
    def linear_reference(s):
        for (a,ra),(b,rb) in zip(measured,measured[1:]):
            if a<=s<=b:
                t=(s-a)/(b-a)
                return tuple(u+(v-u)*t for u,v in zip(ra,rb))
        return measured[0][1] if s<measured[0][0] else measured[-1][1]
    anchors = [(0.0,cuff_radii),(cuff_length,cuff_radii),(first_body,linear_reference(first_body))]
    anchors.extend((s,radii) for s,radii in measured if s>first_body+1e-8)
    # One interpolant bridges the former fore/upper branch boundary. This
    # avoids a radius jump or slope reset exactly at the elbow.
    anchors.append((elbow_arc,linear_reference(elbow_arc)))
    anchors.append((length,measured[-1][1]))
    anchors.sort()
    return SleeveProfile([s for s,_ in anchors],[r for _,r in anchors],reference['source_obj_sha256'],elbow_arc,length,cuff_length)
