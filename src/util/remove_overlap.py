import math

from chimerax.surface._surface import enclosed_volume
import numpy as np
from chimerax.geometry._geometry import closest_triangle_intercept


def calc_overlap(scm, p1, p2):
    # Returns the enclosed volume

    # Get all vertices that are in the other particle
    p1_origin = p1.full_transform().origin()
    p2_origin = p2.full_transform().origin()
    vs1, ts = scm.vertices + p1_origin, scm.triangles
    vs2 = scm.vertices + p2_origin

    bounds = scm.bounds()
    p2_bounds = bounds.xyz_min + p2_origin, bounds.xyz_max + p2_origin
    p2_size = p2_bounds[1] - p2_bounds[0]
    v1s_in_v2 = [False]*len(vs1)
    for i, v in enumerate(vs1):
        from_v_to_o = p1_origin - v  # normalize too
        end = v + from_v_to_o*max(p2_size)
        dist, tnum = closest_triangle_intercept(vs2, ts, v, end)
        if dist is None:
            v1s_in_v2[i] = True


def calculate_overlap(pl, num_total_pts, method='monte carlo'):
    import time
    ps = [pl.get_particle(cid) for cid in pl.particle_ids]
    scm = pl.collection_model.collections['surfaces']
    vertices, triangles = scm.vertices, scm.triangles

    # Kind of unnecessary but maybe small speedup
    surface_bounds = pl.display_model.get(0).surfaces[0].geometry_bounds()
    bounds_size = surface_bounds.size()
    bbox_vol = bounds_size[0] * bounds_size[1] * bounds_size[2]
    if method == 'monte carlo':
        generate_pts = generate_random_pts
    elif method == 'poisson':
        generate_pts = generate_poisson_disc_pts
    elif method == 'regular grid':
        generate_pts = generate_regular_grid_pts
    else:
        print("UNKNOWN METHOD")
        return

    for i, p in enumerate(ps[:-1]):
        # Generate points in the bounding box of p here
        t0 = time.time()
        xyz_min, xyz_max = np.array(surface_bounds.xyz_min + p.coord), np.array(surface_bounds.xyz_max + p.coord)
        pts = generate_pts(num_total_pts, xyz_min, xyz_max)
        print("NUM PTS: ", len(pts))
        p_verts = vertices + p.coord
        t1 = time.time()
        pts_in_p1 = [pt for pt in pts if is_point_in_surface(pt, p_verts, triangles, xyz_min, xyz_max)]
        print("ESTIMATED SIZE OF P: ", bbox_vol * len(pts_in_p1)/len(pts))
        t2 = time.time()
        print("NUM PTS IN P", len(pts_in_p1))
        for other_p in ps[i + 1:]:
            # Figure out which of those points are also in other_p
            p_verts = vertices + other_p.coord
            pts_in_both = [pt for pt in pts_in_p1 if is_point_in_surface(pt, p_verts, triangles, xyz_min, xyz_max)]
            print("NUM PTS IN BOTH", len(pts_in_both))

            overlap_vol = bbox_vol * len(pts_in_both) / len(pts)
            print("OVERLAP BETWEEN: ", p, other_p, overlap_vol)
        t3 = time.time()
        print("Time taken to generate points: ", t1 - t0)
        print("Time taken to figure out the number of points in p1: ", t2 - t1)
        print("Time taken to figure out the number of points in all other particles: ", t3 - t2)
        print("Time taken in total: ", t3 - t0)


def generate_random_pts(num_total_pts, xyz_min, xyz_max):
    rng = np.random.default_rng()
    lens = xyz_max - xyz_min
    return np.array([[rng.random() * lens[0] + xyz_min[0], rng.random() * lens[1] + xyz_min[1], rng.random() * lens[2] + xyz_min[2]]
                    for i in range(num_total_pts)])

def generate_poisson_disc_pts(num_total_pts, xyz_min, xyz_max):
    from scipy.stats import qmc
    radius = 1./int(round(num_total_pts ** (1./3)))
    engine = qmc.PoissonDisk(d=3, radius=radius, ncandidates=10)  # 10 seems to be a good number... might have to look at that again
    samples = engine.fill_space()
    return samples * (xyz_max-xyz_min) + xyz_min


def generate_regular_grid_pts(num_total_pts, xyz_min, xyz_max):
    num_pts_per_axis = int(round(num_total_pts ** (1./3)))
    zz, yy, xx = np.meshgrid(np.linspace(xyz_min[2], xyz_max[2], num_pts_per_axis),
                             np.linspace(xyz_min[1], xyz_max[1], num_pts_per_axis),
                             np.linspace(xyz_min[0], xyz_max[0], num_pts_per_axis), indexing='ij')
    return np.stack((xx, yy, zz), axis=-1).reshape(num_pts_per_axis ** 3, 3)


def is_point_in_surface(point, vertices, triangles, xyz_min, xyz_max):
    closest_side = np.argmin(np.append(point-xyz_min, xyz_max-point))
    end = point.copy()
    end[closest_side % 3] = np.append(xyz_min, xyz_max)[closest_side]

    dist_to_end = end - point
    fraction_of_distance, tnum = closest_triangle_intercept(vertices, triangles, point, end)
    start = point
    intercepts = 0
    margin = 1.001
    while fraction_of_distance is not None:
        intercepts += 1
        if intercepts > 100:
            print("TOO MANY INTERSEPTS")
            return False
        start = start + fraction_of_distance*dist_to_end*margin
        dist_to_end = end - start
        fraction_of_distance, tnum = closest_triangle_intercept(vertices, triangles, start, end)
    return bool(intercepts % 2)




def remove_overlap(session, pl):
    from chimerax.mask.depthmask import masked_volume
    ps = [pl.get_particle(cid) for cid in pl.particle_ids]
    overlap_volume = np.zeros((len(ps), len(ps)))
    if not pl.has_display_model:
        return
    vol = pl.display_model.child_models()[0]
    scm = pl.collection_model.collections['surfaces']
    num_parts = len(ps)
    tris = scm.triangles
    for i in range(num_parts):
        verts = ps[i].full_transform().transform_points(scm.vertices)
        for j in range(i+1, num_parts):
            vol.position = ps[j].full_transform()
            vtf = vol.position.inverse() * scm.scene_position
            if not vtf.is_identity(tolerance=0):
                varray = vtf.transform_points(varray)
            verts = vtf.transform_points(verts)
            surfaces = [(verts, tris)]
            #surfaces = surface_geometry(scm, vol.position.inverse())
            #surfaces[0][0] = ps[i].full_transform().transform_points(surfaces[0][0])
            overlap = masked_volume(vol, surfaces, (0, 1, 0), sandwich=True)
            # verts, tris = overlap.surfaces[0].vertices, overlap.surfaces[0].triangles
            # print(verts)
            # print(tris)
            # overlap_volume[i][j] = measure_volume(overlap.surfaces[0].vertices, overlap.surfaces[0].triangles)
    print(overlap_volume)

    #create vol somehow
        # would be great if i could skip this step and only use the surface values
    #move volume to particle 1
    #get surface verts and tris
    #move them to particle2
    #do the surface geometry stuff
    #run masked_volume()
        # would be great if i could make this in a faster smarter way, because i really only need the verts and tris
    #measure size of new volume

def surface_geometry(surface, tf):
    surfaces = []
    varray, tarray = surface.vertices, surface.masked_triangles

    vtf = tf * surface.scene_position
    if not vtf.is_identity(tolerance = 0):
        varray = vtf.transform_points(varray)
    surfaces.append([varray, tarray])

    return surfaces

def measure_volume(verts, tris):
    vol, holes = enclosed_volume(verts, tris)
    return vol


# def mask(volumes, surfaces):
#     '''Create a new volume where values outside specified surfaces are set to zero.'''
#     surfG = (scm.vertices, scm.masked_triangles)
#     v =
#     mv = masked_volume(v, surf)
#
#     return mv



# def masked_volume(volume, surfaces, projection_axis=(0, 1, 0)):
#     # Calculate position of 2-d depth array and transform surfaces so projection
#     # is along z axis.
#     zsurf, size, tf = surface_projection_coordinates(surfaces, projection_axis,
#                                                      volume)
#     #zsurf is just surf for me i think
#     #size is just bbox size
#     #tf is -bboxmin?
#
#     # Create minimal size volume mask array and calculate transformation from
#     # mask indices to depth array indices.
#
#     #I guess vol is what i need here.
#     vol, mvol, ijk_origin, mijk_to_dijk = volume_mask(volume, surfaces, False, tf)
#
#     # Copy volume to masked volume at depth intervals inside surface.
#     project_and_mask(zsurf, size, mvol, mijk_to_dijk, False, False)
#
#     # Multiply ones mask times volume.
#     mvol *= vol
#
#     # Create masked volume model.
#     v = array_to_model(mvol, volume, ijk_origin, None)
#
#     # Undisplay original map.
#     volume.show(show=False)
#
#     return v


# def surface_projection_coordinates(surfaces, projection_axis, volume):
#
#   g = volume.data
#
#   grid_spacing = g.step #dont think this is actually important for me
#
#   # Determine transform from vertex coordinates to depth array indices
#   # Rotate projection axis to z.
#   from chimerax.geometry import orthonormal_frame, scale, translation
#   tfrs = orthonormal_frame(projection_axis).inverse() * scale([1/s for s in grid_spacing])
#
#   # Transform vertices to depth array coordinates.
#   zsurf = []
#   tcount = 0
#   for vertices, triangles in surfaces:
#     varray = tfrs.transform_points(vertices) #this rotates the coordinates? not sure why. Try skipping
#     zsurf.append((varray, triangles))
#     tcount += len(triangles)
#   if tcount == 0:
#     return None
#
#   # Compute origin for depth grid
#   vmin, vmax = bounding_box(zsurf) #just normal bounding box... vmin =[smallest x, smallest y, smallest z]
#   if axis_aligned: #it is, but not sure i need to do this
#     o = tfrs * g.origin
#     offset = [(vmin[a] - o[a]) for a in (0,1,2)]
#     from math import floor
#     align_frac = [offset[a] - floor(offset[a]) for a in (0,1,2)]
#     vmin -= align_frac
#   else:
#     vmin -= 0.5
#
#   tf = translation(-vmin) * tfrs #dont think this does a lot
#
#   # Shift surface vertices by depth grid origin
#   for varray, triangles in zsurf:
#     varray -= vmin
#
#   # Compute size of depth grid
#   from math import ceil
#   size = tuple(int(ceil(vmax[a] - vmin[a] + 1)) for a in (0,1))
#
#   return zsurf, size, tf
#
# def volume_mask(volume, surfaces, full, tf):
#
#   g = volume.data
#   if full: # its not
#     from chimerax.map.volume import full_region
#     ijk_min, ijk_max = full_region(g.size)[:2]
#   else:
#     ijk_min, ijk_max = bounding_box(surfaces, g.xyz_to_ijk_transform)
#     from math import ceil, floor
#     ijk_min = [int(floor(i)) for i in ijk_min]
#     ijk_max = [int(ceil(i)) for i in ijk_max]
#     from chimerax.map.volume import clamp_region
#     ijk_min, ijk_max = clamp_region((ijk_min, ijk_max, (1,1,1)), g.size)[:2]
#   ijk_size = [a-b+1 for a,b in zip(ijk_max, ijk_min)]
#   vol = g.matrix(ijk_min, ijk_size)
#   from numpy import zeros
#   mvol = zeros(vol.shape, vol.dtype)
#   from chimerax.geometry import translation
#   mijk_to_dijk = tf * g.ijk_to_xyz_transform * translation(ijk_min)
#   return vol, mvol, ijk_min, mijk_to_dijk
#
# def project_and_mask(zsurf, size, mvol, mijk_to_dijk):
#
#   # Create projection depth arrays.
#   from numpy import zeros, intc, float32
#   shape = (size[1], size[0])
#   depth = zeros(shape, float32)
#   tnum = zeros(shape, intc)
#   depth2 = zeros(shape, float32)
#   tnum2 = zeros(shape, intc)
#
#   # Copy volume to masked volume at masked depth intervals.
#   max_depth = 1e37
#   zsurfs = [zsurf]
#   from .mask_cpp import fill_slab
#   for zs in zsurfs:
#     beyond = beyond_tnum = None
#     max_layers = 200
#     for iter in range(max_layers):
#       depth.fill(max_depth)
#       tnum.fill(-1)
#       any = surfaces_z_depth(zs, depth, tnum, beyond, beyond_tnum)
#       if not any:
#         break
#       depth2.fill(max_depth)
#       tnum2.fill(-1)
#       surfaces_z_depth(zs, depth2, tnum2, depth, tnum)
#       fill_slab(depth, depth2, mijk_to_dijk.matrix, mvol, dlimit)
#       beyond = depth2
#       beyond_tnum = tnum2