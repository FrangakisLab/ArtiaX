# vim: set expandtab shiftwidth=4 softtabstop=4:

# This package
from ..particle.ParticleList import delete_selected_particles, invert_selection

_providers = {
    "Launch": "artiax start",
    "Help": "open help:user/artiax_index.html",
    "XY": "artiax view xy",
    "XZ": "artiax view xz",
    "YZ": "artiax view yz",
    "XY Models Tab": "artiax view xy",
    "XZ Models Tab": "artiax view xz",
    "YZ Models Tab": "artiax view yz",
    "Select": 'ui mousemode right select',
    "Rotate": 'ui mousemode right rotate',
    "Translate": 'ui mousemode right translate',
    "Pivot": 'ui mousemode right pivot',
    "Select Models Tab": 'ui mousemode right select',
    "Rotate Models Tab": 'ui mousemode right rotate',
    "Translate Models Tab": 'ui mousemode right translate',
    "Pivot Models Tab": 'ui mousemode right pivot',
    "Translate Selected Particles": 'ui mousemode right "translate selected particles"',
    "Rotate Selected Particles": 'ui mousemode right "rotate selected particles"',
    "Translate Picked Particle": 'ui mousemode right "translate picked particle"',
    "Rotate Picked Particle": 'ui mousemode right "rotate picked particle"',
    "Delete Selected Particles": delete_selected_particles,
    "Delete Picked Particle": 'ui mousemode right "delete picked particle"',
    "Show Markers": "artiax show markers",
    "Hide Markers": "artiax hide markers",
    "Show Axes": "artiax show axes",
    "Hide Axes": "artiax hide axes",
    "Show Surfaces": "artiax show surfaces",
    "Hide Surfaces": "artiax hide surfaces",
    "Invert Selection": invert_selection
    "Show Markers Models Tab": "artiax show markers",
    "Hide Markers Models Tab": "artiax hide markers",
    "Show Axes Models Tab": "artiax show axes",
    "Hide Axes Models Tab": "artiax hide axes",
    "Show Surfaces Models Tab": "artiax show surfaces",
    "Hide Surfaces Models Tab": "artiax hide surfaces",

    "Fit Sphere": "artiax fit sphere",
    "Fit Line": "artiax fit line",
    "Reorient Sphere Particles": "artiax reorient sphere particles",
    "Fit Surface": "artiax fit surface",
    "Triangulate": "artiax triangulate",
    "Boundary": "artiax boundary",
    "Reorient Boundary Particles": "artiax reorient boundary particles",
    "Create Mask": "artiax mask",
    "Remove Links": 'artiax remove links',
    "Triangles From Links": "artiax triangles from links",
    "Flip Z": "artiax flip z",
    "Select Inside Surface": "artiax select inside surface",
    "Delete Picked Triangle": 'ui mousemode right "delete picked triangle"',
    "Delete Tetra From Boundary": 'ui mousemode right "delete tetra from boundary"',
}


def run_provider(session, name):
    what = _providers[name]

    if not isinstance(what, str):
        what(session)
    else:
        from chimerax.core.commands import run
        run(session, what)
