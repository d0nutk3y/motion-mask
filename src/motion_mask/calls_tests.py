import os
import subprocess as sub
import tempfile

from pycallgraph2 import PyCallGraph, GlobbingFilter, Config, PyCallGraphException
from pycallgraph2.output import GraphvizOutput

import main


class GraphvizOutputCustom(GraphvizOutput):
    def __init__(self):
        super().__init__(
            output_file='calls.png',
            font_name='Arial',
            font_size=12,
            group_font_size=16,
        )

    def done(self):
        source = self.generate()

        self.debug(source)

        fd, temp_name = tempfile.mkstemp()
        with os.fdopen(fd, 'w') as f:
            f.write(source)

        # Only change is adding Gdpi cmd arg for better quality
        cmd = '"{0}" -T{1} -Gdpi=100 -o{2} {3}'.format(
            self.tool, self.output_type, self.output_file, temp_name
        )

        self.verbose('Executing: {0}'.format(cmd))
        try:
            proc = sub.Popen(cmd, stdout=sub.PIPE, stderr=sub.PIPE, shell=True)
            ret, output = proc.communicate()
            if ret:
                raise PyCallGraphException(
                    'The command "%(cmd)s" failed with error '
                    'code %(ret)i.' % locals())
        finally:
            os.unlink(temp_name)

        self.verbose('Generated {0} with {1} nodes.'.format(
            self.output_file, len(self.processor.func_count),
        ))


def go_calls_tests():
    graphviz_output = GraphvizOutputCustom()

    custom_filter = GlobbingFilter(
        exclude=[
            'pycallgraph.*',
            'tests.*',
            'unittest.*'
            'loggers'
            'mediapipe',
            'numpy',
            'pyvirtualcam',
            'builtins', 'os', 'sys', 'json', 're', 'pathlib'
        ],

        include=[
            'avatar.*',
            'avatar_engine.*',
            'frame_utils.*',
            'capture.*',
            'common.*',
            'files_io.*',
        ]
    )

    config = Config(
        verbose=True,
        trace_filter=custom_filter,
        include_stdlib=False,
        include_pycallgraph=False,
        max_depth=1000
    )

    avatar_dir_path = './avatars/kanisan'
    model_path = './landmarkers/face_landmarker.task'

    with PyCallGraph(output=graphviz_output, config=config):
        main.launch(mode=main.AppMode.PREVIEW,
                    avatar_dir_path=avatar_dir_path,
                    model_path=model_path)


if __name__ == '__main__':
    go_calls_tests()
