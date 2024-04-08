# General imports
import numpy as np
import math
from scipy import interpolate

# ChimeraX imports
from chimerax.bild.bild import _BildFile
from chimerax.atomic import AtomicShapeDrawing
from chimerax.core.models import Model

# ArtiaX imports
from .GeoModel import GeoModel


class TriangulationSurface(GeoModel):
    """Creates triangles between the particles connected in the particle_pairs list. Can also be made from the triangles
    if they are already known."""

    def __init__(self, name, session, particle_pairs=None, particles=None, triangles=None):
        super().__init__(name, session)

        self.particle_pairs = particle_pairs
        self.particles = particles
        """(n x 2) list of particles, where every row is two connected particles."""
        if triangles is None:
            triangles = triangles_from_pairs(self.particle_pairs)
        self.tri = triangles
        """(n x 3 x 3) list of floats, where every row is a triangle with 3 points."""

        self.update()
        session.logger.info("Created a triangulated surface.")

    def define_surface(self):
        b = _BildFile(self.session, 'dummy')

        for triangle in self.tri:
            b.polygon_command(
                ".polygon {} {} {} {} {} {} {} {} {}".format(*triangle[0], *triangle[1], *triangle[2]).split())

        d = AtomicShapeDrawing('shapes')
        d.add_shapes(b.shapes)

        return d.vertices, d.normals, d.triangles

    def update(self):
        vertices, normals, triangles = self.define_surface()
        self.set_geometry(vertices, normals, triangles)
        self.vertex_colors = np.full((len(vertices), 4), self.color)

    def recalc_and_update(self):
        if self.particle_pairs is not None:
            tris = triangles_from_pairs(self.particle_pairs)
            if len(tris) == 0:  # Particles removed so that no triangles can be made anymore
                self.particle_pairs = None
            else:
                self.tri = tris
        self.update()

    def orient_particles(self, particles, max_dist=None):
        """Uses vertex if particle is one and nearby triangle if it's not. Doesn't really make sense,
        as there's no 'out' in the same way there is for boundarys. So normals point away from an avarage points, which
        doesn't make a lot of sense, but it was the only thing I could think of. If its a convex shape
        it works pretty well."""
        from chimerax.geometry import z_align

        verts = np.zeros((0,3))
        max_normals = 10
        normals = np.zeros((len(self.tri) * 3, max_normals, 3))
        normals_indices = np.zeros(len(normals), dtype=np.int32)
        vertex_index = 0
        for tri in self.tri:
            normal = np.cross(tri[1] - tri[0], tri[2] - tri[0])
            normal = normal/np.linalg.norm(normal)
            for corner in tri:
                added_index = None
                for i, vert in enumerate(verts):
                    if np.isclose(vert, corner).all():
                        added_index = i
                if added_index is not None:
                    normals[added_index][normals_indices[added_index]] = normal
                    normals_indices[added_index] += 1
                    if normals_indices[added_index] == max_normals:
                        normals_indices[added_index] = max_normals - 1
                else:
                    verts = np.append(verts, [corner], axis=0)
                    normals[vertex_index][0] = normal
                    normals_indices[vertex_index] = 1
                    vertex_index += 1
        normals = normals[:vertex_index]
        normals_indices = normals_indices[:vertex_index]
        average_vert = sum(verts)/len(verts)
        for i, vert_norms in enumerate(normals):
            vert_to_avarage = average_vert - verts[i]
            for j, normal in enumerate(vert_norms[:normals_indices[i]]):
                if np.dot(normal, vert_to_avarage) > 0:
                    vert_norms[j] = -normal

        handled_particles = np.array([])
        if self.particles is not None:
            for particle in self.particles:
                if particle in particles and not particle in handled_particles:
                    handled_particles = np.append(handled_particles, particle)
                    pos = np.asarray(particle.coord)
                    vert_index = np.where(verts==particle.coord)[0][0]
                    normal = np.add.reduce(normals[vert_index])
                    rot = z_align(pos, pos + normal).zero_translation().inverse()
                    # Set rotation
                    particle.rotation = rot

        unaligned = [None] * len(particles)
        unaligned_index = 0
        for particle in particles:
            if particle not in handled_particles:
                unaligned[unaligned_index] = particle
                unaligned_index += 1
        unaligned = unaligned[:unaligned_index]
        unaligned_coord = np.array([p.coord for p in unaligned])
        from chimerax.geometry._geometry import find_closest_points
        if max_dist is None:
            max_dist = max(self.bounds().xyz_max - self.bounds().xyz_min)
        unaligned_indices, aligned_indices, closest_indices = find_closest_points(unaligned_coord, verts, max_dist)
        for (unaligned_index, closest_index) in zip(unaligned_indices, closest_indices):
            curr_part = unaligned[unaligned_index]
            closest_pos = verts[closest_index]
            curr_pos = np.asarray(curr_part.coord)
            closest_to_current = curr_pos - np.asarray(closest_pos)
            closest_normals = normals[closest_index][:normals_indices[closest_index]]
            # Find normal most similar to the vector from the vertex to the particles
            orientation = closest_normals[
                np.argmax(np.array([np.dot(closest_to_current, normal) for normal in closest_normals]))]
            rot = z_align(curr_pos, curr_pos + orientation).zero_translation().inverse()
            # Set rotation
            curr_part.rotation = rot

        for particle_list in self.session.ArtiaX.partlists.child_models():
            particle_list.update_places()


    def write_file(self, file_name):
        with open(file_name, 'wb') as file:
            np.savez(file, model_type="TriangulationSurface", triangles=self.tri)

    def take_snapshot(self, session, flags):
        data = {
            'triangles': self.tri,
        }
        data["model state"] = Model.take_snapshot(self, session, flags)
        return data

    @classmethod
    def restore_snapshot(cls, session, data):
        triangles = data['triangles']
        model = cls(data["model state"]["name"], session, triangles=triangles)
        Model.set_state_from_snapshot(model, session, data["model state"])
        return model



def make_links(markers, connections):
    """Creates links between the markers where using the connections.

    Parameters
    ----------
    markers: particle markers. needs to be markers and not particles as only markers can be linked.
    connections: simplices gotten from scipy triangulation. A list of polygons.
    """
    from chimerax.markers.markers import create_link
    for polygon in connections:
        for i in range(0, len(polygon)):
            for j in range(i + 1, len(polygon)):
                try:
                    create_link(markers[polygon[i]], markers[polygon[j]])
                except TypeError:  # bond already exists
                    pass


def triangles_from_pairs(particle_pairs):
    """ Creates a list of triangles using pairs of particles. Kinda complicated, could probably be made simpler.

    Parameters
    ----------
    particle_pairs: (n x 2) list of particles, where every row is two connected particles.


    Returns
    -------
    triangles: (n x 3 x 3) list of floats, where every row is a triangle with 3 points.
    """
    triangles = np.zeros((0, 3, 3))
    while len(particle_pairs[0]) > 1:
        first_corner = particle_pairs[0][0]
        second_corner = particle_pairs[1][0]
        if not first_corner.deleted and not second_corner.deleted:
            bonds_that_contain_first = find_bonds_containing_corner(particle_pairs, first_corner)
            bonds_that_contain_second = find_bonds_containing_corner(particle_pairs, second_corner)
            for second_side in bonds_that_contain_second:
                third_corner = None
                if second_corner == particle_pairs[0][second_side]:
                    if not particle_pairs[1][second_side] == first_corner:
                        third_corner = particle_pairs[1][second_side]
                elif not particle_pairs[0][second_side] == first_corner:
                    third_corner = particle_pairs[0][second_side]
                if third_corner is not None and not third_corner.deleted:
                    for third_side in bonds_that_contain_first:
                        if third_corner == particle_pairs[0][third_side] or third_corner == particle_pairs[1][
                            third_side]:
                            triangles = np.append(triangles, [[first_corner.coord, second_corner.coord,
                                                               third_corner.coord]], axis=0)
        particle_pairs = np.delete(particle_pairs, 0, 1)

    return triangles


def find_bonds_containing_corner(particle_pairs, corner):
    bonds_containing_corner = np.array([])
    for bond in range(0, len(particle_pairs[0])):
        if particle_pairs[0][bond] == corner or particle_pairs[1][bond] == corner:
            bonds_containing_corner = np.append(bonds_containing_corner, bond)
    return bonds_containing_corner.astype(np.int32)
