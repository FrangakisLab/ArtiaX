# vim: set expandtab shiftwidth=4 softtabstop=4:

from .LabelEditSlider import LabelEditSlider
from .CenteredCheckBox import CenteredCheckBox
from .CenteredRadioButton import CenteredRadioButton
from .ManagerTableWidget import ManagerTableWidget
from .GradientRangeSlider import GradientRangeSlider
from .IgnorantComboBox import IgnorantComboBox
from .SelectorWidget import SelectorWidget
from .SelectionTableWidget import SelectionTableWidget
from .ColorRangeWidget import ColorRangeWidget
from .StateButton import StateButton
from .SaveArgsWidget import SaveArgsWidget
from .ColorGeomodelWidget import ColorGeomodelWidget
from .PartlistToolbarWidget import PartlistToolbarWidget
from .LabelEditRangeSlider import LabelEditRangeSlider
from .LineOptions import LineOptions
from .CurvedLineOptions import CurvedLineOptions
from .DegreeButtons import DegreeButtons
from .ModelChooserWidget import ModelChooserWidget
from .LabeledVectorEdit import LabeledVectorEdit
from .ArtiaXSaveDialog import ArtiaXSaveDialog
from .PlaneOptions import PlaneOptions
from .MethodButtons import MethodButtons
from .BoundaryOptions import BoundaryOptions
from .SphereOptions import SphereOptions
from .TriangulateOptions import TriangulateOptions
from .ThreeFieldsAndButton import ThreeFieldsAndButton

def qt_enum_equal(enum_value, comp_value):
    """Compare with Qt enums safely with Qt5 and Qt6."""
    try:
        val = int(enum_value)
    except TypeError:
        val = enum_value.value

    return val == comp_value