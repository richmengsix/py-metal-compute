import sys, math
from time import time as now

from PIL.Image import fromarray

import numpy as np

import metalcompute as mc

width = int(sys.argv[1])
height = int(sys.argv[2])
outname = sys.argv[3]

kernel_start = """
#include <metal_stdlib>
using namespace metal;

kernel void test(const device float *uniform [[ buffer(0) ]],
                device uchar4 *out [[ buffer(1) ]],
                uint id [[ thread_position_in_grid ]]) {
    float width = uniform[0];
    float height = uniform[1];
    float3 camera = float3(uniform[2], uniform[3], uniform[4]);
    float3 target = float3(uniform[5], uniform[6], uniform[7]);
    float2 uv = float2((id%int(width))/width, 1.0-(id/int(width))/height);
    uv -= 0.5;
    uv *= 1.0;
    // Projection
    float3 up = float3(0.0,1.0,0.0);
    float3 camdir = normalize(target - camera);
    float3 camh = normalize(cross(camdir, up));
    float3 camv = normalize(cross(camdir, camh));
    float3 raydir = normalize(uv.x*camh-uv.y*camv+camdir);
    float raylen = 0.0;
    float3 ball = target;
    float ball_radius = 0.2;
    float ball_radius_sq = ball_radius*ball_radius;
    float floory = -0.6;
    float balld=0.0, floord=0.0, neard=0.0;
    float3 pos = float3(0.0);
"""

kernel_step = """\
    pos = camera + raylen * raydir;
    balld = length_squared(fract(pos - ball)-.5)-ball_radius_sq;
    floord = pos.y - floory;        
    neard = min(balld, floord);
    raylen += neard;
"""

kernel_end = """\
    pos = camera + raylen * raydir;
    float fog = min(1.0, 4.0 / raylen);
    if (raylen > 100.0) fog = 0.0;
    float3 col = fract(pos) * fog;
    out[id] = uchar4(uchar3(col.xyz*255.),255);
}
"""

camera = [1.0,1.0,-2.0]
target = [0.0,0.9,0.0]
uniforms = np.array(
    [
        width,
        height,
        camera[0],camera[1],camera[2], 
        target[0],target[1],target[2], 
    ],
    dtype=np.float32)

image = np.zeros((height, width, 4), dtype=np.uint8)

mc.init()
reps = 300
kernel = kernel_start + kernel_step * reps + kernel_end
mc.compile(kernel, "test")
start = now()
mc.run(uniforms, image, width*height)
end = now()
print(f"Render took {end-start:1.6}s")
fromarray(image).save(outname)
mc.release()
