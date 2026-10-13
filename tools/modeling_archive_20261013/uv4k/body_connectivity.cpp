// Read-only topology components; source vertex/face indices are never changed.
#include <cstdint>
#include <fstream>
#include <vector>
#include <iostream>
#include <numeric>
#include <algorithm>
int main(int argc,char**argv){
    if(argc!=4)return 2;
    const uint32_t vertices=std::stoul(argv[2]);
    std::ifstream in(argv[1],std::ios::binary|std::ios::ate);
    const auto bytes=in.tellg();in.seekg(0);if(bytes<0||bytes%12)return 3;
    std::vector<uint32_t> faces(static_cast<size_t>(bytes)/4);
    in.read(reinterpret_cast<char*>(faces.data()),bytes);
    std::vector<uint32_t> parent(vertices),rank(vertices,0);
    std::vector<uint8_t> used(vertices,0);std::iota(parent.begin(),parent.end(),0);
    auto find=[&](uint32_t x){while(parent[x]!=x){parent[x]=parent[parent[x]];x=parent[x];}return x;};
    auto join=[&](uint32_t x,uint32_t y){x=find(x);y=find(y);if(x==y)return;if(rank[x]<rank[y])std::swap(x,y);parent[y]=x;if(rank[x]==rank[y])rank[x]++;};
    for(size_t i=0;i<faces.size();i+=3){
        const auto a=faces[i],b=faces[i+1],c=faces[i+2];
        if(std::max({a,b,c})>=vertices)return 4;
        used[a]=used[b]=used[c]=1;join(a,b);join(a,c);
    }
    uint32_t components=0,referenced=0;
    for(uint32_t i=0;i<vertices;i++){
        parent[i]=find(i);if(used[i]){referenced++;if(parent[i]==i)components++;}
        else parent[i]=UINT32_MAX;
    }
    std::ofstream out(argv[3],std::ios::binary);out.write(reinterpret_cast<char*>(parent.data()),vertices*4);
    std::cout<<"{\"vertices\":"<<vertices<<",\"triangles\":"<<faces.size()/3<<",\"referenced_vertices\":"<<referenced<<",\"unreferenced_vertices\":"<<vertices-referenced<<",\"topological_components\":"<<components<<",\"scope\":\"Exact shared-index connectivity; does not weld coincident positions or edit geometry\"}\n";
}
