# vim: set expandtab shiftwidth=4 softtabstop=4:
import numpy as np

# ChimeraX
from chimerax.mouse_modes.mousemodes import MouseMode
from chimerax.mouse_modes.std_modes import MoveMouseMode
from chimerax.atomic.structure import PickedAtom
from chimerax.graphics.drawing import PickedTriangle
from chimerax.core.models import PickedModel
from chimerax.map import PickedMap
from chimerax.graphics import Drawing
from chimerax.surface import connected_triangles

# This package
from .particle import PickedInstanceTriangle, SurfaceCollectionModel


class MoveParticlesMode(MoveMouseMode):

    def __init__(self, session):
        MoveMouseMode.__init__(self, session)

        # Moving instances, list of drawings
        self._collections = None
        self._masks = None
        self.mouse_action = 'translate'
        self._vr = False

    def mouse_down(self, event):
        MouseMode.mouse_down(self, event)
        self._vr = False
        a = self.action(event)
        self._set_z_rotation(event)

        from .particle.ParticleList import selected_collections
        self._collections, self._masks = selected_collections(self.session)

    def mouse_drag(self, event):
        a = self.action(event)
        if a == 'rotate' or a == 'rotate z':
            axis, angle = self._rotation_axis_angle(event, z_rotate = (a == 'rotate z'))
            self._rotate(axis, angle)
        elif a == 'translate' or a == 'translate z':
            shift = self._translation(event, z_translate = (a == 'translate z'))
            self._translate(shift)
        self._moved = True

    def mouse_up(self, event):
        MouseMode.mouse_up(self, event)

        # Workaround for slow GUI update: only do it when released
        if self._collections is not None:
            for c in self._collections:
                c.parent.update_position_selectors()

    def wheel(self, event):
        return

    def action(self, event):
        if self._vr:
            return self.mouse_action

        a = self.mouse_action
        if event.shift_down():
            # Holding shift key switches between rotation and translation
            if a == 'rotate':
                a = 'translate'
            elif a == 'translate':
                a = 'rotate'
        if event.ctrl_down():
            # Holding control restricts to z-axis rotation or translation
            a = a + ' z'
        if self._z_rotate and a == 'rotate':
            a = 'rotate z'
        return a

    def instances(self):
        return self._collections

    def _rotate(self, axis, angle):
        # Convert axis from camera to scene coordinates
        saxis = self.camera_position.transform_vector(axis)
        angle *= self.speed

        from .particle.SurfaceCollectionModel import rotate_instances
        rotate_instances(saxis, angle, self._collections, self._masks)

    def _translate(self, shift):
        psize = self.pixel_size()
        s = tuple(dx*psize*self.speed for dx in shift)     # Scene units
        step = self.camera_position.transform_vector(s)    # Scene coord system

        from .particle.SurfaceCollectionModel import translate_instances
        translate_instances(step, self._collections, self._masks)

    def _move(self, tf):
        from .particle.SurfaceCollectionModel import move_instances
        move_instances(tf, self._collections, self._masks)

    def wheel(self, event):
        pass

    def touchpad_two_finger_trans(self, event):
        pass

    def touchpad_three_finger_trans(self, event):
        pass

    def touchpad_two_finger_twist(self, event):
        pass

    def vr_press(self, event):
        from .particle.ParticleList import selected_collections
        self._collections, self._masks = selected_collections(self.session)
        self._vr = True

    def vr_motion(self, event):
        if self.action(event) == 'rotate':
            self._move(event.motion)
        else:
            self._move(event.motion)

        self._moved = True

    def vr_release(self, event):
        # Workaround for slow GUI update: only do it when released
        if self._collections is not None:
            for c in self._collections:
                c.parent.update_position_selectors()


class TranslateSelectedParticlesMode(MoveParticlesMode):
    name = 'translate selected particles'
    icon_file = './icons/translate_selected.png'

    def __init__(self, session):
        MoveParticlesMode.__init__(self, session)
        self.mouse_action = 'translate'

class RotateSelectedParticlesMode(MoveParticlesMode):
    name = 'rotate selected particles'
    icon_file = './icons/rotate_selected.png'

    def __init__(self, session):
        MoveParticlesMode.__init__(self, session)
        self.mouse_action = 'rotate'

    # Workaround for particle lists with locked rotation
    def mouse_down(self, event):
        MouseMode.mouse_down(self, event)
        a = self.action(event)
        self._set_z_rotation(event)

        self._vr = False

        from .particle.ParticleList import selected_collections
        self._collections, self._masks = selected_collections(self.session, exclude_rot_lock=True)

    # Workaround for particle lists with locked rotation
    def vr_press(self, event):
        from .particle.ParticleList import selected_collections
        self._collections, self._masks = selected_collections(self.session, exclude_rot_lock=True)
        self._vr = True

class MovePickedParticleMode(MoveParticlesMode):

    def mouse_down(self, event):
        self._vr = False
        a = self.action(event)
        self._set_z_rotation(event)

        x, y = event.position()
        pick = self.view.picked_object(x, y)
        self._pick_model(pick, self.action(event))

    def _pick_model(self, pick, action):
        if isinstance(pick, PickedAtom) and not (action == 'rotate'):
            from .particle import MarkerSetPlus
            par = pick.drawing()
            if isinstance(par, MarkerSetPlus):
                self._collections = [par.parent.collection_model]
                self._masks = [par.parent.id_mask(pick.atom.particle_id)]
            else:
                self._collections = []
                self._masks = []
        elif isinstance(pick, PickedModel) and isinstance(pick.picked_triangle, PickedInstanceTriangle):
            pick = pick.picked_triangle
            self._collections = [pick.drawing().parent]
            self._masks = [pick.position_mask()]
        else:
            self._collections = []
            self._masks = []

    def vr_press(self, event):
        self._vr = True
        pick = event.picked_object(self.view)
        self._pick_model(pick, self.action(event))

class TranslatePickedParticleMode(MovePickedParticleMode):
    name = 'translate picked particle'
    icon_file = './icons/translate_picked.png'

    def __init__(self, session):
        MoveParticlesMode.__init__(self, session)
        self.mouse_action = 'translate'

class RotatePickedParticleMode(MovePickedParticleMode):
    name = 'rotate picked particle'
    icon_file = './icons/rotate_picked.png'

    def __init__(self, session):
        MoveParticlesMode.__init__(self, session)
        self.mouse_action = 'rotate'

class DeletePickedParticleMode(MouseMode):
    name = 'delete picked particle'
    icon_file = './icons/delete.png'

    def __init__(self, session):
        MouseMode.__init__(self, session)

    def mouse_down(self, event):
        x, y = event.position()
        pick = self.view.picked_object(x, y)
        _id, pl = self._pick_model(pick)

        if _id is not None:
            pl.delete_data([_id])

    def _pick_model(self, pick):
        if isinstance(pick, PickedAtom):
            from .particle import MarkerSetPlus
            par = pick.drawing()
            if isinstance(par, MarkerSetPlus):
                return pick.atom.particle_id, par.parent
            else:
                return None, None
        elif isinstance(pick, PickedModel) and isinstance(pick.picked_triangle, PickedInstanceTriangle):
            pick = pick.picked_triangle
            return pick.particle_id(), pick.drawing().parent.parent
        else:
            return None, None

    def vr_press(self, event):
        pick = event.picked_object(self.view)
        _id, pl = self._pick_model(pick)

        if _id is not None:
            pl.delete_data([_id])

class DeleteSelectedParticlesMode(MouseMode):
    name = 'delete selected particles'
    icon_file = './icons/delete_selected.png'

    def __init__(self, session):
        MouseMode.__init__(self, session)

    def mouse_down(self, event):
        from .particle.ParticleList import selected_collections
        collections, masks = selected_collections(self.session)

        for col, ma in zip(collections, masks):
            pl = col.parent
            ids = col.child_ids[ma]
            pl.delete_data(list(ids))

    def vr_press(self, event):
        from .particle.ParticleList import selected_collections
        collections, masks = selected_collections(self.session)

        for col, ma in zip(collections, masks):
            pl = col.parent
            ids = col.child_ids[ma]
            pl.delete_data(list(ids))

class DeletePickedTriangleMode(MouseMode):
    name = 'delete picked triangle'
    icon_file = './icons/delete.png'

    def __init__(self, session):
        MouseMode.__init__(self, session)

    def remove_from_pick(self, pick):
        from .geometricmodel.Boundary import Boundary
        from .geometricmodel.Surface import Surface
        if isinstance(pick, PickedModel) and isinstance(pick.drawing(), (Surface, Boundary)):
            pick = pick.picked_triangle
            geomodel = pick.drawing()
            from .geometricmodel.GeoModel import remove_triangle
            remove_triangle(geomodel, pick.triangle_number)

    def mouse_down(self, event):
        x, y = event.position()
        pick = self.view.picked_object(x, y)
        self.remove_from_pick(pick)

    def vr_press(self, event):
        pick = event.picked_object(self.view)
        self.remove_from_pick(pick)

class DeletePickedTetraMode(MouseMode):
    name = 'delete tetra from boundary'
    icon_file = './icons/delete.png'

    def __init__(self, session):
        MouseMode.__init__(self, session)

    def remove_from_pick(self, pick):
        from .geometricmodel.Boundary import Boundary
        if isinstance(pick, PickedModel) and isinstance(pick.drawing(), Boundary):
            pick = pick.picked_triangle
            boundary = pick.drawing()
            boundary.remove_tetra(pick.triangle_number)

    def mouse_down(self, event):
        x, y = event.position()
        pick = self.view.picked_object(x, y)
        self.remove_from_pick(pick)

    def vr_press(self, event):
        pick = event.picked_object(self.view)
        self.remove_from_pick(pick)


class MaskConnectedTrianglesMode(MouseMode):
    name = 'mask connected triangles'
    #Todo: change image icon
    icon_file = './icons/delete.png'

    def __init__(self, session, radius=None):
        MouseMode.__init__(self, session)
        self.radius = radius

    def mask_connected_triangles(self, pick):
        if hasattr(pick, "drawing") and isinstance(pick.drawing(), Drawing):
            if isinstance(pick, PickedModel):
                t_number = pick.picked_triangle.triangle_number
                surface = pick.drawing()
            elif isinstance(pick, PickedMap) and hasattr(pick, "triangle_pick"):
                t_number = pick.triangle_pick.triangle_number
                surface = None
                for d in pick.drawing().child_drawings():
                    if not d.empty_drawing():
                        surface = d
                        break
                if surface is None:
                    return
            else:
                return

            if isinstance(surface, SurfaceCollectionModel):
                return


            connected_tris = connected_triangles(surface.triangles, t_number)
            if self.radius is not None:
                def tri_coord(surface, tri):
                    return surface.vertices[surface.triangles[tri]].mean(axis=0)
                center = tri_coord(surface, t_number)
                connected_tris = [tri for tri in connected_tris if np.linalg.norm(tri_coord(surface, tri) - center) < self.radius]
            if surface.triangle_mask is None:
                triangles_to_show = np.ones((surface.triangles.shape[0],), dtype=bool)
                triangles_to_show[connected_tris] = False
            else:
                triangles_to_show = surface.triangle_mask
                triangles_to_show[connected_tris] = False
            surface.triangle_mask = triangles_to_show

    def mouse_down(self, event):
        x, y = event.position()
        pick = self.view.picked_object(x, y)
        self.mask_connected_triangles(pick)

    def vr_press(self, event):
        pick = event.picked_object(self.view)
        self.mask_connected_triangles(pick)


# class ColorConnectedTrianglesMode(MouseMode):
#     name = 'color connected triangles'
#     #Todo: change image icon
#     icon_file = './icons/delete.png'
#
#     def __init__(self, session, radius=None):
#         MouseMode.__init__(self, session)
#         self.radius = radius
#
#     def color_connected_triangles(self, pick):
#         print("coloring")
#         if hasattr(pick, "drawing") and isinstance(pick.drawing(), Drawing):
#             if isinstance(pick, PickedModel):
#                 t_number = pick.picked_triangle.triangle_number
#                 surface = pick.drawing()
#             elif isinstance(pick, PickedMap) and hasattr(pick, "triangle_pick"):
#                 t_number = pick.triangle_pick.triangle_number
#                 surface = None
#                 for d in pick.drawing().child_drawings():
#                     if not d.empty_drawing():
#                         surface = d
#                         break
#                 if surface is None:
#                     return
#             else:
#                 return
#
#             if isinstance(surface, SurfaceCollectionModel):
#                 return
#
#             # Only show the color picker dialog if no color is currently selected
#             from Qt.QtWidgets import QColorDialog
#
#             # Launch a color picker dialog
#             color = QColorDialog.getColor()
#
#             if color.isValid():
#                 # Convert QColor to RGBA and store it in the class attribute
#                 self.selected_color = [color.red(), color.green(), color.blue(), 255]
#                 print("Selected color:", self.selected_color)
#
#
#             connected_tris = connected_triangles(surface.triangles, t_number)
#             if self.radius is not None:
#                 def tri_coord(surface, tri):
#                     return surface.vertices[surface.triangles[tri]].mean(axis=0)
#
#                 center = tri_coord(surface, t_number)
#                 connected_tris = [tri for tri in connected_tris if
#                                   np.linalg.norm(tri_coord(surface, tri) - center) < self.radius]
#             if surface.triangle_mask is None:
#                 triangles_to_show = np.ones((surface.triangles.shape[0],), dtype=bool)
#                 triangles_to_show[connected_tris] = True
#             else:
#                 triangles_to_show = surface.triangle_mask
#                 triangles_to_show[connected_tris] = True
#             surface.triangle_mask = triangles_to_show
#
#             # Check if vertex_colors is None
#             if surface.vertex_colors is None:
#                 # Initialize vertex_colors with the existing color or a default color
#                 num_vertices = surface.vertices.shape[0]
#                 if surface._colors is not None:
#                     # Use the existing overall color (_colors)
#                     vertex_colors = np.tile(surface._colors, (num_vertices, 1))  # Repeat _colors for all vertices
#                 else:
#                     # Default to white if no color exists
#                     vertex_colors = np.array([[255, 255, 255, 255]] * num_vertices, dtype=np.uint8)
#                 surface.vertex_colors = vertex_colors
#
#             # Changing color of specific triangles
#             triangle_indices = surface.triangles[connected_tris]  # Get vertex indices for specific triangles
#             for tri in triangle_indices:
#                 surface.vertex_colors[tri] = self.selected_color  # Use the stored color
#
#             # Apply the updated colors
#             print("coloring done")
#             surface.vertex_colors = surface.vertex_colors.copy()
#             surface.set_colors(surface.vertex_colors)
#             print("Vertex colors after update:", surface.vertex_colors[triangle_indices.flatten()])
#
#
#     def mouse_down(self, event):
#         x, y = event.position()
#         pick = self.view.picked_object(x, y)
#         self.color_connected_triangles(pick)
#
#     def vr_press(self, event):
#         pick = event.picked_object(self.view)
#         self.color_connected_triangles(pick)


# class ExtractConnectedTrianglesMode(MouseMode):
#     name = 'extract connected triangles'
#     #Todo: change image icon
#     icon_file = './icons/delete.png'
#
#     def __init__(self, session, radius=None):
#         MouseMode.__init__(self, session)
#         self.radius = radius
#         self.session=session
#
#     def extract_connected_triangles(self, pick, subdivide_length=None):
#         print("extracting")
#         if hasattr(pick, "drawing") and isinstance(pick.drawing(), Drawing):
#             if isinstance(pick, PickedModel):
#                 t_number = pick.picked_triangle.triangle_number
#                 surface = pick.drawing()
#             elif isinstance(pick, PickedMap) and hasattr(pick, "triangle_pick"):
#                 t_number = pick.triangle_pick.triangle_number
#                 surface = None
#                 for d in pick.drawing().child_drawings():
#                     if not d.empty_drawing():
#                         surface = d
#                         break
#                 if surface is None:
#                     return
#             else:
#                 return
#
#             if isinstance(surface, SurfaceCollectionModel):
#                 return
#
#             connected_tris = connected_triangles(surface.triangles, t_number)
#             if self.radius is not None:
#                 def tri_coord(surface, tri):
#                     return surface.vertices[surface.triangles[tri]].mean(axis=0)
#
#                 center = tri_coord(surface, t_number)
#                 connected_tris = [tri for tri in connected_tris if
#                                   np.linalg.norm(tri_coord(surface, tri) - center) < self.radius]
#             if surface.triangle_mask is None:
#                 triangles_to_show = np.ones((surface.triangles.shape[0],), dtype=bool)
#                 triangles_to_show[connected_tris] = True
#             else:
#                 triangles_to_show = surface.triangle_mask
#                 triangles_to_show[connected_tris] = True
#             surface.triangle_mask = triangles_to_show
#
#             # Extract vertices and triangles
#             vertices = surface.vertices
#             triangles = surface.triangles[connected_tris]
#
#             from chimerax.map_data import ArrayGridData
#             from chimerax.geometry.bounds import union_bounds
#             from chimerax.surface._surface import subdivide_mesh
#             from .volume.Tomogram import Tomogram
#
#             # Optional subdivision
#             if subdivide_length:
#                 vertices, triangles, _ = subdivide_mesh(vertices, triangles, normals=None,
#                                                         target_edge_length=subdivide_length)
#
#             # Calculate bounds
#             xyz_min = vertices.min(axis=0)
#             xyz_max = vertices.max(axis=0)
#             grid_size = np.ceil(xyz_max - xyz_min).astype(int)
#             voxel_step = 1  # Adjust step size if needed
#             grid_resolution = [voxel_step] * 3
#
#             # Create an empty grid
#             grid_data = np.zeros(grid_size, dtype=np.float32)
#
#             # Map vertices to voxel indices
#             for vertex in vertices:
#                 grid_index = np.floor((vertex - xyz_min) / voxel_step).astype(int)
#                 if (grid_index >= 0).all() and (grid_index < grid_size).all():
#                     grid_data[grid_index[2], grid_index[1], grid_index[0]] = 1  # Flip to [z, y, x]
#
#             # Create ArrayGridData and Tomogram
#             agd = ArrayGridData(grid_data, step=grid_resolution, name="Subset Volume")
#             new_tomo = Tomogram(self.session, agd)
#             new_tomo.set_parameters(surface_levels=[0.999])  # Adjust level for binary grid
#             self.session.models.add([new_tomo])  # Add new tomogram to session
#
#             # # Extract vertices and triangles
#             # vertices = surface.vertices
#             # triangles = surface.triangles[connected_tris]
#             #
#             # # Define the bounding box for the subset
#             # bounds_min = vertices.min(axis=0)
#             # bounds_max = vertices.max(axis=0)
#             # step = [1.0, 1.0, 1.0]  # Example voxel size, modify as needed
#             # grid_shape = np.ceil((bounds_max - bounds_min) / step).astype(int)
#             #
#             # # Initialize the voxel grid
#             # voxel_grid = np.zeros(grid_shape, dtype=np.float32)
#             #
#             # from chimerax.map_data import ArrayGridData
#             # from volume.Tomogram import Tomogram
#             #
#             # # Voxelize the surface into the grid
#             # for tri in triangles:
#             #     tri_verts = vertices[tri]
#             #     voxelize_triangle_into_grid(tri_verts, voxel_grid, bounds_min, step)
#             #
#             # name="test"
#             #
#             # # Create ArrayGridData for the tomogram
#             # agd = ArrayGridData(voxel_grid, step=step, origin=bounds_min, name=name)
#             #
#             # # Create and add the tomogram to the session
#             # new_tomo = Tomogram(session, agd)
#             # new_tomo.set_parameters(surface_levels=[0.999])  # Adjust surface level as needed
#             # session.models.add([new_tomo])
#             # print(f"New tomogram '{name}' created and added to the session.")
#
#
#     def mouse_down(self,event):
#         x, y = event.position()
#         pick = self.view.picked_object(x, y)
#         self.extract_connected_triangles(pick)
#
#     def vr_press(self, event):
#         pick = event.picked_object(self.view)
#         self.extract_connected_triangles(pick)