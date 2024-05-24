#!/usr/bin/env python3

import argparse
import io
import struct
import collections
import logging
import functools
import math

# Define EGS binary track structure formats
EGS_TRACK_COUNT_FORMAT = 'i'
EGS_TRACK_HEADER_FORMAT = 'ii' # Vertex count | Particle type
EGS_VERTEX_FORMAT = 'dddd' # x | y | z | energy

# Define Gmsh metadata needed for the output
GMSH_HEADER = """$MeshFormat
2.2 0 8
$EndMeshFormat
"""
GMSH_PHYSICAL_NAMES = """$PhysicalNames
6
0 1 "Electron Points"
0 2 "Photon Points"
0 3 "Positron Points"
1 1 "Electron Lines"
1 2 "Photon Lines"
1 3 "Positron Lines"
$EndPhysicalNames
"""
GMSH_OPTIONS = """Mesh.ColorCarousel = 2;
Mesh.Lines = 1;
Geometry.Points = 0;
General.Color.Background = {90,90,90};
General.Color.BackgroundGradient = {45,45,75};
Mesh.Color.One = {210,24,6};
Mesh.Color.Two = {208,210,8};
Mesh.Color.Three = {19,210,36};
"""

# Define format-independent track structures
Track = collections.namedtuple('Track', ['vertex_count', 'particle_type', 'vertices'])
Vertex = collections.namedtuple('Vertex', ['x', 'y', 'z', 'e'])

# Define translation schema
PARTICLE_TYPE_TO_PHYSICAL_GROUP = {-1: 1, 0: 2, 1: 3}
OUTPUT_UNITS = ["mm", "cm", "m"]

def scale_for_unit(unit: str) -> float:
    """Translate unit strings to scaling factors"""
    scales = {
        "mm": 10.0,
        "cm": 1.0,
        "m": 0.01,
    }
    # default to cm
    return scales.get(unit, 1.0)

# Configure logging
LOG = logging.getLogger(__name__)
CH = logging.StreamHandler()
FMT = logging.Formatter('[%(asctime)s][%(levelname)s] %(message)s', '%H:%M:%S')
CH.setFormatter(FMT)
LOG.addHandler(CH)
LOG.setLevel(logging.INFO) # Change this to DEBUG if developing

def charge_to_physical_group(charge):
    """Translate EGS particle types to Gmsh physical groups. Unknown particle types will return 0 (no physical group)."""
    return PARTICLE_TYPE_TO_PHYSICAL_GROUP.get(charge, 0)

def parse_args():
    """Parse converter arguments."""
    parser = argparse.ArgumentParser(description='Translate .ptracks files to .msh files such that particle tracks may be viewed in Gmsh.')

    parser.add_argument('input_file', help='Path to .ptracks file you wish to convert.')
    parser.add_argument('output_file', help='Path to the .msh file you wish to create.')

    parser.add_argument('units', type=str, choices=OUTPUT_UNITS,
        help="""Desired converter output units. Assumes input file is in cm""")
    parser.add_argument('-l', '--limit', type=int, help="""Hard cutoff number of tracks beyond which no more tracks will be loaded and converted.
    Setting a cutoff can be useful when there are many tracks, and you wish to lower the memory load of viewing the output in gmsh.""")

    parser.add_argument('-c', '--coarseness', type=int, default=1, help="""The granularity at which to convert the particle tracks.
    Setting this parameter to a number N will mean that one in every N points in each track will be included in the output.
    Start and end points are always included, to preserve the overall shape of the track.
    EGS generates highly granular tracks with a great deal of points, which can be memory intensive for Gmsh despite not greatly affecting visual clarity.
    Suggested values for this parameter range from 100 to 5000 depending on the .ptracks file in question.""")
    
    parser.add_argument('-n', '--min_length', type=int, default=0, help="""The minimum number of points a track must have to be included in the converted output.
    EGS often generates many short lived particles, so setting this value to `3`, `5`, or `10` can help lower memory usage.""")

    parser.add_argument('-x', '--max_length', type=int, default=math.inf, help="""The maximum number of points a track must have to be included in the converted output.
    If you are interested in short-lived particles, set this value.""")

    return parser.parse_args()

def stream_unpack(format, stream):
    """Unpack a struct from a stream."""
    size = struct.calcsize(format)
    buffer = stream.read(size)
    return struct.unpack(format, buffer)

def read_tracks(input_file, limit):
    """Read ptracks from a ptracks file into the intermediate representation."""
    with open(input_file, 'rb') as input:
        input_binary = input.read()
    input_stream = io.BytesIO(input_binary)

    (track_count,) = stream_unpack(EGS_TRACK_COUNT_FORMAT, input_stream)
    LOG.info(f'Total tracks in file: {track_count}')

    if limit is not None and limit < track_count:
        track_count = limit
        LOG.info(f'Limiting tracks loaded to {limit}')

    tracks = []
    for track_index in range(track_count):

        track = Track(*stream_unpack(EGS_TRACK_HEADER_FORMAT, input_stream), [])
        LOG.debug(f'Track #{track_index}: {track}')

        for vertex_index in range(track.vertex_count):
            vertex = Vertex(*stream_unpack(EGS_VERTEX_FORMAT, input_stream))
            LOG.debug(f'\tVertex #{vertex_index}: {vertex}')
            track.vertices.append(vertex)

        tracks.append(track)
    
    return tracks

def filter_tracks(tracks, coarseness, min_length, max_length):
    """Filter tracks in the intermediate representation based on track length and coarseness."""
    # Filter for length
    length_filter = lambda x: min_length <= x.vertex_count <= max_length
    length_filtered = [track for track in tracks if length_filter(track)]
    # Filter for coarseness
    coarse_filtered = []
    for track in length_filtered:

        coarse_filter = lambda i: i == 0 or i == track.vertex_count - 1 or i % coarseness == 0

        coarse_vertices = [track.vertices[i] for i in range(track.vertex_count) if coarse_filter(i)]
        coarse_vertex_count = len(coarse_vertices)
        coarse_track = Track(coarse_vertex_count, track.particle_type, coarse_vertices)

        coarse_filtered.append(coarse_track)

    LOG.info(f'Filtered to {len(coarse_filtered)} tracks.')
    return coarse_filtered

def write_tracks(output_file, tracks, scale: float):
    """Write ptracks in the intermediate representation to a file in the .msh v2 format."""
    # Write headers
    with open(output_file, 'w') as output:
        output.write(GMSH_HEADER)
        output.write(GMSH_PHYSICAL_NAMES)
        # Write nodes
        output.write('$Nodes\n')
        # First, write total number of nodes
        total_nodes = functools.reduce(lambda x,y: x + y.vertex_count, tracks, 0)
        output.write(f'{total_nodes}\n')
        # Then, write each node in the format `node_id x y z`'
        node_id = 0
        node_tracks = []

        for track in tracks:
            node_tracks.append([])
            for vertex in track.vertices:
                output.write(f'{node_id} {vertex.x * scale} {vertex.y * scale} {vertex.z * scale}\n')
                node_tracks[-1].append(node_id)
                node_id += 1
        output.write('$EndNodes\n')
        # Write elements
        output.write('$Elements\n')
        # First, write total number of elements.
        # Each track has vertex_count-1 lines, thus the total number of lines is the total number of vertices minus the total number of tracks
        output.write(f'{total_nodes - len(tracks)}\n')
        # Then, write each element in the format `element_id element_type tag_count tags... nodes...`
        # We want element_type 1 (lines)
        # We want the two mandatory tags, so tag_count 2
        # The first tag is physical group
        # The second tag is mesh entity, we set these to the same as the physical groups so we can toggle the particle views
        element_id = 0
        for track_index in range(len(tracks)):
            node_track = node_tracks[track_index]
            track = tracks[track_index]
            physical_group = charge_to_physical_group(track.particle_type)
            pair_count = len(node_track) - 1
            vertex_pairs = [node_track[i:i+2] for i in range(pair_count)]
            for vertex_pair in vertex_pairs:
                output.write(f'{element_id} 1 2 {physical_group} {physical_group} {vertex_pair[0]} {vertex_pair[1]}\n')
                element_id += 1
        output.write('$EndElements\n')
        LOG.info(f'wrote output file "{output_file}"')

def write_options(output_file):
    """Write options file for the given .msh output file."""
    options_file = output_file + ".opt"
    with open(options_file, 'w') as options:
        options.write(GMSH_OPTIONS)

# new function to call python script 'in python' instead of initiating a new command line instance
def process_ptracks(input_file, output_file, limit=10000, units='mm'):  #  there are a few more 'defaults' than these inputs
    tracks = read_tracks(input_file, limit)  #  limit
    tracks = filter_tracks(tracks, 1, 0, math.inf)  #  coarseness, min length, max length
    write_tracks(output_file, tracks, scale_for_unit(units))
    write_options(output_file)

def main():
    """Main program flow."""
    args = parse_args()
    tracks = read_tracks(args.input_file, args.limit)
    tracks = filter_tracks(tracks, args.coarseness, args.min_length, args.max_length)
    write_tracks(args.output_file, tracks, scale_for_unit(args.units))
    write_options(args.output_file)

if __name__=="__main__":
    main()