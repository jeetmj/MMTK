# This module contains interfaces to external visualization programs
# and a visualization base class
#
# Written by Konrad Hinsen
#

"""
Visualization of chemical objects, including animation

This module provides visualization of chemical objects and animated
visualization of normal modes and sequences of configurations, including
trajectories. Visualization depends on external visualization programs.
On Unix systems, these programs are defined by environment variables.
Under Windows NT, the system definitions for files with extension
"pdb" and "wrl" are used.

A viewer for PDB files can be defined by the environment variable
'PDBVIEWER'. For showing a PDB file, MMTK will execute a command
consisting of the value of this variable followed by a space
and the name of the PDB file.

A viewer for VRML files can be defined by the environment variable
'VRMLVIEWER'. For showing a VRML file, MMTK will execute a command
consisting of the value of this variable followed by a space
and the name of the VRML file.

Since there is no standard for launching viewers for animation,
MMTK supports only two programs: VMD and XMol. MMTK detects
these programs by inspecting the value of the environment variable
'PDBVIEWER'. This value must be the file name of the executable,
and must give "vmd" or "xmol" after stripping off an optional
directory specification.
"""

__docformat__ = 'restructuredtext'

from MMTK import Units, Utility
from Scientific import N
import subprocess, sys, tempfile, os

#
# If you want temporary files in a non-standard directory, make
# its name the value of this variable:
#
tempdir = None

#
# Identify OS
#
running_on_windows = sys.platform == 'win32'
running_on_macosx = sys.platform.startswith('darwin')
running_on_linux = sys.platform.startswith('linux')

#
# Get visualization program names
#
viewer = {}
try:
    pdbviewer = os.environ['PDBVIEWER']
    prog = os.path.split(pdbviewer)[1].lower().split('.')[0]
    viewer['pdb'] = (prog, pdbviewer)
except KeyError: pass
try:
    vrmlviewer = os.environ['VRMLVIEWER']
    prog = os.path.split(vrmlviewer)[1].lower().split('.')[0]
    viewer['vrml'] = (prog, vrmlviewer)
except KeyError: pass


def definePDBViewer(progname, exec_path):
    """
    Define the program used to view PDB files.

    :param progname: the canonical name of the PDB viewer. If it is
                     a known one (one of "vmd", "xmol", "imol"),
                     special features such as animation may be
                     available.
    :type progname: str
    :param exec_path: the path to the executable program
    :type exec_path: str
    """
    viewer['pdb'] = (progname.lower(), exec_path)

def defineVRMLiewer(progname, exec_path):
    """
    Define the program used to view VRML files.

    :param progname: the canonical name of the VRML viewer
    :type progname: str
    :param exec_path: the path to the executable program
    :type exec_path: str
    """
    viewer['vrml'] = (progname.lower(), exec_path)

#
# Visualization base class. Defines methods for general visualization
# tasks.
#
class Viewable(object):

    """
    Any viewable chemical object

    This is a mix-in class that defines a general
    visualization method for all viewable objects, i.e. chemical
    objects (atoms, molecules, etc.), collections, and universes.
    """

    def graphicsObjects(self, **options):
        """
        :keyword configuration: the configuration in which the objects
                                are drawn (default: the current configuration)
        :type configuration: :class:`~MMTK.ParticleProperties.Configuration`
        :keyword model: the graphical representation to be used (one of
                        "wireframe", "tube", "ball_and_stick", "vdw" and
                        "vdw_and_stick").  The vdw models use balls
                        with the radii taken from the atom objects.
                        Default is "wireframe".
        :type model: str
        :keyword ball_radius: the radius of the balls representing the atoms
                              in a ball_and_stick model, default: 0.03
                              This is also used in vdw and vdw_and_stick when
                              an atom does not supply a radius.
        :type ball_radius: float
        :keyword stick_radius: the radius of the sticks representing the bonds
                               in a ball_and_stick, vdw_and_stick or tube model.
                               Default: 0.02 for the tube model, 0.01 for the
                               ball_and_stick and vdw_and_stick models
        :type stick_radius: float
        :keyword graphics_module: the module in which the elementary graphics
                                  objects are defined
                                  (default: Scientific.Visualization.VRML)
        :type graphics_module: module
        :keyword color_values:  a color value for each atom which defines
                                the color via the color scale object specified
                                by the option color_scale. If no value is
                                given, the atoms' colors are taken from the
                                attribute 'color' of each atom object (default
                                values for each chemical element are provided
                                in the chemical database).
        :type  color_values: :class:`~MMTK.ParticleProperties.ParticleScalar`
        :keyword color_scale: an object that returns a color object (as defined
                              in the module Scientific.Visualization.Color)
                              when called with a number argument. Suitable
                              objects are defined by
                              Scientific.Visualization.Color.ColorScale and
                              Scientific.Visualization.Color.SymmetricColorScale.
                              The object is used only when the option
                              color_values is specified as well. The default
                              is a blue-to-red color scale that covers the
                              range of the values given in color_values.
        :type color_scale: callable
        :keyword color: a color name predefined in the module
                        Scientific.Visualization.Color. The corresponding
                        color is applied to all graphics objects that are
                        returned.
        :returns: a list of graphics objects that represent
                  the object for which the method is called.
        :rtype: list
        """
        conf = options.get('configuration', None)
        model = options.get('model', 'wireframe')
        if model == 'tube':
            model = 'ball_and_stick'
            radius = options.get('stick_radius', 0.02)
            options['stick_radius'] = radius
            options['ball_radius'] = radius
        try:
            module = options['graphics_module']
        except KeyError:
            from Scientific.Visualization import VRML
            module = VRML
        color = options.get('color', None)
        if color is None:
            color_values = options.get('color_values', None)
            if color_values is not None:
                lower = N.minimum.reduce(color_values.array)
                upper = N.maximum.reduce(color_values.array)
                options['color_scale'] = module.ColorScale((lower, upper))
        try:
            distance_fn = self.universe().distanceVector
        except AttributeError:
            from MMTK import Universe
            distance_fn = Universe.InfiniteUniverse().distanceVector
        return self._graphics(conf, distance_fn, model, module, options)

    def _atomColor(self, atom, options):
        color = options.get('color', None)
        if color is not None:
            return color
        color_values = options.get('color_values', None)
        if color_values is None:
            return atom.color
        else:
            scale = options['color_scale']
            return scale(color_values[atom])


#
# View anything viewable.
#
def view(object, *parameters):
    "Equivalent to object.view(parameters)."
    object.view(*parameters)

#
# Display an object or a collection of objects using an external
# viewing program.
#
def genericViewConfiguration(object, configuration = None, format = 'pdb',
                             label = None):
    format = format.lower()
    viewer_format = format.split('.')[0]

    tempfile.tempdir = tempdir
    filename = tempfile.mktemp()
    tempfile.tempdir = None
    if viewer_format == 'pdb':
        filename = filename + '.pdb'
    elif viewer_format == 'vrml':
        filename = filename + '.wrl'
    
    if running_on_windows:
        object.writeToFile(filename, configuration, format)
        try:
            os.startfile(filename)
        except win32api.error, error_number:
            #Looking for error 31, SE_ERR_NOASSOC, in particular
            file_type = os.path.splitext(filename)[1]
            if error_number[0]==31:
                print ('There is no program associated with .%s files,' + \
                       ' please install a suitable viewer') % file_type
            else:
                print 'Unexpected error attempting to open .%s file' % file_type
                print sys.exc_value
    elif viewer.has_key(viewer_format):
        # On Unix-like systems, give priority to a  user-specified viewer.
        object.writeToFile(filename, configuration, format)
        if os.fork() == 0:
            pipe = os.popen(viewer[format][1] + ' ' + filename + \
                            ' 1> /dev/null 2>&1', 'w')
            pipe.close()
            os.unlink(filename)
            os._exit(0)
    elif running_on_macosx:
        object.writeToFile(filename, configuration, format)
        subprocess.call(["/usr/bin/open", filename])
    elif running_on_linux:
        object.writeToFile(filename, configuration, format)
        subprocess.call(["xdg-open", filename])
    else:
        Utility.warning('No viewer for %s defined.' % viewer_format)
        return

def viewConfiguration(*args, **kwargs):
    pdbviewer, exec_path = viewer.get('pdb', (None, None))
    function = {'vmd': viewConfigurationVMD,
                'xmol': viewConfigurationXMol,
                'imol': viewConfigurationIMol} \
               .get(pdbviewer,genericViewConfiguration)
    function(*args, **kwargs)

#
# Normal mode and trajectory animation
#
def viewSequence(object, conf_list, periodic = False, label = None):
    """
    Launches an animation using an external viewer.

    :param object: the object for which the animation is displayed.
    :type object: :class:`~MMTK.Collections.GroupOfAtoms`
    :param conf_list: a sequence of configurations that define the animation
    :type conf_list: sequence
    :param periodic: if True, turn animation into a loop
    :param label: an optional text string that some interfaces
                  use to pass a description of the object to the
                  visualization system.
    :type label: str
    """
    pdbviewer, exec_path = viewer.get('pdb', (None, None))
    function = {'vmd': viewSequenceVMD,
                'xmol': viewSequenceXMol,
                'imol': viewSequenceIMol,
                None: None}[pdbviewer]
    if function is None:
        Utility.warning('No viewer with animation feature defined.')
    else:
        function(object, conf_list, periodic, label)


def viewTrajectory(trajectory, first=0, last=None, skip=1, subset = None,
                   label = None):
    """
    Launches an animation based on a trajectory using an external viewer.

    :param trajectory: the trajectory
    :type trajectory: :class:`~MMTK.Trajectory.Trajectory`
    :param first: the first trajectory step to be used
    :type first: int
    :param last: the first trajectory step NOT to be used
    :type last: int
    :param skip: the distance between two consecutive steps shown
    :type skip: int
    :param subset: the subset of the universe that is shown
                   (default: the whole universe)
    :type subset: :class:`~MMTK.Collections.GroupOfAtoms`
    :param label: an optional text string that some interfaces
                  use to pass a description of the object to the
                  visualization system.
    :type label: str
    """
    if type(trajectory) == type(''):
        from MMTK.Trajectory import Trajectory
        trajectory = Trajectory(None, trajectory, 'r')
    if last is None:
        last = len(trajectory)
    elif last < 0:
        last = len(trajectory) + last
    universe = trajectory.universe
    if subset is None:
        subset = universe
    viewSequence(subset, trajectory.configuration[first:last:skip], label)

def viewMode(mode, factor=1., subset=None, label=None):
    universe = mode.universe
    if subset is None:
        subset = universe
    conf = universe.configuration()
    viewSequence(subset, [conf, conf+factor*mode, conf, conf-factor*mode], 1,
                 label)

#
# XMol support
#    

#
# Animation with XMol.
#
viewConfigurationXMol = viewConfiguration

def viewSequenceXMol(object, conf_list, periodic = 0, label = None):
    tempfile.tempdir = tempdir
    file_list = []
    for conf in conf_list:
        file = tempfile.mktemp()
        file_list.append(file)
        object.writeToFile(file, conf, 'pdb')
    bigfile = tempfile.mktemp()
    tempfile.tempdir = None
    subprocess.call(['cat'] + file_list + ['>', bigfile])
    for file in file_list:
        os.unlink(file)
    if os.fork() == 0:
        pipe = os.popen('xmol -readFormat pdb ' + bigfile + \
                        ' 1> /dev/null 2>&1', 'w')
        pipe.close()
        os.unlink(bigfile)
        os._exit(0)


#
# VMD support
#

#
# View configuration
#
def isCalpha(object):
    from MMTK.Proteins import isProtein, isPeptideChain
    from MMTK.Universe import isUniverse
    from MMTK.Collections import isCollection
    if isProtein(object):
       chain_list = list(object)
    elif isPeptideChain(object):
        chain_list = [object]
    elif isUniverse(object) or isCollection(object):
        chain_list = []
        for element in object:
            if isProtein(element):
                chain_list = chain_list + list(element)
            elif isPeptideChain(element):
                chain_list.append(element)
            else:
                return False
    else:
        return False
    for chain in chain_list:
        try:
            if chain.model != 'calpha':
                return False
        except AttributeError:
            return False
    return True

def viewConfigurationVMD(object, configuration = None, format = 'pdb',
                      label = None):
    from MMTK import Universe
    format = format.lower()
    if format != 'pdb':
        return genericViewConfiguration(object, configuration, format)
    tempfile.tempdir = tempdir
    filename = tempfile.mktemp()
    filename_tcl = filename.replace('\\', '\\\\')
    script = tempfile.mktemp()
    script_tcl = script.replace('\\', '\\\\')
    tempfile.tempdir = None
    object.writeToFile(filename, configuration, format)
    file = open(script, 'w')
    file.write('mol load pdb ' + filename_tcl + '\n')
    if isCalpha(object):
        file.write('mol modstyle 0 all trace\n')
    file.write('color Name 1 white\n')
    file.write('color Name 2 white\n')
    file.write('color Name 3 white\n')
    if Universe.isUniverse(object):
        # add a box around periodic universes
        basis = object.basisVectors()
        if basis is not None:
            v1, v2, v3 = basis
            p = -0.5*(v1+v2+v3)
            for p1, p2 in [(p, p+v1), (p, p+v2), (p+v1, p+v1+v2),
                           (p+v2, p+v1+v2), (p, p+v3), (p+v1, p+v1+v3),
                           (p+v2, p+v2+v3), (p+v1+v2, p+v1+v2+v3),
                           (p+v3, p+v1+v3), (p+v3, p+v2+v3),
                           (p+v1+v3, p+v1+v2+v3), (p+v2+v3, p+v1+v2+v3)]:
                file.write('graphics 0 line {%f %f %f} {%f %f %f}\n' %
                           (tuple(p1/Units.Ang) + tuple(p2/Units.Ang)))
    file.write('file delete ' + filename_tcl + '\n')
    if sys.platform != 'win32':
            # Under Windows, it seems to be impossible to delete
            # the script file while it is still in use. For the moment
            # we just don't delete it at all.
        file.write('file delete ' + script_tcl + '\n')
    file.close()
    subprocess.Popen([viewer['pdb'][1], '-nt', '-e', script])

#
# Animate sequence
#
def viewSequenceVMD(object, conf_list, periodic = 0, label=None):
    tempfile.tempdir = tempdir
    script = tempfile.mktemp()
    script_tcl = script.replace('\\', '\\\\')
    np = object.numberOfPoints()
    universe = object.universe()
    if np == universe.numberOfPoints() \
       and len(conf_list) > 2:
        from MMTK import DCD
        pdbfile = tempfile.mktemp()
        pdbfile_tcl = pdbfile.replace('\\', '\\\\')
        dcdfile = tempfile.mktemp()
        dcdfile_tcl = dcdfile.replace('\\', '\\\\')
        tempfile.tempdir = None
        sequence = DCD.writePDB(universe, conf_list[0], pdbfile)
        # For now, write the first bead of each atom:
        indices = [a.index for a in sequence]
        # For writing all beads, this should be:
        # indices = sum((range(a.index, a.index+a.nbeads) for a in sequence), [])
        # but this requires a change in PDB output.
        DCD.writeDCD(conf_list[1:], dcdfile, 1./Units.Ang, indices)
        file = open(script, 'w')
        file.write('mol load pdb ' + pdbfile_tcl + '\n')
        if isCalpha(object):
            file.write('mol modstyle 0 all trace\n')
        file.write('animate read dcd ' + dcdfile_tcl + '\n')
        if periodic:
            file.write('animate style loop\n')
        else:
            file.write('animate style once\n')
        file.write('animate forward\n')
        file.write('file delete ' + pdbfile_tcl + '\n')
        file.write('file delete ' + dcdfile_tcl + '\n')
        if sys.platform != 'win32':
            # Under Windows, it seems to be impossible to delete
            # the script file while it is still in use. For the moment
            # we just don't delete it at all.
            file.write('file delete ' + script_tcl + '\n')
        file.close()
    else:
        file_list = []
        for conf in conf_list:
            file = tempfile.mktemp()
            file_list.append(file)
            object.writeToFile(file, conf, 'pdb')
        tempfile.tempdir = None
        file = open(script, 'w')
        file.write('mol load pdb ' + file_list[0] + '\n')
        for conf in file_list[1:]:
            file.write('animate read pdb ' + conf.replace('\\', '\\\\') + '\n')
        if periodic:
            file.write('animate style loop\n')
        else:
            file.write('animate style once\n')
        file.write('animate forward\n')
        for conf in file_list:
            file.write('file delete ' + conf.replace('\\', '\\\\') + '\n')
        if sys.platform != 'win32':
            # Under Windows, it seems to be impossible to delete
            # the script file while it is still in use. For the moment
            # we just don't delete it at all.
            file.write('file delete ' + script_tcl + '\n')
        file.close()
    subprocess.Popen([viewer['pdb'][1], '-nt', '-e', script])

#
# iMol support
#

#
# View configuration
#
def viewConfigurationIMol(object, configuration = None, format = 'pdb',
                      label = None):
    format = format.lower()
    if format != 'pdb':
        return genericViewConfiguration(object, configuration, format)
    tempfile.tempdir = tempdir
    filename = tempfile.mktemp() + '.pdb'
    tempfile.tempdir = None
    object.writeToFile(filename, configuration, format)
    subprocess.call(['open', '-a', prog, filename])

#
# Animate sequence
#
def viewSequenceIMol(object, conf_list, periodic = 0, label=None):
    from MMTK import PDB
    tempfile.tempdir = tempdir
    filename = tempfile.mktemp() + '.pdb'
    file = PDB.PDBOutputFile(filename)
    for conf in conf_list:
        file.nextModel()
        file.write(object, conf)
    file.close()
    tempfile.tempdir = None
    subprocess.call(['open', '-a', prog, filename])

#
# PyMOL support
#
from MMTK import PyMOL
if PyMOL.in_pymol:

    _representation = None

    def viewConfiguration(object, configuration = None, format = 'pdb',
                          label = None):
        global _representation
        if label is None:
            label = "MMTK Object"
        if _representation is not None:
            _representation.remove()
        _representation = PyMOL.Representation(object, label, configuration)
        _representation.show()
        
    def viewSequence(object, conf_list, periodic = 0, label = None):
        global _representation
        if label is None:
            label = "MMTK Object"
        if _representation is not None:
            _representation.remove()
        _representation = PyMOL.Representation(object, label,
                                               conf_list[0])
        _representation.movie(conf_list)

    genericViewMode = viewMode
    
    def viewMode(mode, factor=1., subset=None, label=None):
        from pymol import cmd
        cmd.set("movie_delay","200",log=1)
        genericViewMode(mode, factor, subset, label)


