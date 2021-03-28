import argparse
import glob
import os
import csv
import shutil
import subprocess
from io import StringIO
from typing import Dict, Union

from clams import ClamsApp, Restifier
from mmif import DocumentTypes, AnnotationTypes, Mmif, Document, View, Annotation

__version__ = '0.3.0'
MEDIA_DIRECTORY = '/segmenter/data'
SEGMENTER_DIR = '/segmenter/acoustic-classification-segmentation'
TIME_FRAME_PREFIX = 'tf'
SEGMENTER_ACCEPTED_EXTENSIONS = {'.mp3', '.wav'}


class Segmenter(ClamsApp):

    def _appmetadata(self) -> dict:
        return {
            "name": "Brandeis Acoustic Classification & Segmentation tool",
            "description": "tbd",
            "vendor": "Team CLAMS",
            "iri": f"http://mmif.clams.ai/apps/brandeis-acs/{__version__}",
            "requires": [DocumentTypes.AudioDocument.value],
            "produces": [
                AnnotationTypes.TimeFrame.value
            ]
        }

    def _annotate(self, mmif: Union[str, dict, Mmif], save_tsv=False, pretty=False) -> Mmif:
        mmif_obj: Mmif
        if isinstance(mmif, Mmif):
            mmif_obj: Mmif = mmif
        else:
            mmif_obj: Mmif = Mmif(mmif)

        # get AudioDocuments with locations
        docs = [document for document in mmif_obj.documents
                if document.at_type == DocumentTypes.AudioDocument.value
                and len(document.location) > 0
                and os.path.splitext(document.location)[-1] in SEGMENTER_ACCEPTED_EXTENSIONS]

        files = [document.location for document in docs]

        # key them by location basenames
        docs_dict: Dict[str, Document] = {os.path.splitext(os.path.basename(doc.location))[0]: doc for doc in docs}
        assert len(docs) == len(docs_dict), 'no duplicate filenames'
        # TODO (angus-lherrou @ 2020-10-03): allow duplicate basenames for files originally from different folders
        #  by renaming files more descriptively

        self.setup(files)

        tsv_string = self.segment(save_tsv)

        reader = csv.reader(StringIO(tsv_string), delimiter='\t')

        for row in reader:
            filename = os.path.splitext(os.path.split(row[0])[-1])[0]
            splits = row[1:-1]  # first element is filepath, last element is speech ratio
            assert len(splits) % 2 == 0, 'every row should have an even number of timestamps'

            v: View = mmif_obj.new_view()
            self.stamp_view(v, docs_dict[filename].id)

            tf_idx = 1

            for speech_start_idx in range(0, len(splits)-2, 2):
                s_start_ts = float(splits[speech_start_idx])
                s_end_ts = float(splits[speech_start_idx+1])
                ns_end_ts = float(splits[speech_start_idx+2])
                s_tf = self.create_segment_tf(s_start_ts, s_end_ts, tf_idx, frame_type='speech')
                ns_tf = self.create_segment_tf(s_end_ts, ns_end_ts, tf_idx+1, frame_type='non-speech')
                tf_idx += 2
                v.add_annotation(s_tf)
                v.add_annotation(ns_tf)

            final_s_start_ts = float(splits[-2])
            final_s_end_ts = float(splits[-1])
            final_s_tf = self.create_segment_tf(final_s_start_ts, final_s_end_ts, tf_idx, frame_type='speech')
            v.add_annotation(final_s_tf)

        return mmif_obj

    @staticmethod
    def create_segment_tf(start: float, end: float, index: int, frame_type: str) -> Annotation:
        assert frame_type in {'speech', 'non-speech'}
        tf = Annotation()
        tf.at_type = AnnotationTypes.TimeFrame.value
        tf.id = TIME_FRAME_PREFIX + str(index)
        tf.properties['frameType'] = 'speech'
        # times should be in milliseconds
        tf.properties['start'] = int(start * 1000)
        tf.properties['end'] = int(end * 1000)
        tf.properties['frameType'] = frame_type
        return tf

    def stamp_view(self, view: View, tf_source_id: str):
        if view.is_frozen():
            raise ValueError("can't modify an old view")
        view.metadata['app'] = self.metadata['iri']
        view.new_contain(AnnotationTypes.TimeFrame.value, {'unit': 'milliseconds', 'document': tf_source_id})

    @staticmethod
    def setup(files: list):
        for file in glob.glob(os.path.join(MEDIA_DIRECTORY, '*')):
            os.remove(file)
        links = [os.path.join(MEDIA_DIRECTORY, os.path.basename(file)) for file in files]
        for file, link in zip(files, links):
            shutil.copy(file, link)

    @staticmethod
    def segment(save_tsv=False) -> str:
        pretrained_model_dir = sorted(os.listdir(os.path.join(SEGMENTER_DIR, "pretrained")))[-1]
        if save_tsv:
            output = open('segmented.tsv', 'w')
        else:
            output = subprocess.PIPE
        proc = subprocess.run(
            [
                'python',
                os.path.join(SEGMENTER_DIR, 'run.py'),
                '-s',
                os.path.join(SEGMENTER_DIR, 'pretrained', pretrained_model_dir),
                MEDIA_DIRECTORY
            ],
            stdout=output
        )
        if save_tsv:
            output.close()
            with open('segmented.tsv', 'r') as tsv:
                return tsv.read()
        else:
            return proc.stdout.decode(encoding='utf8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--once',
                        type=str,
                        metavar='PATH',
                        help='Use this flag if you want to run the segmenter on a path you specify, instead of running '
                             'the Flask app.')
    parser.add_argument('--pretty',
                        action='store_true',
                        help='Use this flag to return "pretty" (indented) MMIF data.')
    parser.add_argument('--save-tsv',
                        action='store_true',
                        help='Use this flag to preserve the intermediary TSV file '
                             'generated by the segmenter.')

    parsed_args = parser.parse_args()

    if parsed_args.once:
        with open(parsed_args.once) as mmif_in:
            mmif_str = mmif_in.read()

        segmenter_app = Segmenter()

        mmif_out = segmenter_app.annotate(mmif_str, save_tsv=parsed_args.save_tsv, pretty=parsed_args.pretty)
        with open('mmif_out.json', 'w') as out_file:
            out_file.write(mmif_out)
    else:
        segmenter_app = Segmenter()
        annotate = segmenter_app.annotate
        segmenter_app.annotate = lambda *args, **kwargs: annotate(*args,
                                                                  save_tsv=parsed_args.save_tsv,
                                                                  pretty=parsed_args.pretty)
        segmenter_service = Restifier(segmenter_app)
        segmenter_service.run()
