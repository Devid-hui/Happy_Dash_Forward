// Independent 4096x4096 strict-interior pixel coverage/overlap measurement.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <vector>

double orient(double ax,double ay,double bx,double by,double px,double py) {
    return (bx-ax)*(py-ay)-(by-ay)*(px-ax);
}
int main(int argc,char**argv) {
    if(argc!=3)return 2;
    std::ifstream input(argv[1],std::ios::binary|std::ios::ate);
    const auto length=input.tellg();input.seekg(0);
    if(length<0||length%24)return 3;
    std::vector<float> uv(static_cast<size_t>(length)/4);input.read(reinterpret_cast<char*>(uv.data()),length);
    constexpr int resolution=4096;
    std::vector<int32_t> owner(resolution*resolution,-1);
    uint64_t overlaps=0,covered=0,degenerate=0,valid=0;
    for(size_t i=0;i<uv.size()/6;i++) {
        double x[3],y[3];
        for(int j=0;j<3;j++){x[j]=uv[i*6+j*2]*resolution;y[j]=uv[i*6+j*2+1]*resolution;}
        double area=orient(x[0],y[0],x[1],y[1],x[2],y[2]);
        if(std::abs(area)<1e-14){degenerate++;continue;}valid++;
        const int lowx=std::max(0,(int)std::ceil(std::min({x[0],x[1],x[2]})-.5));
        const int highx=std::min(resolution-1,(int)std::floor(std::max({x[0],x[1],x[2]})-.5));
        const int lowy=std::max(0,(int)std::ceil(std::min({y[0],y[1],y[2]})-.5));
        const int highy=std::min(resolution-1,(int)std::floor(std::max({y[0],y[1],y[2]})-.5));
        const double sign=area>0?1:-1,epsilon=std::abs(area)*1e-8;
        for(int yy=lowy;yy<=highy;yy++)for(int xx=lowx;xx<=highx;xx++) {
            const double px=xx+.5,py=yy+.5;
            if(orient(x[0],y[0],x[1],y[1],px,py)*sign<=epsilon||orient(x[1],y[1],x[2],y[2],px,py)*sign<=epsilon||orient(x[2],y[2],x[0],y[0],px,py)*sign<=epsilon)continue;
            auto &previous=owner[yy*resolution+xx];
            if(previous>=0&&previous!=(int32_t)i)overlaps++;
            else if(previous<0){previous=(int32_t)i;covered++;}
        }
    }
    std::ofstream output(argv[2],std::ios::binary);output.write(reinterpret_cast<char*>(owner.data()),owner.size()*4);
    std::cout<<"{\"resolution\":4096,\"triangles\":"<<uv.size()/6<<",\"valid_uv_triangles\":"<<valid<<",\"degenerate_uv_triangles\":"<<degenerate<<",\"strict_interior_covered_pixels\":"<<covered<<",\"overlapping_pixel_writes\":"<<overlaps<<",\"coverage_fraction\":"<<(double)covered/(resolution*resolution)<<",\"scope\":\"Independent strict pixel-center triangle interiors; shared borders excluded. Does not exclude subpixel overlaps.\"}\n";
}
